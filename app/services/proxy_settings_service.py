from app.db import models
from app.domain.settings_manager import normalize_proxy_urls


PROXY_URLS_KEY = "proxy_urls"
SELECTED_PROXY_KEY = "selected_proxy_url"


class ProxySettingsService:
    @staticmethod
    def _get(db, key):
        setting = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
        return setting.value if setting else None

    @classmethod
    def get_urls(cls, db):
        stored = cls._get(db, PROXY_URLS_KEY)
        if stored is None:
            return []
        try:
            return normalize_proxy_urls(stored)
        except ValueError:
            return []

    @classmethod
    def get_selected(cls, db):
        selected = cls._get(db, SELECTED_PROXY_KEY)
        if selected:
            try:
                selected = normalize_proxy_urls([selected])[0]
            except (IndexError, ValueError):
                selected = ""
        urls = cls.get_urls(db)
        return selected if selected in urls else (urls[0] if urls else "")

    @classmethod
    def save(cls, db, urls, selected=""):
        normalized = normalize_proxy_urls(urls)
        selected = selected if selected in normalized else (normalized[0] if normalized else "")
        for key, value in ((PROXY_URLS_KEY, normalized), (SELECTED_PROXY_KEY, selected)):
            setting = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
            if setting:
                setting.value = value
            else:
                db.add(models.AppSetting(key=key, value=value))
        db.commit()
        return normalized, selected
