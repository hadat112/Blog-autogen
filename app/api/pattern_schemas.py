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


class PatternSummaryResponse(BaseModel):
    total: int
    completed: int
    recoverable: int
    distinct_themes: int
