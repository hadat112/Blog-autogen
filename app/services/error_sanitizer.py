import re


_CREDENTIAL_URL = re.compile(r"(https?://)([^/\s:@]+):([^@\s]+)@", re.IGNORECASE)
_BEARER_TOKEN = re.compile(r"(Bearer\s+)[^\s,;]+", re.IGNORECASE)
_API_KEY = re.compile(r"\b(sk-[a-zA-Z0-9_-]{8,}|key-[a-zA-Z0-9_-]{8,})\b", re.IGNORECASE)


def sanitize_error(value):
    if not isinstance(value, str):
        return value
    result = _CREDENTIAL_URL.sub(r"\1[redacted]@", value)
    result = _BEARER_TOKEN.sub(r"\1[redacted]", result)
    return _API_KEY.sub("[REDACTED]", result)
