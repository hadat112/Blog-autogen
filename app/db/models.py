import uuid
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer, ForeignKey, Index, Text
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


class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)

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
    workflow_type = Column(String, nullable=False, default="legacy", server_default="legacy")
    parent_job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    draft_id = Column(String, ForeignKey("content_drafts.id"), nullable=True)
    outputs = Column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_jobs_workflow_status", "workflow_type", "status"),
        Index("ix_jobs_parent_job_id", "parent_job_id"),
    )


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id = Column(String, primary_key=True, default=generate_uuid)
    kind = Column(String, nullable=False)
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=True)
    wp_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    source_url = Column(String, nullable=True)
    language = Column(String, nullable=True)
    title = Column(String, default="", nullable=False)
    content = Column(Text, default="", nullable=False)
    caption = Column(Text, nullable=True)
    image_kind = Column(String, nullable=True)
    image_source = Column(String, nullable=True)
    content_format = Column(String, default="plain", nullable=False)
    category_id = Column(String, nullable=True)
    wp_status = Column(String, default="draft", nullable=False)
    state = Column(String, default="generating", nullable=False)
    wp_media_id = Column(String, nullable=True)
    wp_post_id = Column(String, nullable=True)
    wp_url = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    wordpress_created_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_content_drafts_kind_state", "kind", "state"),
        Index("ix_content_drafts_updated_at", "updated_at"),
    )


class TextStoryComposition(Base):
    __tablename__ = "text_story_compositions"

    id = Column(String, primary_key=True, default=generate_uuid)
    draft_id = Column(String, ForeignKey("content_drafts.id"), nullable=False, unique=True)
    source_text = Column(Text, nullable=False)
    rewrite_text = Column(Text, default="", nullable=False)
    continuation_text = Column(Text, default="", nullable=False)
    image_prompt = Column(Text, default="", nullable=False)
    prompt_version = Column(String, nullable=False)
    stage_status = Column(JSON, default=dict, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_url = Column(String, nullable=False, unique=True)
    source_slug = Column(String, nullable=True, index=True)
    source_title = Column(String, default="", nullable=False)
    source_content = Column(Text, default="", nullable=False)
    source_image_url = Column(String, default="", nullable=False)
    source_language = Column(String, default="", nullable=False)
    source_content_hash = Column(String, default="", nullable=False)
    source_fetched_at = Column(DateTime, nullable=True)
    original_title = Column(String, default="", nullable=False)
    theme_tags = Column(JSON, default=list, nullable=False)
    structure = Column(JSON, nullable=True)
    word_count = Column(Integer, default=0, nullable=False)
    analysis_status = Column(String, default="pending", nullable=False)
    analysis_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_articles_analysis_processed", "analysis_status", "processed_at"),
    )


class ArticleEnrichment(Base):
    __tablename__ = "article_enrichments"

    id = Column(String, primary_key=True, default=generate_uuid)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=True)
    plot_beats = Column(JSON, nullable=True)
    characters = Column(JSON, nullable=True)
    setting = Column(JSON, nullable=True)
    conflict = Column(JSON, nullable=True)
    emotional_arc = Column(JSON, nullable=True)
    creative_dna = Column(JSON, nullable=True)
    summary_status = Column(String, default="missing", nullable=False)
    analysis_status = Column(String, default="missing", nullable=False)
    dna_status = Column(String, default="missing", nullable=False)
    summary_error = Column(Text, nullable=True)
    analysis_error = Column(Text, nullable=True)
    dna_error = Column(Text, nullable=True)
    ai_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    model = Column(String, default="", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ThemeRule(Base):
    __tablename__ = "theme_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    tag = Column(String, nullable=False, unique=True)
    keywords = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
