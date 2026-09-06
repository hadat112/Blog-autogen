from app.db import models
from app.db.session import SessionLocal
from app.domain.rewrite_engine import RewriteEngine
from app.integrations.wordpress.source import WordPressSourceGateway
from app.services.ai_client_factory import create_ai_client
from app.services.pattern_collection_service import PatternCollectionService
from app.services.workflow_job_service import WorkflowJobService


class RewriteWorkflowService:
    @staticmethod
    def execute(job_id, draft_id, source_gateway=None):
        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            draft = db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if not draft or not job or job.status == "cancelled":
                return
            profile = db.query(models.Pipeline).filter(models.Pipeline.id == draft.pipeline_id, models.Pipeline.type == "rewrite").first()
            if not profile:
                jobs.fail(job_id, "Rewrite profile is unavailable")
                return
            ai_account_id = (profile.step_accounts or {}).get("ai")
            account = db.query(models.Account).filter(models.Account.id == ai_account_id, models.Account.type == "ai").first()
            if not account:
                jobs.fail(job_id, "AI account is unavailable")
                return
            try:
                jobs.progress(job_id, "Fetch source article", 5)
                source = (source_gateway or WordPressSourceGateway()).fetch(draft.source_url)
                draft.image_kind = "url" if source.image_url else None
                draft.image_source = source.image_url or None
                db.commit()
                if bool((profile.settings or {}).get("collect_patterns", False)):
                    PatternCollectionService(db).collect(
                        {
                            "source_url": source.source_url,
                            "title": source.title,
                            "content": source.content,
                            "image_url": source.image_url,
                        },
                        profile.id,
                        parent_job_id=job_id,
                        ai_account_id=ai_account_id,
                    )

                def on_progress(index, total, _):
                    fresh = db.query(models.Job).filter(models.Job.id == job_id).first()
                    if fresh and fresh.status == "cancelled":
                        raise InterruptedError("Rewrite cancelled")
                    jobs.progress(job_id, f"Rewrite chunk {index}/{total}", 10 + round(index / total * 70))

                ai_client = create_ai_client(account)
                result = RewriteEngine(ai_client, chunk_size=ai_client.translation_chunk_size).rewrite(
                    source.title, source.content, profile.language, on_progress
                )
                db.expire(job)
                if job.status == "cancelled":
                    raise InterruptedError("Rewrite cancelled")
                draft.title = result["title"]
                draft.content = result["content"]
                draft.caption = result["caption"]
                draft.language = profile.language
                draft.state = "ready_for_review"
                draft.error = None
                draft.version += 1
                db.commit()
                jobs.complete(job_id, {"draft_id": draft.id, "warnings": result["warnings"]})
            except InterruptedError:
                if draft.state == "generating":
                    draft.state = "generation_failed"
                    draft.error = "Generation was cancelled"
                    draft.version += 1
                    db.commit()
                return
            except Exception as exc:
                draft.state = "generation_failed"
                draft.error = str(exc)[:500]
                draft.version += 1
                db.commit()
                jobs.fail(job_id, exc)
