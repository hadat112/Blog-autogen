from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.pattern_schemas import ThemeRuleInput, ThemeRuleResponse
from app.db.session import get_db
from app.services.theme_rule_service import ThemeRuleService


router = APIRouter(prefix="/theme-rules", tags=["theme rules"])


@router.get("", response_model=List[ThemeRuleResponse])
def list_rules(db: Session = Depends(get_db)):
    return ThemeRuleService(db).list()


@router.post("", response_model=ThemeRuleResponse)
def create_rule(data: ThemeRuleInput, db: Session = Depends(get_db)):
    try:
        return ThemeRuleService(db).create(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{rule_id}", response_model=ThemeRuleResponse)
def update_rule(rule_id: str, data: ThemeRuleInput, db: Session = Depends(get_db)):
    try:
        rule = ThemeRuleService(db).update(rule_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not rule:
        raise HTTPException(status_code=404, detail="Theme rule not found")
    return rule


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    if not ThemeRuleService(db).delete(rule_id):
        raise HTTPException(status_code=404, detail="Theme rule not found")
    return {"status": "ok"}
