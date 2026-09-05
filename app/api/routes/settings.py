from fastapi import APIRouter

from app.api import schemas
from app.domain.settings_manager import (
    SettingsManager,
    normalize_ai_request_timeout,
    normalize_translation_chunk_size,
    normalize_translation_max_concurrency,
    normalize_translation_mode,
)


router = APIRouter()


def _settings_from_config(config: dict) -> schemas.AppSettings:
    return schemas.AppSettings(
        translation_mode=normalize_translation_mode(config.get("translation_mode")),
        translation_max_concurrency=normalize_translation_max_concurrency(
            config.get("translation_max_concurrency")
        ),
        ai_request_timeout=normalize_ai_request_timeout(config.get("ai_request_timeout")),
        translation_chunk_size=normalize_translation_chunk_size(
            config.get("translation_chunk_size")
        ),
    )


@router.get("/settings", response_model=schemas.AppSettings)
def get_settings():
    manager = SettingsManager()
    return _settings_from_config(manager.config)


@router.put("/settings", response_model=schemas.AppSettings)
def update_settings(settings: schemas.AppSettings):
    manager = SettingsManager()
    manager.config["translation_mode"] = normalize_translation_mode(settings.translation_mode)
    manager.config["translation_max_concurrency"] = normalize_translation_max_concurrency(
        settings.translation_max_concurrency
    )
    manager.config["ai_request_timeout"] = normalize_ai_request_timeout(
        settings.ai_request_timeout
    )
    manager.config["translation_chunk_size"] = normalize_translation_chunk_size(
        settings.translation_chunk_size
    )
    manager.save_config()
    return _settings_from_config(manager.config)
