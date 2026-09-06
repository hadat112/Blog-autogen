import threading
from datetime import datetime

from app.db import models
from app.db.session import SessionLocal
from app.domain.pattern_analyzer import PatternAnalyzer
from app.domain.theme_matcher import match_theme_tags
from app.services.ai_client_factory import create_ai_client
from app.services.article_service import ArticleService
from app.services.workflow_job_service import WorkflowJobService
from app.integrations.wordpress.source import WordPressSourceGateway


class PatternCollectionService:
    def __init__(self, db):
        self.db = db

    def collect(self, article_data, pipeline_id, parent_job_id=None, ai_account_id=None):
        rules = self.db.query(models.ThemeRule).filter(models.ThemeRule.is_active.is_(True)).all()
        tags = match_theme_tags(article_data.get("title"), article_data.get("content"), rules)
        article = ArticleService(self.db).upsert(
            article_data.get("source_url"), article_data.get("title"), article_data.get("content"), tags
        )
        if not ai_account_id:
            article.analysis_status = "failed"
            article.analysis_error = "AI account is unavailable"
            self.db.commit()
            return article, None
        job = WorkflowJobService(self.db).create(
            pipeline_id, "pattern_analysis", parent_job_id=parent_job_id, input_text=article.source_url
        )
        thread = threading.Thread(
            target=self._analyze_in_background,
            args=(article.id, job.id, ai_account_id, article_data.get("content") or ""),
            daemon=True,
        )
        thread.start()
        return article, job

    @staticmethod
    def _analyze_in_background(article_id, job_id, ai_account_id, source_content=None):
        with SessionLocal() as db:
            article = db.query(models.Article).filter(models.Article.id == article_id).first()
            account = db.query(models.Account).filter(models.Account.id == ai_account_id, models.Account.type == "ai").first()
            jobs = WorkflowJobService(db)
            if not article or not account:
                if article:
                    article.analysis_status = "failed"
                    article.analysis_error = "AI account is unavailable"
                    db.commit()
                jobs.fail(job_id, "Pattern analysis source or AI account is unavailable")
                return
            article.analysis_status = "processing"
            article.analysis_error = None
            db.commit()
            jobs.progress(job_id, "Analyze story structure", 20)
            try:
                content = source_content
                if not content:
                    content = WordPressSourceGateway().fetch(article.source_url).content
                structure = PatternAnalyzer(create_ai_client(account)).analyze(article.original_title, content)
                current_job = db.query(models.Job).populate_existing().filter(models.Job.id == job_id).first()
                if not current_job or current_job.status == "cancelled":
                    article.analysis_status = "failed"
                    article.analysis_error = "Analysis was cancelled"
                    db.commit()
                    return
                article.structure = structure
                article.analysis_status = "completed"
                article.updated_at = datetime.utcnow()
                db.commit()
                jobs.complete(job_id, {"article_id": article.id})
            except Exception as exc:
                article.analysis_status = "failed"
                article.analysis_error = str(exc)[:500]
                article.updated_at = datetime.utcnow()
                db.commit()
                jobs.fail(job_id, exc)

    def retry(self, article_id, pipeline_id, ai_account_id):
        article = ArticleService(self.db).get(article_id)
        if not article:
            return None
        if article.analysis_status not in {"pending", "failed"}:
            raise ValueError("Only incomplete or failed analysis can be retried")
        job = WorkflowJobService(self.db).create(pipeline_id, "pattern_analysis", input_text=article.source_url)
        threading.Thread(
            target=self._analyze_in_background,
            args=(article.id, job.id, ai_account_id, None),
            daemon=True,
        ).start()
        return job
