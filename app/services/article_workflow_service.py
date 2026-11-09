import hashlib
from types import SimpleNamespace
from app.services.workflow_recovery_service import WorkflowRecoveryService
from app.services.article_workflow_intake import build_article_manifest
import re
from time import monotonic
from pathlib import Path
import logging

from app.db import models
from app.db.session import SessionLocal
from app.domain.content_validation import caption_matches_prefix
from app.domain.rewrite_engine import RewriteEngine
from app.integrations.notifiers.telegram import send_telegram_msg
from app.integrations.publishers.facebook_page import FacebookPagePublisher
from app.integrations.wordpress.source import WordPressSourceGateway
from app.services.ai_client_factory import create_ai_client
from app.services.article_service import ArticleService, normalize_source_url, source_slug
from app.services.article_enrichment_service import ArticleEnrichmentService
from app.services.error_sanitizer import sanitize_error
from app.services.pattern_collection_service import PatternCollectionService
from app.services.wordpress_publishing_service import WordPressPublishingService, _draft_locks
from app.services.workflow_job_service import WorkflowJobService
from app.services.proxy_settings_service import ProxySettingsService
from app.domain.settings_manager import SettingsManager


def _definitely_rejected(error):
    status = getattr(getattr(error, "response", None), "status_code", None)
    return status in {400, 401, 403, 404, 413, 422, 429}


def _create_v1_caption(translated_content: str, max_words: int = 50) -> str:
    """Extract a sentence-safe teaser caption matching the prefix of translated_content."""
    clean = (translated_content or "").strip()
    if not clean:
        return ""
    sentences = re.split(r"(?<=[.!?…])\s+", clean)
    parts = []
    word_count = 0
    for sentence in sentences:
        parts.append(sentence)
        word_count += len(sentence.split())
        if word_count >= max_words:
            break
    caption = " ".join(parts).strip()
    # Ensure it is a strict prefix of clean text
    if not clean.startswith(caption):
        # Fallback to direct prefix slice
        words = clean.split()
        caption = " ".join(words[:max_words])
    return caption


