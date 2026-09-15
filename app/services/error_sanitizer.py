import re


_CREDENTIAL_URL = re.compile(r"(https?://)([^/\s:@]+):([^@\s]+)@", re.IGNORECASE)
_BEARER_TOKEN = re.compile(r"(Bearer\s+)[^\s,;]+", re.IGNORECASE)


def sanitize_error(value):
    if not isinstance(value, str):
        return value
    result = _CREDENTIAL_URL.sub(r"\1[redacted]@", value)
    return _BEARER_TOKEN.sub(r"\1[redacted]", result)
