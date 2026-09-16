import re
from time import monotonic

from app.db import models
from app.db.session import SessionLocal
from app.domain.content_validation import caption_matches_prefix
from app.domain.rewrite_engine import RewriteEngine
from app.integrations.notifiers.telegram import send_telegram_msg
from app.integrations.publishers.facebook_page import FacebookPagePublisher
from app.integrations.wordpress.source import WordPressSourceGateway
from app.services.ai_client_factory import create_ai_client
from app.services.error_sanitizer import sanitize_error
from app.services.pattern_collection_service import PatternCollectionService
from app.services.wordpress_publishing_service import WordPressPublishingService
from app.services.workflow_job_service import WorkflowJobService
from app.services.proxy_settings_service import ProxySettingsService


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
    def execute(job_id: str, draft_id: str, mode: str = "v2", source_gateway=None, use_proxy: bool = False):
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

            step_accounts = pipeline.step_accounts or {}
            ai_account_id = step_accounts.get("ai")
            wp_account_id = step_accounts.get("wp")

            ai_account = (
                db.query(models.Account)
                .filter(models.Account.id == ai_account_id, models.Account.type == "ai")
                .first()
            )
            if not ai_account:
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

            try:
                # Step 2: Source Ingestion & Pattern Collection
                jobs.progress(job_id, "fetch_source", 10, "Fetching source article")
                if source_gateway:
                    source = source_gateway.fetch(draft.source_url)
                else:
                    proxy_url = ProxySettingsService.get_selected(db) if use_proxy else ""
                    source = WordPressSourceGateway(proxy_url=proxy_url).fetch(draft.source_url)
                draft.image_kind = "url" if source.image_url else None
                draft.image_source = source.image_url or None
                db.commit()

                if bool((pipeline.settings or {}).get("collect_patterns", False)):
                    PatternCollectionService(db).collect(
                        {
                            "source_url": source.source_url,
                            "title": source.title,
                            "content": source.content,
                            "image_url": source.image_url,
                        },
                        pipeline.id,
                        parent_job_id=job_id,
                        ai_account_id=ai_account_id,
                    )

                def check_cancelled():
                    fresh = db.query(models.Job).filter(models.Job.id == job_id).first()
                    if fresh and fresh.status == "cancelled":
                        raise InterruptedError("Article workflow cancelled")

                ai_client = create_ai_client(ai_account)

                # Step 3: AI Processing Core (The only branching point)
                if mode == "v1":
                    # Mode V1: Deterministic Translation
                    def v1_progress(msg: str):
                        check_cancelled()
                        jobs.progress(job_id, "translate_story", 50, msg)

                    translated = ai_client.translate_article_fields(
                        title=source.title,
                        content=source.content,
                        image_url=source.image_url or "",
                        language=pipeline.language,
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
                    rewrite_result = RewriteEngine(ai_client, chunk_size=chunk_size).rewrite(
                        source.title, source.content, pipeline.language, v2_progress
                    )
                    check_cancelled()
                    res_title = rewrite_result["title"]
                    res_content = rewrite_result["content"]
                    res_caption = rewrite_result["caption"]
                    res_caption_matches_prefix = rewrite_result.get("caption_matches_prefix", False)
                    res_warnings = rewrite_result.get("warnings", [])

                db.expire(job)
                if job.status == "cancelled":
                    raise InterruptedError("Article workflow cancelled")

                # Step 4: Draft Assembly & Quality Validation
                draft.title = res_title
                draft.content = res_content
                draft.caption = res_caption
                draft.language = pipeline.language
                draft.state = "ready_for_review"
                draft.error = None
                draft.version += 1
                db.commit()

                # Step 5: Multi-Channel Publishing Hub
                jobs.progress(job_id, "publish_wordpress", 92, "Publishing to WordPress")
                published = WordPressPublishingService(db).publish(draft.id, confirmed=True)

                fb_post_id = None
                if fb_account and fb_account.config:
                    try:
                        jobs.progress(job_id, "publish_facebook", 96, "Publishing to Facebook Page")
                        fb_cfg = fb_account.config or {}
                        fb_pub = FacebookPagePublisher(
                            page_id=fb_cfg.get("page_id"),
                            access_token=fb_cfg.get("access_token"),
                            graph_version=fb_cfg.get("graph_version", "v23.0"),
                        )
                        fb_caption = f"{res_caption}\n\nĐọc chi tiết tại: {published.wp_url}" if published.wp_url else res_caption
                        if draft.image_source:
                            fb_post_id = fb_pub.publish_photo_caption(fb_caption, draft.image_source)
                        else:
                            fb_post_id = fb_pub.publish_text(fb_caption)
                    except Exception as fb_err:
                        res_warnings.append(f"Facebook publish error: {sanitize_error(str(fb_err))[:120]}")

                tg_status = None
                if tg_account and tg_account.config:
                    try:
                        jobs.progress(job_id, "notify_telegram", 98, "Sending Telegram notification")
                        tg_cfg = tg_account.config or {}
                        bot_token = tg_cfg.get("bot_token")
                        chat_id = tg_cfg.get("chat_id")
                        if bot_token and chat_id:
                            msg = (
                                f"✅ <b>Article Processed [{pipeline.language}] ({mode.upper()})</b>\n\n"
                                f"📝 <b>Title:</b> {res_title}\n"
                                f"🔗 <b>WP URL:</b> {published.wp_url}\n"
                            )
                            if fb_post_id:
                                msg += f"📱 <b>FB Post:</b> {fb_post_id}\n"
                            send_telegram_msg(bot_token, chat_id, msg)
                            tg_status = "sent"
                    except Exception as tg_err:
                        res_warnings.append(f"Telegram notify error: {sanitize_error(str(tg_err))[:120]}")

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
                if draft.state == "generating":
                    draft.state = "generation_failed"
                    draft.error = "Generation was cancelled"
                    draft.version += 1
                    db.commit()
                return
            except Exception as exc:
                if draft.state not in {"publish_failed", "publish_unknown"}:
                    draft.state = "generation_failed"
                draft.error = sanitize_error(str(exc))[:500]
                draft.version += 1
                db.commit()
                jobs.fail(job_id, exc)
