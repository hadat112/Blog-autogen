import json
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from infrastructure.db import models


DEFAULT_LANGUAGES_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "default_languages.json"
)


def load_default_languages():
    with DEFAULT_LANGUAGES_PATH.open(encoding="utf-8") as default_file:
        return json.load(default_file)


def validate_language_code(code: str) -> str:
    normalized = (code or "").strip().lower()
    if not normalized or len(normalized) > 12:
        raise ValueError("Language code must contain 1 to 12 characters")
    if not normalized.replace("-", "").isalnum():
        raise ValueError("Language code may only contain letters, numbers, and hyphens")
    return normalized


class LanguageService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_defaults(self):
        defaults = load_default_languages()
        existing_codes = {
            code for (code,) in self.db.query(models.Language.code).all()
        }
        missing = [
            models.Language(
                code=language["code"],
                display_name=language["display_name"],
                is_active=True,
            )
            for language in defaults
            if language["code"] not in existing_codes
        ]
        if missing:
            self.db.add_all(missing)
            self.db.commit()

    def list_languages(self):
        self.ensure_defaults()
        return self.db.query(models.Language).order_by(models.Language.created_at).all()

    def get_language(self, code: str):
        return self.db.query(models.Language).filter(
            models.Language.code == validate_language_code(code)
        ).first()

    def resolve_language(self, value: str):
        normalized = (value or "").strip()
        if not normalized:
            return None
        return self.db.query(models.Language).filter(
            (func.lower(models.Language.code) == normalized.lower())
            | (func.lower(models.Language.display_name) == normalized.lower())
        ).first()

    def create_language(self, language_data):
        code = validate_language_code(language_data.code)
        if self.get_language(code):
            raise ValueError(f"Language code '{code}' already exists")
        display_name = language_data.display_name.strip()
        if not display_name:
            raise ValueError("Language name is required")
        duplicate_name = self.resolve_language(display_name)
        if duplicate_name:
            raise ValueError(f"Language name '{display_name}' already exists")

        language = models.Language(
            code=code,
            display_name=display_name,
            is_active=language_data.is_active,
        )
        self.db.add(language)
        self.db.commit()
        self.db.refresh(language)
        return language

    def update_language(self, code: str, language_data):
        language = self.get_language(code)
        if not language:
            return None

        display_name = language_data.display_name.strip()
        if not display_name:
            raise ValueError("Language name is required")
        duplicate_name = self.resolve_language(display_name)
        if duplicate_name and duplicate_name.code != language.code:
            raise ValueError(f"Language name '{display_name}' already exists")
        language.display_name = display_name
        language.is_active = language_data.is_active
        self.db.commit()
        self.db.refresh(language)
        return language
