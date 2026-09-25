from html.parser import HTMLParser
from html import unescape
import inspect
import logging
import os
import re
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import yaml


logger = logging.getLogger(__name__)
_MIN_SOURCE_CONTENT_CHARS = 12


class _ArticleHTMLCleaner(HTMLParser):
    SKIP_TAGS = {"script", "style", "nav", "footer", "aside", "iframe", "noscript"}
    KEEP_TAGS = {"article", "main", "section", "h1", "h2", "h3", "p", "a", "img", "figure", "figcaption", "time", "meta"}

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag not in self.KEEP_TAGS:
            return

        attrs_dict = dict(attrs)
        kept = []
        if tag == "img" and attrs_dict.get("src"):
            kept.append(("src", urljoin(self.base_url, attrs_dict["src"])))
            if attrs_dict.get("alt"):
                kept.append(("alt", attrs_dict["alt"]))
        elif tag == "a" and attrs_dict.get("href"):
            kept.append(("href", urljoin(self.base_url, attrs_dict["href"])))
        elif tag == "meta":
            name = attrs_dict.get("name") or attrs_dict.get("property")
            content = attrs_dict.get("content")
            if name and content and (name.startswith("og:") or name in {"description", "author"}):
                kept.append(("name", name))
                kept.append(("content", content))

        attrs_text = "".join(f' {name}="{value}"' for name, value in kept)
        self.parts.append(f"<{tag}{attrs_text}>")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth or tag not in self.KEEP_TAGS or tag == "meta":
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def clean_article_html(html: str, base_url: str) -> str:
    parser = _ArticleHTMLCleaner(base_url)
    parser.feed(html or "")
    return "\n".join(parser.parts).strip()


