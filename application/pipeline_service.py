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

    def create_pipeline(self, pipeline_data):
        pipeline = models.Pipeline(
            name=pipeline_data.name,
            type=pipeline_data.type,
            language=pipeline_data.language,
            step_accounts=pipeline_data.step_accounts,
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
        pipeline.language = pipeline_data.language
        pipeline.step_accounts = pipeline_data.step_accounts
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

    async def start_pipeline_run(self, pipeline_id: str, prompt_data=None):
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        job_id = await worker_manager.start_pipeline_run(
            pipeline_id=pipeline_id,
            db=self.db,
            prompts_file=prompt_data.prompts_file if prompt_data and prompt_data.prompts_file else "prompts.txt",
            prompt=prompt_data.prompt if prompt_data else None,
        )
        return job_id
