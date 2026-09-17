from app.db import models
from app.db.session import SessionLocal
from app.domain.rewrite_engine import RewriteEngine
from app.integrations.wordpress.source import WordPressSourceGateway
from app.services.ai_client_factory import create_ai_client
from app.services.pattern_collection_service import PatternCollectionService
from app.services.wordpress_publishing_service import WordPressPublishingService
from app.services.workflow_job_service import WorkflowJobService
from app.services.error_sanitizer import sanitize_error
from app.domain.settings_manager import SettingsManager
from app.services.article_service import ArticleService, normalize_source_url, source_slug


class RewriteWorkflowService:
    @staticmethod
    def execute(job_id, draft_id, source_gateway=None):
        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            draft = db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if not draft or not job or job.status == "cancelled":
                return
            pipeline = db.query(models.Pipeline).filter(models.Pipeline.id == draft.pipeline_id, models.Pipeline.is_active.is_(True)).first()
            if not pipeline:
                jobs.fail(job_id, "Rewrite pipeline is unavailable")
                return
            ai_account_id = (pipeline.step_accounts or {}).get("ai")
            account = db.query(models.Account).filter(models.Account.id == ai_account_id, models.Account.type == "ai").first()
            if not account:
                jobs.fail(job_id, "AI account is unavailable")
                return
            try:
                source_url = normalize_source_url(draft.source_url)
                pattern_exists = ArticleService(db).get_by_slug(source_slug(source_url)) is not None
                jobs.progress(job_id, "fetch_source", 5, "Fetching source article")
                source = (source_gateway or WordPressSourceGateway()).fetch(draft.source_url)
                draft.image_kind = "url" if source.image_url else None
                draft.image_source = source.image_url or None
                db.commit()
                if not pattern_exists and SettingsManager().config.get("auto_collect_patterns", True):
                    PatternCollectionService(db).collect(
                        {
                            "source_url": draft.source_url,
                            "title": source.title,
                            "content": source.content,
                            "image_url": source.image_url,
                        },
                        pipeline.id,
                        parent_job_id=job_id,
                        ai_account_id=ai_account_id,
                    )

                def on_progress(index, total, phase, meta=None):
                    fresh = db.query(models.Job).filter(models.Job.id == job_id).first()
                    if fresh and fresh.status == "cancelled":
                        raise InterruptedError("Rewrite cancelled")
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
                        10 + round(index / total * 70),
                        detail,
                    )

                ai_client = create_ai_client(account)
                result = RewriteEngine(ai_client, chunk_size=ai_client.translation_chunk_size).rewrite(
                    source.title, source.content, pipeline.language, on_progress
                )
                db.expire(job)
                if job.status == "cancelled":
                    raise InterruptedError("Rewrite cancelled")
                draft.title = result["title"]
                draft.content = result["content"]
                draft.caption = result["caption"]
                draft.language = pipeline.language
                draft.state = "ready_for_review"
                draft.error = None
                draft.version += 1
                db.commit()
                jobs.progress(job_id, "publish_wordpress", 95, "Publishing to WordPress")
                published = WordPressPublishingService(db).publish(draft.id, confirmed=True)
                jobs.complete(job_id, {
                    "draft_id": draft.id,
                    "wp_post_id": published.wp_post_id,
                    "wp_url": published.wp_url,
                    "wp_status": published.wp_status,
                    "caption_matches_prefix": result["caption_matches_prefix"],
                    "warnings": result["warnings"],
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
