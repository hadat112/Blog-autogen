"""Credential-scoped quota identities without keeping secrets in diagnostics."""
import hashlib
from urllib.parse import urlsplit, urlunsplit


def quota_identity(base_url, api_key):
    url = urlsplit((base_url or '').strip().rstrip('/'))
    endpoint = urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path, '', ''))
    return hashlib.sha256((endpoint + '\0' + (api_key or '')).encode()).hexdigest()


def normalize_concurrency(value):
    try:
        return max(1, min(int(value), 8))
    except (TypeError, ValueError):
        return 2