class _BlockTextExtractor(HTMLParser):
    BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "figcaption"}
    SKIP_TAGS = {"script", "style", "noscript", "iframe"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.current_tag = None
        self.current_parts = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "br" and self.current_tag:
            self.current_parts.append("\n")
            return
        if tag in self.BLOCK_TAGS:
            self.current_tag = tag
            self.current_parts = []

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth or tag != self.current_tag:
            return

        text = " ".join(" ".join(self.current_parts).split())
        if text:
            self.blocks.append(text)
        self.current_tag = None
        self.current_parts = []

    def handle_data(self, data):
        if self.skip_depth or not self.current_tag:
            return
        text = " ".join(data.split())
        if text:
            self.current_parts.append(text)


def strip_html_preserve_paragraphs(html: str) -> str:
    parser = _BlockTextExtractor()
    parser.feed(html or "")
    if parser.blocks:
        return "\n\n".join(parser.blocks).strip()

    text = re.sub(r"<[^>]+>", " ", html or "")
    return unescape(" ".join(text.split())).strip()


def _extract_html_attr(html: str, name: str):
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", re.IGNORECASE)
        if match:
            return unescape(match.group(1)).strip()
    return ""


def _extract_html_title(html: str) -> str:
    title = _extract_html_attr(html, "og:title")
    if title:
        return title

    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", html or "", re.IGNORECASE | re.DOTALL)
    if match:
        return strip_html_preserve_paragraphs(match.group(1))

    match = re.search(r"<title\b[^>]*>(.*?)</title>", html or "", re.IGNORECASE | re.DOTALL)
    if match:
        return strip_html_preserve_paragraphs(match.group(1))

    return ""


def extract_wp_post_id(html: str, final_url: str = ""):
    match = re.search(r"/wp-json/wp/v2/posts/(\d+)", html or "")
    if match:
        return match.group(1)

    match = re.search(r"[?&]p=(\d+)", html or "")
    if match:
        return match.group(1)

    if final_url:
        parsed = urlparse(final_url)
        query_id = parse_qs(parsed.query).get("p", [None])[0]
        if query_id and query_id.isdigit():
            return query_id

    match = re.search(r"\b(?:post|postid)-(\d+)\b", html or "", re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _wp_api_base(final_url: str):
    parsed = urlparse(final_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/wp-json/wp/v2"


def _wp_rest_query_url(origin_api: str) -> str:
    return origin_api.removesuffix("/wp-json/wp/v2") + "/"


def _slug_from_url(final_url: str):
    path_parts = [part for part in urlparse(final_url).path.split("/") if part]
    return path_parts[-1] if path_parts else ""


def _wp_post_matches_slug(post_json: dict, expected_slug: str) -> bool:
    if not post_json or not expected_slug:
        return True

    returned_slug = (post_json.get("slug") or "").strip("/")
    if returned_slug:
        return returned_slug == expected_slug

    returned_link_slug = _slug_from_url(post_json.get("link") or "")
    if returned_link_slug:
        return returned_link_slug == expected_slug

    return True


def fetch_wp_post_json(origin_api: str, post_id: str, proxies=None):
    response = requests.get(
        f"{origin_api}/posts/{post_id}",
        params={"_embed": "1"},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
        proxies=proxies,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code not in {403, 404, 405}:
            raise
        fallback_url = _wp_rest_query_url(origin_api)
        logger.warning("WordPress REST path blocked; retrying query route: url=%s", fallback_url)
        response = requests.get(
            fallback_url,
            params={"rest_route": f"/wp/v2/posts/{post_id}"},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=30,
            proxies=proxies,
        )
        response.raise_for_status()
    return response.json()


def fetch_wp_post_by_slug(origin_api: str, slug: str, proxies=None):
    if not slug:
        return None
    response = requests.get(
        f"{origin_api}/posts",
        params={"slug": slug, "_embed": "1"},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
        proxies=proxies,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code not in {403, 404, 405}:
            raise
        fallback_url = _wp_rest_query_url(origin_api)
        logger.warning("WordPress REST path blocked; retrying query route: url=%s", fallback_url)
        response = requests.get(
            fallback_url,
            params={"rest_route": "/wp/v2/posts", "slug": slug, "_embed": "1"},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            timeout=30,
            proxies=proxies,
        )
        response.raise_for_status()
    posts = response.json()
    return posts[0] if posts else None


def _extract_embedded_image(post_json: dict):
    embedded = post_json.get("_embedded") or {}
    media_values = embedded.get("wp:featuredmedia") or []
    for media in media_values:
        image_url = media.get("source_url")
        if image_url:
            return image_url
    return ""


def _extract_yoast_image(post_json: dict):
    yoast = post_json.get("yoast_head_json") or {}
    images = yoast.get("og_image") or []
    for image in images:
        image_url = image.get("url")
        if image_url:
            return image_url
    return ""


def _fetch_featured_media_url(origin_api: str, post_json: dict, proxies=None):
    media_id = post_json.get("featured_media")
    if not media_id:
        return ""

    response = requests.get(
        f"{origin_api}/media/{media_id}",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
        proxies=proxies,
    )
    response.raise_for_status()
    return (response.json() or {}).get("source_url", "")


def parse_wp_post_payload(post_json: dict, original_html: str = "", origin_api: str = "", proxies=None):
    title = strip_html_preserve_paragraphs((post_json.get("title") or {}).get("rendered", ""))
    content = strip_html_preserve_paragraphs((post_json.get("content") or {}).get("rendered", ""))
    image_url = (
        _extract_embedded_image(post_json)
        or _extract_yoast_image(post_json)
        or post_json.get("jetpack_featured_media_url", "")
    )

    if not image_url and origin_api:
        try:
            image_url = _fetch_featured_media_url(origin_api, post_json, proxies=proxies)
        except Exception:
            image_url = ""

    if not image_url:
        image_url = _extract_html_attr(original_html, "og:image")

    return {
        "title": title.strip(),
        "content": content.strip(),
        "image_url": (image_url or "").strip(),
    }


def _has_usable_source_fields(fields: dict) -> bool:
    return bool((fields.get("title") or "").strip()) and len((fields.get("content") or "").strip()) >= _MIN_SOURCE_CONTENT_CHARS


def _parse_defuddle_response(response_text: str, source_url: str) -> dict:
    frontmatter = {}
    content = (response_text or "").strip()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()

    return {
        "title": str(frontmatter.get("title") or "").strip(),
        "content": content,
        "image_url": str(frontmatter.get("image") or "").strip(),
        "source_url": str(frontmatter.get("source") or source_url).strip(),
        "language": str(frontmatter.get("language") or "").strip(),
    }


def _fetch_defuddle_article(source_url: str, proxies=None):
    endpoint = f"https://defuddle.md/{source_url}"
    headers = {"User-Agent": "story-autogen/1.0"}
    api_key = os.getenv("DEFUDDLE_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(endpoint, headers=headers, timeout=60, proxies=proxies)
    response.raise_for_status()
    article = _parse_defuddle_response(response.text, source_url)
    if not _has_usable_source_fields(article):
        raise ValueError("Defuddle returned no usable article content")
    return article


def _supports_progress_callback(func) -> bool:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False

    return "progress_callback" in signature.parameters


def _extract_wp_article_from_response(
    response,
    ai_client,
    language: str,
    log_callback=None,
    translate: bool = True,
    source_callback=None,
    proxies=None,
):
    origin_api = _wp_api_base(response.url)
    if not origin_api:
        logger.warning("WordPress REST lookup skipped: invalid origin URL=%s", response.url)
        return None

    post_json = None
    try:
        requested_slug = _slug_from_url(response.url)
        if proxies:
            post_json = fetch_wp_post_by_slug(origin_api, requested_slug, proxies=proxies)
        else:
            post_json = fetch_wp_post_by_slug(origin_api, requested_slug)
        post_id = extract_wp_post_id(response.text, response.url)
        if post_json and not _wp_post_matches_slug(post_json, requested_slug):
            if log_callback:
                log_callback("Step 2: WordPress slug lookup returned a different post; retrying by post ID.")
            post_json = None
        if not post_json and post_id:
            if proxies:
                post_json = fetch_wp_post_json(origin_api, post_id, proxies=proxies)
            else:
                post_json = fetch_wp_post_json(origin_api, post_id)
    except Exception as exc:
        logger.warning(
            "WordPress REST lookup failed: type=%s message=%s source_url=%s",
            type(exc).__name__,
            exc,
            response.url,
        )
        return None

    if not post_json:
        logger.warning(
            "WordPress REST lookup returned no post: slug=%s source_url=%s",
            requested_slug,
            response.url,
        )
        return None

    fields = parse_wp_post_payload(
        post_json,
        original_html=response.text,
        origin_api=origin_api,
        proxies=proxies,
    )
    if not _has_usable_source_fields(fields):
        logger.warning(
            "WordPress REST post is missing or too short: title_present=%s content_chars=%s source_url=%s",
            bool(fields["title"]),
            len(fields["content"]),
            response.url,
        )
        return None

    if source_callback:
        try:
            source_callback({**fields, "source_url": response.url})
        except Exception:
            pass

    if not translate:
        if log_callback:
            log_callback("Step 2: Using original WordPress article without translation.")
        return {
            "title": fields["title"],
            "content": fields["content"],
            "caption": "",
            "image_url": fields["image_url"],
        }

    if log_callback:
        log_callback("Step 2: Translating article via AI...")

    if hasattr(ai_client, "translate_article_fields"):
        kwargs = {"language": language}
        if log_callback and _supports_progress_callback(ai_client.translate_article_fields):
            kwargs["progress_callback"] = log_callback

        return ai_client.translate_article_fields(
            fields["title"],
            fields["content"],
            fields["image_url"],
            **kwargs,
        )

    clean_html = f"<h1>{fields['title']}</h1>\n{fields['content']}"
    return ai_client.extract_article(clean_html, response.url, language=language)


def extract_article_from_url(
    article_url: str,
    ai_client,
    language: str = "Ukrainian",
    log_callback=None,
    translate: bool = True,
    source_callback=None,
    proxy_url=None,
) -> dict:
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    response = requests.get(
        article_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,app/services/xhtml+xml,app/services/xml;q=0.9,*/*;q=0.8",
        },
        timeout=30,
        allow_redirects=True,
        proxies=proxies,
    )
    response.raise_for_status()

    article = _extract_wp_article_from_response(
        response,
        ai_client,
        language,
        log_callback=log_callback,
        translate=translate,
        source_callback=source_callback,
        proxies=proxies,
    )
    if article is None:
        try:
            defuddle_fields = _fetch_defuddle_article(response.url, proxies=proxies)
            if source_callback:
                try:
                    source_callback(defuddle_fields)
                except Exception:
                    pass
            if not translate:
                article = {
                    "title": defuddle_fields["title"],
                    "content": defuddle_fields["content"],
                    "caption": "",
                    "image_url": defuddle_fields["image_url"],
                }
            elif hasattr(ai_client, "translate_article_fields"):
                kwargs = {"language": language}
                if log_callback and _supports_progress_callback(ai_client.translate_article_fields):
                    kwargs["progress_callback"] = log_callback
                if log_callback:
                    log_callback("Step 2: Translating Defuddle article via AI...")
                article = ai_client.translate_article_fields(
                    defuddle_fields["title"],
                    defuddle_fields["content"],
                    defuddle_fields["image_url"],
                    **kwargs,
                )
            else:
                clean_html = f"<h1>{defuddle_fields['title']}</h1>\n{defuddle_fields['content']}"
                article = ai_client.extract_article(clean_html, response.url, language=language)
            logger.info("Defuddle fallback succeeded: source_url=%s", response.url)
        except Exception as exc:
            logger.warning("Defuddle fallback failed: type=%s message=%s source_url=%s", type(exc).__name__, exc, response.url)
    if article is None and not translate:
        # Some WordPress sites serve the article HTML but block /wp-json/ with
        # a firewall. Preserve repost functionality by extracting the visible
        # article instead of treating a REST-only failure as a hard failure.
        clean_html = clean_article_html(response.text, response.url)
        html_title = _extract_html_title(response.text)
        html_content = strip_html_preserve_paragraphs(clean_html)
        if html_title and html_content:
            logger.warning(
                "WordPress REST unavailable; reposting from HTML fallback: title_present=%s content_chars=%s source_url=%s",
                bool(html_title),
                len(html_content),
                response.url,
            )
            return {
                "title": html_title,
                "content": html_content,
                "caption": "",
                "image_url": _extract_html_attr(response.text, "og:image"),
                "source_url": response.url,
            }
        raise ValueError(
            "Repost original requires a WordPress REST article with title and content. "
            "Check server logs for the REST status, content type, and lookup URL."
        )
    if article is None:
        clean_html = clean_article_html(response.text, response.url)
        if log_callback:
            log_callback("Step 2: Extracting and translating article via AI fallback...")
        article = ai_client.extract_article(clean_html, response.url, language=language)

    article["source_url"] = response.url
    return article
