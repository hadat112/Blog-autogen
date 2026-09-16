import os
from urllib.parse import quote, urlparse

import yaml


TRANSLATION_MODE_CHOICES = ["sequential", "parallel"]
DEFAULT_TRANSLATION_MODE = "sequential"
DEFAULT_TRANSLATION_MAX_CONCURRENCY = 2
DEFAULT_AI_REQUEST_TIMEOUT = 300
DEFAULT_TRANSLATION_CHUNK_SIZE = 6000


def normalize_proxy_url(value):
    proxy_url = str(value or "").strip()
    if not proxy_url:
        return ""
    if "://" not in proxy_url:
        parts = proxy_url.split(":", 3)
        if len(parts) not in {2, 4} or not parts[0] or not parts[1]:
            raise ValueError(
                "Proxy must be http(s)://... or host:port[:username:password]"
            )
        host, port = parts[:2]
        if len(parts) == 4 and (not parts[2] or not parts[3]):
            raise ValueError("Proxy username and password cannot be empty")
        credentials = (
            f"{quote(parts[2], safe='')}:{quote(parts[3], safe='')}@"
            if len(parts) == 4
            else ""
        )
        proxy_url = f"http://{credentials}{host}:{port}"
    parsed = urlparse(proxy_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Proxy URL must use http:// or https:// and include a host")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Proxy URL contains an invalid port") from exc
    return proxy_url


def normalize_proxy_urls(values):
    if isinstance(values, str):
        values = values.splitlines()
    if values is None:
        values = []
    normalized = []
    for value in values:
        proxy_url = normalize_proxy_url(value)
        if proxy_url and proxy_url not in normalized:
            normalized.append(proxy_url)
    return normalized


def normalize_translation_mode(value):
    mode = str(value or DEFAULT_TRANSLATION_MODE).strip().lower()
    return mode if mode in TRANSLATION_MODE_CHOICES else DEFAULT_TRANSLATION_MODE


def normalize_translation_max_concurrency(value):
    try:
        concurrency = int(value)
    except (TypeError, ValueError):
        concurrency = DEFAULT_TRANSLATION_MAX_CONCURRENCY
    return max(1, min(concurrency, 8))


def normalize_ai_request_timeout(value):
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_AI_REQUEST_TIMEOUT
    return max(30, min(timeout, 900))


def normalize_translation_chunk_size(value):
    try:
        chunk_size = int(value)
    except (TypeError, ValueError):
        chunk_size = DEFAULT_TRANSLATION_CHUNK_SIZE
    return max(1000, min(chunk_size, 30000))


class SettingsManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.normalize()

    def load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def normalize(self):
        self.config["translation_mode"] = normalize_translation_mode(
            self.config.get("translation_mode")
        )
        self.config["translation_max_concurrency"] = normalize_translation_max_concurrency(
            self.config.get("translation_max_concurrency")
        )
        self.config["ai_request_timeout"] = normalize_ai_request_timeout(
            self.config.get("ai_request_timeout")
        )
        self.config["translation_chunk_size"] = normalize_translation_chunk_size(
            self.config.get("translation_chunk_size")
        )

    def save_config(self):
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config, f)
