from html.parser import HTMLParser
from urllib.parse import urljoin

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


def extract_article_from_url(article_url: str, ai_client, language: str = "Ukrainian") -> dict:
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

    clean_html = clean_article_html(response.text, response.url)
    article = ai_client.extract_article(clean_html, response.url, language=language)
    article["source_url"] = response.url
    return article
