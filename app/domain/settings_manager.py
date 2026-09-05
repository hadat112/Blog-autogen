import os

import yaml


TRANSLATION_MODE_CHOICES = ["sequential", "parallel"]
DEFAULT_TRANSLATION_MODE = "sequential"
DEFAULT_TRANSLATION_MAX_CONCURRENCY = 2
DEFAULT_AI_REQUEST_TIMEOUT = 300
DEFAULT_TRANSLATION_CHUNK_SIZE = 6000


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
