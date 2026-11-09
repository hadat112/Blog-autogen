"""Character bounds shared by API and translation clients."""
MIN_TRANSLATION_CHARS = 1000
MAX_TRANSLATION_CHARS = 50000
DEFAULT_TRANSLATION_CHARS = 50000

def normalize_translation_chars(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_TRANSLATION_CHARS
    return max(MIN_TRANSLATION_CHARS, min(value, MAX_TRANSLATION_CHARS))


def resolve_translation_chunk_size(account_config, app_settings):
    """A blank account limit inherits the application's character threshold."""
    value = (account_config or {}).get("translation_chunk_size")
    if value is None or value == "":
        value = (app_settings or {}).get("translation_chunk_size", DEFAULT_TRANSLATION_CHARS)
    return normalize_translation_chars(value)


def normalize_account_character_limit(config):
    """Validate an optional account override without changing other settings."""
    config = dict(config or {})
    value = config.get("translation_chunk_size")
    if value is None or (isinstance(value, str) and not value.strip()):
        config.pop("translation_chunk_size", None)
        return config
    try:
        if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
            raise ValueError()
        parsed = int(value)
        if not MIN_TRANSLATION_CHARS <= parsed <= MAX_TRANSLATION_CHARS:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Characters per request must be an integer from 1,000 to 50,000") from None
    config["translation_chunk_size"] = parsed
    return config
