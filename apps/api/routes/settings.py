from fastapi import APIRouter

from apps.api import schemas
from core.config_manager import (
    ConfigManager,
    _normalize_translation_max_concurrency,
    _normalize_translation_mode,
)


router = APIRouter()


def _settings_from_config(config: dict) -> schemas.AppSettings:
    return schemas.AppSettings(
        translation_mode=_normalize_translation_mode(config.get("translation_mode")),
        translation_max_concurrency=_normalize_translation_max_concurrency(
            config.get("translation_max_concurrency")
        ),
    )


@router.get("/settings", response_model=schemas.AppSettings)
def get_settings():
    manager = ConfigManager()
    return _settings_from_config(manager.config)


@router.put("/settings", response_model=schemas.AppSettings)
def update_settings(settings: schemas.AppSettings):
    manager = ConfigManager()
    manager.config["translation_mode"] = _normalize_translation_mode(settings.translation_mode)
    manager.config["translation_max_concurrency"] = _normalize_translation_max_concurrency(
        settings.translation_max_concurrency
    )
    manager.save_config()
    return _settings_from_config(manager.config)
