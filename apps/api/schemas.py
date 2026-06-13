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

class LanguageBase(BaseModel):
    display_name: str = Field(min_length=1)
    is_active: bool = True

class LanguageCreate(LanguageBase):
    code: str = Field(min_length=1, max_length=12)

class LanguageUpdate(LanguageBase):
    pass

class LanguageResponse(LanguageCreate):
    created_at: datetime

    class Config:
        from_attributes = True

class PipelineBase(BaseModel):
    name: str
    type: str
    language: str
    step_accounts: Dict[str, str]
    settings: Dict[str, Any] = Field(default_factory=dict)
    wp_category_id: Optional[str] = None
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
    rerun_from_job_id: Optional[str] = None

class JobBase(BaseModel):
    pipeline_id: str
    pipeline_name: Optional[str] = None
    input_text: Optional[str] = None
    input_type: Optional[str] = None
    status: str
    current_step: Optional[str] = None
    progress: int = 0
    logs: List[Any] = Field(default_factory=list)
    rerun_at: Optional[datetime] = None
    rerun_job_id: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: str
    start_time: datetime

    class Config:
        from_attributes = True
