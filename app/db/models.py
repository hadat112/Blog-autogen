import uuid
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer, ForeignKey
from datetime import datetime
from .session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    language = Column(String, default="Ukrainian")
    step_accounts = Column(JSON, nullable=False)
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def wp_category_id(self):
        if not isinstance(self.settings, dict):
            return None
        return self.settings.get("wp_category_id")

class Language(Base):
    __tablename__ = "languages"
    code = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    pipeline_id = Column(String, ForeignKey("pipelines.id"))
    input_text = Column(String, nullable=True)
    input_type = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    current_step = Column(String, nullable=True)
    progress = Column(Integer, default=0)
    logs = Column(JSON, default=list)
    rerun_at = Column(DateTime, nullable=True)
    rerun_job_id = Column(String, nullable=True)
