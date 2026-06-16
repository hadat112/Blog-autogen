from html.parser import HTMLParser
from html import unescape
import inspect
import re
from urllib.parse import parse_qs, urljoin, urlparse

import requests


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


def fetch_wp_post_json(origin_api: str, post_id: str):
    response = requests.get(
        f"{origin_api}/posts/{post_id}",
        params={"_embed": "1"},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_wp_post_by_slug(origin_api: str, slug: str):
    if not slug:
        return None
    response = requests.get(
        f"{origin_api}/posts",
        params={"slug": slug, "_embed": "1"},
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
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


def _fetch_featured_media_url(origin_api: str, post_json: dict):
    media_id = post_json.get("featured_media")
    if not media_id:
        return ""

    response = requests.get(
        f"{origin_api}/media/{media_id}",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        timeout=30,
    )
    response.raise_for_status()
    return (response.json() or {}).get("source_url", "")


def parse_wp_post_payload(post_json: dict, original_html: str = "", origin_api: str = ""):
    title = strip_html_preserve_paragraphs((post_json.get("title") or {}).get("rendered", ""))
    content = strip_html_preserve_paragraphs((post_json.get("content") or {}).get("rendered", ""))
    image_url = (
        _extract_embedded_image(post_json)
        or _extract_yoast_image(post_json)
        or post_json.get("jetpack_featured_media_url", "")
    )

    if not image_url and origin_api:
        try:
            image_url = _fetch_featured_media_url(origin_api, post_json)
        except Exception:
            image_url = ""

    if not image_url:
        image_url = _extract_html_attr(original_html, "og:image")

    return {
        "title": title.strip(),
        "content": content.strip(),
        "image_url": (image_url or "").strip(),
    }


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
):
    origin_api = _wp_api_base(response.url)
    if not origin_api:
        return None

    post_json = None
    try:
        requested_slug = _slug_from_url(response.url)
        post_json = fetch_wp_post_by_slug(origin_api, requested_slug)
        post_id = extract_wp_post_id(response.text, response.url)
        if post_json and not _wp_post_matches_slug(post_json, requested_slug):
            if log_callback:
                log_callback("Step 2: WordPress slug lookup returned a different post; retrying by post ID.")
            post_json = None
        if not post_json and post_id:
            post_json = fetch_wp_post_json(origin_api, post_id)
    except Exception:
        return None

    if not post_json:
        return None

    fields = parse_wp_post_payload(post_json, original_html=response.text, origin_api=origin_api)
    if not fields["title"] or not fields["content"]:
        return None

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
) -> dict:
    response = requests.get(
        article_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    article = _extract_wp_article_from_response(
        response,
        ai_client,
        language,
        log_callback=log_callback,
        translate=translate,
    )
    if article is None and not translate:
        raise ValueError("Repost original requires a WordPress REST article with title and content.")
    if article is None:
        clean_html = clean_article_html(response.text, response.url)
        if log_callback:
            log_callback("Step 2: Extracting and translating article via AI fallback...")
        article = ai_client.extract_article(clean_html, response.url, language=language)

    article["source_url"] = response.url
    return article
