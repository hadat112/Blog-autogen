from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.workflow_schemas import CollectionSourceUpdate
from app.db import models
from app.db.session import get_db


router = APIRouter(prefix="/pattern-collection-sources", tags=["pattern collection"])


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
            "collect_patterns": bool((pipeline.settings or {}).get("collect_patterns", False)),
            "can_analyze": bool(pipeline.is_active and has_ai_account),
        })
    return sources


@router.put("/{pipeline_id}")
def update_source(pipeline_id: str, data: CollectionSourceUpdate, db: Session = Depends(get_db)):
    pipeline = _eligible_query(db).filter(models.Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Eligible pipeline not found")
    settings = dict(pipeline.settings or {})
    settings["collect_patterns"] = data.collect_patterns
    pipeline.settings = settings
    db.commit()
    return {"pipeline_id": pipeline.id, "collect_patterns": data.collect_patterns}
