from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

class AccountBase(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

class LanguageBase(BaseModel):
    display_name: str = Field(min_length=1)
    is_active: bool = True

class LanguageCreate(LanguageBase):
    code: str = Field(min_length=1, max_length=12)

class LanguageUpdate(LanguageBase):
    pass

class LanguageResponse(LanguageCreate):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime

class AppSettings(BaseModel):
    proxy_url: str = ""
    proxy_urls: List[str] = Field(default_factory=list)
    translation_mode: str = Field(default="sequential")
    translation_max_concurrency: int = Field(default=2, ge=1, le=8)
    ai_request_timeout: int = Field(default=300, ge=30, le=900)
    translation_chunk_size: int = Field(default=6000, ge=1000, le=30000)
    auto_collect_patterns: bool = True
    default_ai_enrichment: bool = False
    enrichment_ai_account_id: str = ""


class ProxyCheckInput(BaseModel):
    proxy_urls: List[str] = Field(default_factory=list)

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
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

class QuickRunInput(BaseModel):
    prompts_file: Optional[str] = None
    prompt: Optional[str] = None
    rerun_from_job_id: Optional[str] = None

class JobBase(BaseModel):
    pipeline_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    input_text: Optional[str] = None
    input_type: Optional[str] = None
    status: str
    current_step: Optional[str] = None
    progress: int = 0
    logs: List[Any] = Field(default_factory=list)
    rerun_at: Optional[datetime] = None
    rerun_job_id: Optional[str] = None
    workflow_type: str = "legacy"
    parent_job_id: Optional[str] = None
    draft_id: Optional[str] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)
    capabilities: Dict[str, bool] = Field(default_factory=dict)

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None

class JobPageResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
