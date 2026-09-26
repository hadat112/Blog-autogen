from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


DraftKind = Literal["rewrite", "generated", "text_story", "manual", "article_workflow", "article_v1", "article_v2"]


class DraftInput(BaseModel):
    pipeline_id: Optional[str] = None
    wp_account_id: Optional[str] = None
    kind: DraftKind = "manual"
    source_url: Optional[str] = None
    language: Optional[str] = None
    title: str = ""
    content: str = ""
    caption: Optional[str] = None
    image_kind: Optional[Literal["upload", "url"]] = None
    image_source: Optional[str] = None
    content_format: Literal["plain", "html"] = "plain"
    category_id: Optional[str] = None
    wp_status: Literal["draft", "publish"] = "draft"

    @model_validator(mode="after")
    def validate_image(self):
        if bool(self.image_kind) != bool(self.image_source):
            raise ValueError("image_kind and image_source must be provided together")
        return self


class DraftUpdate(DraftInput):
    version: int = Field(ge=1)


class DraftResponse(DraftInput):
    model_config = ConfigDict(from_attributes=True)

    id: str
    state: str
    error: Optional[str] = None
    version: int
    wp_media_id: Optional[str] = None
    wp_post_id: Optional[str] = None
    wp_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    wordpress_created_at: Optional[datetime] = None


class PublishDraftInput(BaseModel):
    confirmed: bool = False


class JobCapabilities(BaseModel):
    can_cancel: bool = False
    can_rerun: bool = False
    can_open_draft: bool = False
    can_copy_link: bool = False


class RewriteJobInput(BaseModel):
    pipeline_id: str
    source_url: str = Field(min_length=8)
    use_proxy: bool = False
    use_enrichment: bool = False
    rerun_from_job_id: Optional[str] = None


class ArticleWorkflowRunInput(BaseModel):
    pipeline_id: str
    source_url: str = Field(min_length=8)
    mode: Literal["v1", "v2"] = "v2"
    use_proxy: bool = False
    use_enrichment: bool = False
    rerun_from_job_id: Optional[str] = None


class GenerationJobInput(BaseModel):
    pipeline_id: str


class WorkflowJobCreated(BaseModel):
    job_id: str
    draft_id: str
    status: str


class CategoryResponse(BaseModel):
    id: Union[int, str]
    name: str
    count: int = 0


class DraftListResponse(BaseModel):
    items: List[DraftResponse]
    total: int
