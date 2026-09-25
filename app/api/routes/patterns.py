from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.pattern_schemas import ArticleEnrichmentResponse, ArticleListResponse, ArticleResponse, PatternSummaryResponse
from app.db import models
from app.db.session import get_db
from app.services.article_service import ArticleService
from app.services.pattern_collection_service import PatternCollectionService
from app.services.article_enrichment_service import ArticleEnrichmentService
from app.domain.settings_manager import SettingsManager


router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/summary", response_model=PatternSummaryResponse)
def summary(db: Session = Depends(get_db)):
    total = db.query(models.Article).count()
    completed = db.query(models.Article).filter(models.Article.analysis_status == "completed").count()
    recoverable = db.query(models.Article).filter(models.Article.analysis_status.in_(("pending", "processing", "failed"))).count()
    tags = set()
    for (values,) in db.query(models.Article.theme_tags).all():
        tags.update(values or [])
    return {"total": total, "completed": completed, "recoverable": recoverable, "distinct_themes": len(tags)}


@router.get("", response_model=ArticleListResponse)
def list_patterns(
    q: Optional[str] = None,
    status: Optional[str] = None,
    theme: Optional[str] = None,
    sort: str = "processed_at",
    direction: str = "desc",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    try:
        items, total = ArticleService(db).search(q, status, theme, sort, direction, page, page_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": items, "total": total, "page": max(1, page), "page_size": min(100, max(1, page_size))}


@router.get("/{article_id}", response_model=ArticleResponse)
def get_pattern(article_id: str, db: Session = Depends(get_db)):
    article = ArticleService(db).get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return article


@router.get("/{article_id}/enrichment", response_model=ArticleEnrichmentResponse)
def get_enrichment(article_id: str, db: Session = Depends(get_db)):
    article = ArticleService(db).get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Pattern not found")
    enrichment = db.query(models.ArticleEnrichment).filter(models.ArticleEnrichment.article_id == article_id).first()
    if not enrichment:
        enrichment = models.ArticleEnrichment(article_id=article_id)
        db.add(enrichment)
        db.commit()
        db.refresh(enrichment)
    return enrichment


@router.post("/enrichment/bulk")
def enrich_missing(db: Session = Depends(get_db)):
    account_id = SettingsManager().config.get("enrichment_ai_account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Configure an enrichment AI account in Settings")
    articles = db.query(models.Article).all()
    queued = 0
    for article in articles:
        enrichment = db.query(models.ArticleEnrichment).filter(models.ArticleEnrichment.article_id == article.id).first()
        if not enrichment or enrichment.summary_status != "completed":
            if ArticleEnrichmentService.enqueue(article.id, ai_account_id=account_id):
                queued += 1
    return {"queued": queued}


@router.post("/{article_id}/enrichment/{step}")
def enqueue_enrichment(article_id: str, step: str, db: Session = Depends(get_db)):
    if step not in {"summary", "analysis", "dna"}:
        raise HTTPException(status_code=400, detail="Unsupported enrichment step")
    article = ArticleService(db).get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Pattern not found")
    account_id = SettingsManager().config.get("enrichment_ai_account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Configure an enrichment AI account in Settings")
    try:
        job = ArticleEnrichmentService.enqueue(article_id, ai_account_id=account_id, step=step)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": job.id if job else None, "status": "queued" if job else "already_complete"}


@router.delete("/{article_id}")
def delete_pattern(article_id: str, db: Session = Depends(get_db)):
    if not ArticleService(db).delete(article_id):
        raise HTTPException(status_code=404, detail="Pattern not found")
    return {"status": "ok"}


@router.post("/{article_id}/retry-analysis")
def retry_pattern(article_id: str, pipeline_id: str, db: Session = Depends(get_db)):
    pipeline = db.query(models.Pipeline).filter(
        models.Pipeline.id == pipeline_id,
        models.Pipeline.type.in_(("crawl", "rewrite")),
        models.Pipeline.is_active.is_(True),
    ).first()
    if not pipeline:
        raise HTTPException(status_code=400, detail="An eligible AI pipeline is required")
    ai_account_id = (pipeline.step_accounts or {}).get("ai")
    ai_account = db.query(models.Account.id).filter(
        models.Account.id == ai_account_id,
        models.Account.type == "ai",
    ).first()
    if not ai_account:
        raise HTTPException(status_code=400, detail="AI pipeline has no valid AI account")
    try:
        job = PatternCollectionService(db).retry(article_id, pipeline_id, ai_account_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return {"job_id": job.id, "status": job.status}