class ArticleWorkflowService:
    @staticmethod
    def execute(job_id: str, draft_id: str, mode: str = "v2", source_gateway=None, use_proxy: bool = False, use_enrichment: bool = False):
        mode = str(mode or "v2").strip().lower()
        if mode not in {"v1", "v2"}:
            mode = "v2"

        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            draft = db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if not draft or not job or job.status == "cancelled":
                return

            pipeline = (
                db.query(models.Pipeline)
                .filter(models.Pipeline.id == draft.pipeline_id, models.Pipeline.is_active.is_(True))
                .first()
            )
            if not pipeline:
                jobs.fail(job_id, "Pipeline is unavailable")
                return

            existing_recovery = db.get(models.WorkflowRecovery, draft.id)
            frozen = (existing_recovery.manifest or {}) if existing_recovery else {}
            step_accounts = frozen.get("step_accounts", pipeline.step_accounts or {})
            ai_account_id = step_accounts.get("ai")
            wp_account_id = step_accounts.get("wp")
            is_original = not (frozen.get("language", pipeline.language) or "").strip()

            ai_account = None
            if not is_original:
                ai_account = (
                    db.query(models.Account)
                    .filter(models.Account.id == ai_account_id, models.Account.type == "ai")
                    .first()
                )
            if not is_original and not ai_account:
                jobs.fail(job_id, "AI account is unavailable")
                return

            wp_account = (
                db.query(models.Account)
                .filter(models.Account.id == wp_account_id, models.Account.type == "wp")
                .first()
            )
            if not wp_account:
                jobs.fail(job_id, "WordPress account is unavailable")
                return

            # Resolve optional secondary accounts
            fb_account = None
            fb_account_id = step_accounts.get("fb")
            if fb_account_id:
                fb_account = (
                    db.query(models.Account)
                    .filter(models.Account.id == fb_account_id, models.Account.type == "fb")
                    .first()
                )

            tg_account = None
            tg_account_id = step_accounts.get("tg")
            if tg_account_id:
                tg_account = (
                    db.query(models.Account)
                    .filter(models.Account.id == tg_account_id, models.Account.type == "tg")
                    .first()
                )

            recovery = WorkflowRecoveryService(db, draft_id, job_id)
            claimed_recovery = False
            db.commit()  # Never hold the caller's read transaction during network work.
            try:
                manifest = recovery.claim(build_article_manifest(
                    db, draft, mode=mode, source_kind=frozen.get('source_kind', 'url'),
                    use_proxy=use_proxy, use_enrichment=use_enrichment,
                    app_config=SettingsManager().config, frozen=frozen,
                ))
                claimed_recovery = True
                mode = manifest["mode"]
                target_language = manifest["language"]
                use_proxy = manifest["use_proxy"]
                use_enrichment = manifest["use_enrichment"]
                is_original = not (target_language or "").strip()
                frozen_accounts = manifest["step_accounts"]
                ai_account_id = frozen_accounts.get("ai")
                ai_account = db.get(models.Account, ai_account_id) if ai_account_id else None
                if not is_original and not ai_account:
                    raise ValueError("Original AI account is unavailable")
                if frozen_accounts.get("wp"):
                    recovery.save_draft(wp_account_id=frozen_accounts["wp"])
                fb_account = db.get(models.Account, frozen_accounts.get("fb")) if frozen_accounts.get("fb") else None
                tg_account = db.get(models.Account, frozen_accounts.get("tg")) if frozen_accounts.get("tg") else None
                db.commit()

                # Historic failed publication may already contain a complete translation.
                if not recovery.get("assembled") and draft.title and draft.content and draft.state in {"ready_for_review", "publish_failed", "publish_unknown", "wordpress_created"}:
                    recovery.save("assembled", {"title": draft.title, "content": draft.content, "caption": draft.caption or "", "warnings": [], "caption_matches_prefix": False})
                is_manual = manifest.get('source_kind', 'url') == 'manual'
                if is_manual:
                    source_data = recovery.get('source')
                    assembled = recovery.get('assembled')
                    if not source_data or not source_data.get('title', '').strip() or not source_data.get('content', '').strip():
                        raise ValueError('Saved manual source is unavailable; start a new run')
                    source = SimpleNamespace(title=source_data['title'], content=source_data['content'],
                        image_url=source_data.get('image_url') or '', source_url=None)
                    recovery.save_draft(image_kind=source_data.get('image_kind'), image_source=source_data.get('image_source'))
                else:
                    source_data = recovery.get("source")
                    assembled = recovery.get("assembled")
                    if source_data is None and assembled is None:
                        jobs.progress(job_id, "fetch_source", 10, "Fetching source article")
                        recovery.check_active()
                        proxy_url = ProxySettingsService.get_selected(db) if use_proxy else ""
                        source = (source_gateway or WordPressSourceGateway(proxy_url=proxy_url)).fetch(draft.source_url)
                        source_data = {"title": source.title, "content": source.content, "image_url": source.image_url, "source_url": draft.source_url}
                        recovery.save("source", source_data)
                        recovery.save("source_hash", hashlib.sha256(source.content.encode()).hexdigest())
                        recovery.save_draft(image_kind="url" if source.image_url else None, image_source=source.image_url or None)
                        db.expire_all()
                    source = SimpleNamespace(**(source_data or {"title": draft.title, "content": draft.content, "image_url": draft.image_source or "", "source_url": draft.source_url}))
                    source_url = normalize_source_url(draft.source_url)
                    pattern_exists = ArticleService(db).get_by_slug(source_slug(source_url)) is not None
                    if not assembled and not recovery.get("collected"):
                        # Archive the fetched source even when it already exists. This
                        # backfills older rows that predate source_content.
                        should_collect = SettingsManager().config.get("auto_collect_patterns", True)
                        if should_collect:
                            source_data = {
                                "source_url": draft.source_url,
                                "title": source.title,
                                "content": source.content,
                                "image_url": source.image_url,
                                "language": target_language,
                            }
                            if pattern_exists:
                                ArticleService(db).archive_source(**source_data)
                            else:
                                PatternCollectionService(db).collect(
                                    source_data,
                                    pipeline.id,
                                    parent_job_id=job_id,
                                    ai_account_id=ai_account_id,
                                    analyze=not use_enrichment and not is_original,
                                )
                            if use_enrichment and not is_original:
                                article = ArticleService(db).get_by_slug(source_slug(source_url))
                                enrichment_account_id = SettingsManager().config.get("enrichment_ai_account_id") or ai_account_id
                                ArticleEnrichmentService.enqueue(
                                    article.id,
                                    pipeline.id,
                                    parent_job_id=job_id,
                                    ai_account_id=enrichment_account_id,
                                ) if article else None
                        recovery.save("collected", True)
                def check_cancelled():
                    recovery.check_active()

                if assembled:
                    res_title, res_content, res_caption = assembled["title"], assembled["content"], assembled["caption"]
                    res_caption_matches_prefix = assembled.get("caption_matches_prefix", False)
                    res_warnings = list(assembled.get("warnings", []))
                else:
                    # Step 3: AI Processing Core (The only branching point)
                    if is_original:
                        # Original/repost pipelines preserve the fetched article and
                        # skip all translation/rewrite and enrichment AI calls.
                        res_title = source.title
                        res_content = source.content
                        res_caption = ""
                        res_caption_matches_prefix = False
                        res_warnings = []
                    elif mode == "v1":
                        ai_client = create_ai_client(ai_account)
                        ai_client.recovery = recovery
                        ai_client.retry_transient = True
                        ai_client.cancelled = recovery.cancelled
                        ai_client.translation_chunk_size = manifest["chunk_size"]
                        ai_client.translation_mode = manifest.get("translation_mode", "sequential")
                        # Mode V1: Deterministic Translation
                        def v1_progress(msg: str):
                            check_cancelled()
                            jobs.progress(job_id, "translate_story", 50, msg)

                        translated = ai_client.translate_article_fields(
                            title=source.title,
                            content=source.content,
                            image_url=source.image_url or "",
                            language=target_language,
                            progress_callback=v1_progress,
                        )
                        check_cancelled()
                        res_title = str(translated.get("title") or "").strip()
                        res_content = str(translated.get("content") or "").strip()
                        res_caption = str(translated.get("caption") or "").strip()
                        if not res_caption:
                            res_caption = _create_v1_caption(res_content, max_words=50)

                        res_caption_matches_prefix = caption_matches_prefix(res_content, res_caption)
                        res_warnings = []
                    else:
                        # Mode V2: Dramatic Rewrite
                        ai_client = create_ai_client(ai_account)
                        ai_client.recovery = recovery
                        ai_client.retry_transient = True
                        ai_client.cancelled = recovery.cancelled
                        ai_client.translation_chunk_size = manifest["chunk_size"]
                        ai_client.translation_mode = manifest.get("translation_mode", "sequential")
                        def v2_progress(index, total, phase, meta=None):
                            check_cancelled()
                            if phase == "metadata":
                                jobs.progress(job_id, "prepare_publish", 90, "Preparing automatic WordPress publication")
                                return
                            meta = meta or {}
                            event = meta.get("event", "progress")
                            if event == "start":
                                detail = f"Chunk {index}/{total} started · {meta.get('word_count', 0):,} words"
                            elif event == "done":
                                detail = f"Chunk {index}/{total} completed · {meta.get('word_count', 0):,} words · {meta.get('elapsed_ms', 0):,} ms"
                            else:
                                detail = f"Chunk {index}/{total}"
                            jobs.progress(
                                job_id,
                                "rewrite_story",
                                10 + round(index / total * 75),
                                detail,
                            )

                        chunk_size = getattr(ai_client, "translation_chunk_size", 6000)
                        engine = RewriteEngine(ai_client, chunk_size=chunk_size)
                        engine.recovery = recovery
                        rewrite_result = engine.rewrite(
                            source.title, source.content, target_language, v2_progress
                        )
                        check_cancelled()
                        res_title = rewrite_result["title"]
                        res_content = rewrite_result["content"]
                        res_caption = rewrite_result["caption"]
                        res_caption_matches_prefix = rewrite_result.get("caption_matches_prefix", False)
                        res_warnings = rewrite_result.get("warnings", [])
                    if not res_title.strip() or not res_content.strip():
                        raise ValueError("AI result requires a complete title and article body")
                    recovery.save("assembled", {"title": res_title, "content": res_content, "caption": res_caption,
                                               "caption_matches_prefix": res_caption_matches_prefix, "warnings": res_warnings})

                db.expire(job)
                if job.status == "cancelled":
                    raise InterruptedError("Article workflow cancelled")

                # Completed generation is durable before any external publication.
                if not draft.wp_post_id:
                    next_state = draft.state if draft.state in {"publish_unknown", "publishing"} else "ready_for_review"
                    recovery.save_draft(title=res_title, content=res_content, caption=res_caption,
                                        language=target_language, state=next_state, error=None)
                db.expire_all()
                db.commit()

                # Step 5: Multi-Channel Publishing Hub
                jobs.progress(job_id, "publish_wordpress", 92, "Publishing to WordPress")
                source_proxy_url = ProxySettingsService.get_selected(db) if use_proxy else ""
                published_data = recovery.get("wordpress")
                if not published_data and draft.wp_post_id:
                    published_data = {"wp_post_id": draft.wp_post_id, "wp_url": draft.wp_url, "wp_status": draft.wp_status, "error": draft.error}
                if published_data:
                    published = SimpleNamespace(**published_data)
                else:
                    recovery.check_active()
                    if draft.state in {"publish_unknown", "publishing"}:
                        raise ValueError("WordPress result is uncertain; verify the previous post before retrying")
                    published = WordPressPublishingService(db).publish(
                        draft.id, confirmed=True, source_proxy_url=source_proxy_url, guard=recovery.check_active,
                        retain_upload=is_manual,
                    )
                    published_data = {"wp_post_id": published.wp_post_id, "wp_url": published.wp_url, "wp_status": published.wp_status,
                                      "error": published.error if isinstance(published.error, str) else None}
                recovery.save("wordpress", published_data)
                if isinstance(published.error, str) and published.error:
                    res_warnings.append(published.error)

                fb_post_id = recovery.get("facebook")
                delivery_errors = []
                if fb_account and fb_account.config and not fb_post_id:
                    try:
                        with _draft_locks[draft.id]:
                            fb_post_id = recovery.get("facebook")
                            if not fb_post_id:
                                jobs.progress(job_id, "publish_facebook", 96, "Publishing to Facebook Page")
                                recovery.check_active()
                                if recovery.get("facebook_pending"):
                                    raise ValueError("Facebook result is uncertain; verify the previous delivery before retrying")
                                recovery.save("facebook_pending", True)
                                fb_cfg = fb_account.config or {}
                                fb_pub = FacebookPagePublisher(
                                    page_id=fb_cfg.get("page_id"),
                                    access_token=fb_cfg.get("access_token"),
                                    graph_version=fb_cfg.get("graph_version", "v23.0"),
                                )
                                fb_caption = f"{res_caption}\n\nĐọc chi tiết tại: {published.wp_url}" if published.wp_url else res_caption
                                if draft.image_kind == 'upload' and draft.image_source:
                                    fb_post_id = fb_pub.publish_photo_file(fb_caption, draft.image_source)
                                elif draft.image_source:
                                    fb_post_id = fb_pub.publish_photo_caption(fb_caption, draft.image_source)
                                else:
                                    fb_post_id = fb_pub.publish_text(fb_caption)
                                recovery.save_receipt("facebook", fb_post_id)
                    except InterruptedError:
                        raise
                    except Exception as fb_err:
                        if _definitely_rejected(fb_err):
                            recovery.save("facebook_pending", False)
                        delivery_errors.append("Facebook delivery failed or is uncertain")
                        res_warnings.append(f"Facebook publish error: {sanitize_error(str(fb_err))[:120]}")

                tg_status = recovery.get("telegram")
                if tg_account and tg_account.config and not tg_status:
                    try:
                        with _draft_locks[draft.id]:
                            tg_status = recovery.get("telegram")
                            if not tg_status:
                                jobs.progress(job_id, "notify_telegram", 98, "Sending Telegram notification")
                                recovery.check_active()
                                if recovery.get("telegram_pending"):
                                    raise ValueError("Telegram result is uncertain; verify the previous delivery before retrying")
                                tg_cfg = tg_account.config or {}
                                bot_token = tg_cfg.get("bot_token")
                                chat_id = tg_cfg.get("chat_id")
                                if bot_token and chat_id:
                                    msg = (
                                        f"✅ <b>Article Processed [{target_language}] ({mode.upper()})</b>\n\n"
                                        f"📝 <b>Title:</b> {res_title}\n"
                                        f"🔗 <b>WP URL:</b> {published.wp_url}\n"
                                    )
                                    if fb_post_id:
                                        msg += f"📱 <b>FB Post:</b> {fb_post_id}\n"
                                    recovery.save("telegram_pending", True)
                                    send_telegram_msg(bot_token, chat_id, msg)
                                    tg_status = "sent"
                                    recovery.save_receipt("telegram", tg_status)
                    except InterruptedError:
                        raise
                    except Exception as tg_err:
                        if _definitely_rejected(tg_err):
                            recovery.save("telegram_pending", False)
                        delivery_errors.append("Telegram delivery failed or is uncertain")
                        res_warnings.append(f"Telegram notify error: {sanitize_error(str(tg_err))[:120]}")

                recovery.check_active()
                if delivery_errors:
                    raise ValueError("; ".join(delivery_errors))
                recovery.save("complete", True)
                if is_manual and draft.image_kind == 'upload' and draft.image_source:
                    path = Path(draft.image_source)
                    if 'var/uploads' in path.as_posix():
                        try:
                            path.unlink(missing_ok=True)
                        except OSError:
                            logging.getLogger(__name__).warning('Could not remove completed workflow upload: draft_id=%s', draft.id)
                jobs.complete(job_id, {
                    "draft_id": draft.id,
                    "mode": mode,
                    "wp_post_id": published.wp_post_id,
                    "wp_url": published.wp_url,
                    "wp_status": published.wp_status,
                    "fb_post_id": fb_post_id,
                    "tg_status": tg_status,
                    "caption_matches_prefix": res_caption_matches_prefix,
                    "warnings": res_warnings,
                })
            except InterruptedError:
                recovery.finish_cancelled()
                return
            except Exception as exc:
                if not claimed_recovery:
                    jobs.fail(job_id, exc)
                    return
                try:
                    recovery.check_active()
                except InterruptedError:
                    return
                db.rollback()
                db.expire_all()
                state = draft.state
                if state == "publishing":
                    state = "publish_unknown"
                if state not in {"publish_failed", "publish_unknown", "wordpress_created"}:
                    state = "publish_failed" if recovery.get("assembled") else "generation_failed"
                recovery.save_draft(state=state, error=sanitize_error(str(exc))[:500])
                jobs.fail(job_id, exc)
