from datetime import datetime
from urllib.parse import unquote, urlsplit, urlunsplit

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.db import models


SORT_FIELDS = {
    "processed_at": models.Article.processed_at,
    "updated_at": models.Article.updated_at,
    "word_count": models.Article.word_count,
    "title": models.Article.original_title,
}


def normalize_source_url(value):
    parsed = urlsplit((value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("A valid HTTP(S) source URL is required")
    if parsed.username or parsed.password:
        raise ValueError("Source URL cannot contain credentials")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def source_slug(value):
    path = urlsplit(value or "").path.rstrip("/")
    return unquote(path.rsplit("/", 1)[-1]).strip().lower()


class ArticleService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, article_id):
        return self.db.query(models.Article).filter(models.Article.id == article_id).first()

    def get_by_slug(self, slug):
        normalized_slug = (slug or "").strip().lower()
        if not normalized_slug:
            return None
        article = self.db.query(models.Article).filter(models.Article.source_slug == normalized_slug).first()
        if article:
            return article
        # Backward-compatible lookup for rows created before source_slug existed.
        for candidate in self.db.query(models.Article).filter(models.Article.source_slug.is_(None)).all():
            if source_slug(candidate.source_url) == normalized_slug:
                candidate.source_slug = normalized_slug
                self.db.commit()
                return candidate
        return None

    def upsert(self, source_url, title, content, tags):
        source_url = normalize_source_url(source_url)
        article = self.db.query(models.Article).filter(models.Article.source_url == source_url).first()
        if not article:
            article = models.Article(source_url=source_url, source_slug=source_slug(source_url))
            self.db.add(article)
        elif not article.source_slug:
            article.source_slug = source_slug(source_url)
        article.original_title = (title or "").strip()
        article.word_count = len((content or "").split())
        article.theme_tags = sorted(set(tags or []))
        article.analysis_status = "pending"
        article.analysis_error = None
        article.processed_at = datetime.utcnow()
        article.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(article)
        return article

    def search(self, query=None, status=None, theme=None, sort="processed_at", direction="desc", page=1, page_size=20):
        if sort not in SORT_FIELDS:
            raise ValueError("Unsupported sort field")
        if direction not in {"asc", "desc"}:
            raise ValueError("Sort direction must be asc or desc")
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        db_query = self.db.query(models.Article)
        if query:
            like = f"%{query.strip()}%"
            db_query = db_query.filter(or_(models.Article.original_title.ilike(like), models.Article.source_url.ilike(like)))
        if status:
            db_query = db_query.filter(models.Article.analysis_status == status)
        if theme:
            db_query = db_query.filter(text(
                "EXISTS (SELECT 1 FROM json_each(articles.theme_tags) WHERE json_each.value = :theme)"
            )).params(theme=theme)
        total = db_query.count()
        column = SORT_FIELDS[sort]
        db_query = db_query.order_by(column.asc() if direction == "asc" else column.desc())
        return db_query.offset((page - 1) * page_size).limit(page_size).all(), total

    def delete(self, article_id):
        article = self.get(article_id)
        if not article:
            return False
        self.db.delete(article)
        self.db.commit()
        return True
