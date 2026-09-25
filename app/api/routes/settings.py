import os

from fastapi import APIRouter, Depends, HTTPException
import requests
from sqlalchemy.orm import Session

from app.api import schemas
from app.domain.settings_manager import (
    SettingsManager,
    normalize_ai_request_timeout,
    normalize_translation_chunk_size,
    normalize_translation_max_concurrency,
    normalize_translation_mode,
    normalize_auto_collect_patterns,
    normalize_ai_enrichment,
    normalize_proxy_url,
    normalize_proxy_urls,
)
from app.db import models
from app.db.session import get_db
from app.db.session import engine
from app.services.proxy_settings_service import ProxySettingsService


router = APIRouter()


@router.get("/settings/database-info")
def get_database_info(db: Session = Depends(get_db)):
    database = engine.url.database
    size_bytes = None
    if database and database != ":memory:" and os.path.isfile(database):
        size_bytes = os.path.getsize(database)
    return {
        "size_bytes": size_bytes,
        "database": os.path.basename(database) if database and database != ":memory:" else "memory",
        "articles": db.query(models.Article).count(),
        "enrichments": db.query(models.ArticleEnrichment).count(),
        "jobs": db.query(models.Job).count(),
        "drafts": db.query(models.ContentDraft).count(),
    }


def _settings_from_config(config: dict, proxy_urls=None) -> schemas.AppSettings:
    proxy_urls = proxy_urls if proxy_urls is not None else config.get("proxy_urls") or ([config.get("proxy_url")] if config.get("proxy_url") else [])
    return schemas.AppSettings(
        proxy_url=str(proxy_urls[0] if proxy_urls else ""),
        proxy_urls=proxy_urls,
        translation_mode=normalize_translation_mode(config.get("translation_mode")),
        translation_max_concurrency=normalize_translation_max_concurrency(
            config.get("translation_max_concurrency")
        ),
        ai_request_timeout=normalize_ai_request_timeout(config.get("ai_request_timeout")),
        translation_chunk_size=normalize_translation_chunk_size(
            config.get("translation_chunk_size")
        ),
        auto_collect_patterns=normalize_auto_collect_patterns(config.get("auto_collect_patterns")),
        default_ai_enrichment=normalize_ai_enrichment(config.get("default_ai_enrichment")),
        enrichment_ai_account_id=str(config.get("enrichment_ai_account_id") or ""),
    )


@router.get("/settings", response_model=schemas.AppSettings)
def get_settings(db: Session = Depends(get_db)):
    manager = SettingsManager()
    return _settings_from_config(manager.config, ProxySettingsService.get_urls(db))


@router.put("/settings", response_model=schemas.AppSettings)
def update_settings(settings: schemas.AppSettings, db: Session = Depends(get_db)):
    manager = SettingsManager()
    try:
        proxy_urls = normalize_proxy_urls(settings.proxy_urls or settings.proxy_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ProxySettingsService.save(db, proxy_urls)
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
    manager.config["auto_collect_patterns"] = normalize_auto_collect_patterns(
        settings.auto_collect_patterns
    )
    manager.config["default_ai_enrichment"] = normalize_ai_enrichment(
        settings.default_ai_enrichment
    )
    enrichment_account_id = (settings.enrichment_ai_account_id or "").strip()
    if enrichment_account_id:
        account = db.query(models.Account).filter(
            models.Account.id == enrichment_account_id,
            models.Account.type == "ai",
        ).first()
        if not account:
            raise HTTPException(status_code=400, detail="Selected enrichment account is invalid")
    manager.config["enrichment_ai_account_id"] = enrichment_account_id
    manager.save_config()
    return _settings_from_config(manager.config, proxy_urls)


@router.post("/settings/proxy/check")
def check_proxy(settings: schemas.ProxyCheckInput, db: Session = Depends(get_db)):
    try:
        proxy_urls = normalize_proxy_urls(settings.proxy_urls)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not proxy_urls:
        raise HTTPException(status_code=400, detail="No proxy is configured")

    for index, proxy_url in enumerate(proxy_urls):
        proxies = {"http": proxy_url, "https": proxy_url}
        try:
            response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=8)
            response.raise_for_status()
            ProxySettingsService.save(db, proxy_urls, selected=proxy_url)
            return {"ok": True, "proxy_index": index, "checked": len(proxy_urls)}
        except requests.RequestException:
            continue
    raise HTTPException(status_code=502, detail="No configured proxy is reachable")
