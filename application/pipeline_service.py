from datetime import datetime

from sqlalchemy.orm import Session

from core.worker_manager import worker_manager
from infrastructure.db import models


class PipelineService:
    def __init__(self, db: Session):
        self.db = db

    def list_pipelines(self):
        return self.db.query(models.Pipeline).all()

    def get_pipeline(self, pipeline_id: str):
        return self.db.query(models.Pipeline).filter(models.Pipeline.id == pipeline_id).first()

    def _settings_from_pipeline_data(self, pipeline_data):
        settings = dict(pipeline_data.settings or {})
        if pipeline_data.wp_category_id is not None:
            settings["wp_category_id"] = pipeline_data.wp_category_id
        return settings

    def _language_value(self, language: str, pipeline_type: str):
        if not isinstance(language, str):
            raise ValueError("Language is required")
        if pipeline_type != "crawl" and not language.strip():
            raise ValueError("Language is required")
        return language

    def create_pipeline(self, pipeline_data):
        language_name = self._language_value(pipeline_data.language, pipeline_data.type)
        pipeline = models.Pipeline(
            name=pipeline_data.name,
            type=pipeline_data.type,
            language=language_name,
            step_accounts=pipeline_data.step_accounts,
            settings=self._settings_from_pipeline_data(pipeline_data),
            is_active=pipeline_data.is_active,
        )
        self.db.add(pipeline)
        self.db.commit()
        self.db.refresh(pipeline)
        return pipeline

    def update_pipeline(self, pipeline_id: str, pipeline_data):
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        pipeline.name = pipeline_data.name
        pipeline.type = pipeline_data.type
        pipeline.language = self._language_value(pipeline_data.language, pipeline_data.type)
        pipeline.step_accounts = pipeline_data.step_accounts
        pipeline.settings = self._settings_from_pipeline_data(pipeline_data)
        pipeline.is_active = pipeline_data.is_active
        self.db.commit()
        self.db.refresh(pipeline)
        return pipeline

    def delete_pipeline(self, pipeline_id: str) -> bool:
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return False

        self.db.delete(pipeline)
        self.db.commit()
        return True

    def _input_from_legacy_logs(self, logs):
        logs = list(logs or [])
        for log in logs:
            if log.get("event") == "input" and log.get("detail"):
                return log["detail"]

        prefix = "Step 1: Extracting article from "
        for log in logs:
            detail = log.get("detail")
            if (
                log.get("step_name") == "Extract article from URL"
                and isinstance(detail, str)
                and prefix in detail
            ):
                return detail.split(prefix, 1)[1].strip()

        return None

    async def start_pipeline_run(self, pipeline_id: str, prompt_data=None):
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        prompt = prompt_data.prompt if prompt_data else None

        rerun_from_job_id = prompt_data.rerun_from_job_id if prompt_data else None
        old_job = None
        if rerun_from_job_id:
            old_job = self.db.query(models.Job).filter(
                models.Job.id == rerun_from_job_id,
                models.Job.pipeline_id == pipeline_id,
                models.Job.status == "failed",
            ).first()
            if old_job and not prompt:
                prompt = old_job.input_text or self._input_from_legacy_logs(old_job.logs)
            if not prompt:
                raise ValueError("Rerun input was not found")

        job_id = await worker_manager.start_pipeline_run(
            pipeline_id=pipeline_id,
            db=self.db,
            prompts_file=prompt_data.prompts_file if prompt_data and prompt_data.prompts_file else "prompts.txt",
            prompt=prompt,
        )

        if old_job:
            old_job.rerun_at = datetime.utcnow()
            old_job.rerun_job_id = job_id
            self.db.commit()

        return job_id
