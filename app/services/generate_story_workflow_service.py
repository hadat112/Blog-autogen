from app.db import models
from app.db.session import SessionLocal
from app.domain.story_agent import StoryAgent
from app.domain.story_agent_tools import StoryAgentTools
from app.services.ai_client_factory import create_ai_client
from app.services.workflow_job_service import WorkflowJobService


class GenerateStoryWorkflowService:
    @staticmethod
    def execute(job_id, draft_id):
        with SessionLocal() as db:
            jobs = WorkflowJobService(db)
            draft = db.query(models.ContentDraft).filter(models.ContentDraft.id == draft_id).first()
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if not draft or not job or job.status == "cancelled":
                return
            profile = db.query(models.Pipeline).filter(
                models.Pipeline.id == draft.pipeline_id, models.Pipeline.type == "generate_story"
            ).first()
            account_id = (profile.step_accounts or {}).get("ai") if profile else None
            account = db.query(models.Account).filter(models.Account.id == account_id, models.Account.type == "ai").first()
            if not profile or not account:
                jobs.fail(job_id, "Generate Story profile or AI account is unavailable")
                return
            try:
                jobs.progress(job_id, "Choose story patterns", 5)

                def on_tool(call_number, name):
                    current = db.query(models.Job).filter(models.Job.id == job_id).first()
                    if current and current.status == "cancelled":
                        raise InterruptedError("Generation cancelled")
                    jobs.progress(job_id, f"Agent tool: {name}", min(70, 10 + call_number * 10))

                result = StoryAgent(create_ai_client(account), StoryAgentTools(db)).generate(profile.language, on_tool)
                db.expire(job)
                if job.status == "cancelled":
                    raise InterruptedError("Generation cancelled")
                draft.title = result["title"]
                draft.content = result["content"]
                draft.caption = result["caption"]
                draft.language = profile.language
                draft.state = "ready_for_review"
                draft.error = None
                draft.version += 1
                db.commit()
                warnings = [] if result["caption_matches_prefix"] else ["Caption differs from story opening"]
                jobs.complete(job_id, {
                    "draft_id": draft.id,
                    "tool_calls": result["tool_calls"],
                    "caption_matches_prefix": result["caption_matches_prefix"],
                    "warnings": warnings,
                })
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
