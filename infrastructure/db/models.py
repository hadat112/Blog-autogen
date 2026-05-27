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
    language = Column(String, default="uk")
    step_accounts = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    pipeline_id = Column(String, ForeignKey("pipelines.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    current_step = Column(String, nullable=True)
    progress = Column(Integer, default=0)
    logs = Column(JSON, default=[])
