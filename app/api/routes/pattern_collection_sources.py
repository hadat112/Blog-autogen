from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db


router = APIRouter(prefix="/pattern-analysis-pipelines", tags=["pattern analysis"])


def _eligible_query(db):
    return db.query(models.Pipeline).filter(models.Pipeline.type.in_(("crawl", "rewrite")))


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    sources = []
    for pipeline in _eligible_query(db).order_by(models.Pipeline.name.asc()).all():
        ai_account_id = (pipeline.step_accounts or {}).get("ai")
        has_ai_account = bool(db.query(models.Account.id).filter(
            models.Account.id == ai_account_id,
            models.Account.type == "ai",
        ).first())
        sources.append({
            "pipeline_id": pipeline.id,
            "name": pipeline.name,
            "type": pipeline.type,
            "can_analyze": bool(pipeline.is_active and has_ai_account),
        })
    return sources
