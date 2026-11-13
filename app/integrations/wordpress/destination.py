import mimetypes
import base64
import re
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.auth import HTTPBasicAuth
from app.services.error_sanitizer import sanitize_error


ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def detect_image_mime(header):
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image_signature(header, declared_mime=None):
    detected = detect_image_mime(header)
    if not detected or (declared_mime and declared_mime != detected):
        raise ValueError("Image content does not match a supported MIME type")
    return detected


class AmbiguousWordPressResult(RuntimeError):
    pass


class WordPressDestinationGateway:
    def __init__(self, config, session=None, remote_proxy_url=""):
        self.url = (config.get("url") or "").rstrip("/")
        self.auth = HTTPBasicAuth(config.get("username"), config.get("password") or config.get("app_password"))
        self.session = session or requests.Session()
        self.session.max_redirects = 3
        self.remote_proxy_url = remote_proxy_url or ""

    def _raise_for_status(self, response):
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Keep useful WP codes without recording raw HTML, headers, or
            # arbitrary response objects that could contain credentials.
            details = ""
            try:
                body = response.json()
                if isinstance(body, dict):
                    details = ": ".join(str(body[key]) for key in ("code", "message")
                                        if isinstance(body.get(key), str))
            except ValueError:
                pass
            if not details and "html" in response.headers.get("Content-Type", "").lower():
                details = "Server returned an HTML rejection; check hosting/firewall logs"
            message = f"WordPress HTTP {response.status_code}: {details or 'Request rejected'}"
            basic = base64.b64encode(f"{self.auth.username}:{self.auth.password}".encode('latin1')).decode('ascii')
            message = re.sub(r"(Basic\s+)[^\s,;]+", r"\1[redacted]", message, flags=re.IGNORECASE)
            for secret in (basic, self.auth.password):
                if secret:
                    message = message.replace(str(secret), "[redacted]")
            message = " ".join(sanitize_error(message).split())[:450]
            raise requests.HTTPError(message, response=response, request=exc.request) from exc

    def categories(self):
        response = self.session.get(
            f"{self.url}/wp-json/wp/v2/categories",
            auth=self.auth,
            params={"per_page": 100},
            timeout=15,
        )
        self._raise_for_status(response)
        return response.json()

    def _upload_bytes(self, content, filename, mime):
        if mime not in ALLOWED_IMAGE_MIME:
            raise ValueError("Image must be JPEG, PNG, WebP, or GIF")
        response = self.session.post(
            f"{self.url}/wp-json/wp/v2/media",
            auth=self.auth,
            headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
            data=content,
            timeout=60,
        )
        self._raise_for_status(response)
        return str(response.json()["id"])

    def upload_file(self, source):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError("Uploaded image is unavailable")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds the 10 MiB limit")
        declared = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as handle:
            mime = validate_image_signature(handle.read(16), declared)
            handle.seek(0)
            return self._upload_bytes(handle, path.name, mime)

    def upload_remote(self, source):
        parsed = urlsplit(source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Remote image must use HTTP(S)")
        if parsed.username or parsed.password:
            raise ValueError("Remote image URL cannot contain credentials")
        proxies = {"http": self.remote_proxy_url, "https": self.remote_proxy_url} if self.remote_proxy_url else None
        with self.session.get(source, stream=True, timeout=(10, 30), allow_redirects=True, proxies=proxies) as response:
            response.raise_for_status()
            final_url = urlsplit(response.url)
            if final_url.scheme not in {"http", "https"} or final_url.username or final_url.password:
                raise ValueError("Remote image redirect target is not allowed")
            mime = (response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
            if mime not in ALLOWED_IMAGE_MIME:
                raise ValueError("Remote resource is not a supported image")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds the 10 MiB limit")
            chunks = []
            size = 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise ValueError("Image exceeds the 10 MiB limit")
                chunks.append(chunk)
        filename = Path(parsed.path).name or "featured-image"
        extension = mimetypes.guess_extension(mime) or ""
        if not Path(filename).suffix:
            filename += extension
        content = b"".join(chunks)
        validate_image_signature(content[:16], mime)
        return self._upload_bytes(content, filename, mime)

    def create_post(self, title, content, status="draft", category_id=None, media_id=None):
        payload = {"title": title, "content": content, "status": status}
        if category_id:
            payload["categories"] = [int(category_id)]
        if media_id:
            payload["featured_media"] = int(media_id)
        try:
            response = self.session.post(
                f"{self.url}/wp-json/wp/v2/posts",
                auth=self.auth,
                json=payload,
                timeout=30,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise AmbiguousWordPressResult("WordPress may have created the post; verify it before retrying") from exc
        self._raise_for_status(response)
        result = response.json()
        return {"id": str(result["id"]), "link": result["link"], "status": result.get("status", status)}
