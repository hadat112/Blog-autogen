from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ThemeRuleInput(BaseModel):
    tag: str = Field(min_length=1, max_length=80)
    keywords: List[str] = Field(min_length=1)
    is_active: bool = True


class ThemeRuleResponse(ThemeRuleInput):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_url: str
    original_title: str
    theme_tags: List[str]
    structure: Optional[dict[str, Any]] = None
    word_count: int
    analysis_status: str
    analysis_error: Optional[str] = None
    processed_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    page: int
    page_size: int


class ArticleEnrichmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    article_id: str
    summary: Optional[str] = None
    plot_beats: Optional[Any] = None
    characters: Optional[Any] = None
    setting: Optional[Any] = None
    conflict: Optional[Any] = None
    emotional_arc: Optional[Any] = None
    creative_dna: Optional[Any] = None
    summary_status: str
    analysis_status: str
    dna_status: str
    summary_error: Optional[str] = None
    analysis_error: Optional[str] = None
    dna_error: Optional[str] = None
    ai_account_id: Optional[str] = None
    model: str = ""
    updated_at: datetime


class PatternSummaryResponse(BaseModel):
    total: int
    completed: int
    recoverable: int
    distinct_themes: int
