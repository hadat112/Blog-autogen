from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

class AccountBase(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class PipelineBase(BaseModel):
    name: str
    type: str
    language: str
    step_accounts: Dict[str, str]
    is_active: bool = True

class PipelineCreate(PipelineBase):
    pass

class PipelineResponse(PipelineBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class QuickRunInput(BaseModel):
    prompts_file: Optional[str] = None
    prompt: Optional[str] = None

class JobBase(BaseModel):
    pipeline_id: str
    pipeline_name: Optional[str] = None
    status: str
    current_step: Optional[str] = None
    progress: int = 0
    logs: List[Any] = Field(default_factory=list)

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: str
    start_time: datetime

    class Config:
        from_attributes = True
