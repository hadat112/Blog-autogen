from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api import schemas
from application.language_service import LanguageService
from infrastructure.db.session import get_db


router = APIRouter()


@router.get("/languages", response_model=List[schemas.LanguageResponse])
def get_languages(db: Session = Depends(get_db)):
    return LanguageService(db).list_languages()


@router.post("/languages", response_model=schemas.LanguageResponse)
def create_language(language: schemas.LanguageCreate, db: Session = Depends(get_db)):
    try:
        return LanguageService(db).create_language(language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/languages/{code}", response_model=schemas.LanguageResponse)
def update_language(
    code: str,
    language: schemas.LanguageUpdate,
    db: Session = Depends(get_db),
):
    try:
        updated = LanguageService(db).update_language(code, language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Language not found")
    return updated
