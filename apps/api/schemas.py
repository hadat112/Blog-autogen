from datetime import datetime
from typing import Optional, List, Any, Dict, Literal
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


class TranslationBenchmarkCreate(BaseModel):
    account_ids: List[str]
    target_language: str
    suite: Literal["standard", "custom"] = "standard"
    custom_title: Optional[str] = None
    custom_content: Optional[str] = None


class TranslationBenchmarkRating(BaseModel):
    account_id: str
    score: int = Field(ge=1, le=5)
    notes: str = ""


class TranslationBenchmarkResponse(BaseModel):
    id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    target_language: str
    suite: str
    selected_account_ids: List[str] = Field(default_factory=list)
    request_config: Dict[str, Any] = Field(default_factory=dict)
    results: List[Any] = Field(default_factory=list)
    manual_ratings: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
