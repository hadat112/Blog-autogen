from dataclasses import dataclass

from app.domain.article_importer import extract_article_from_url


@dataclass(frozen=True)
class SourceArticle:
    title: str
    content: str
    image_url: str
    source_url: str


class WordPressSourceGateway:
    def fetch(self, source_url: str) -> SourceArticle:
        result = extract_article_from_url(source_url, None, translate=False)
        return SourceArticle(
            title=(result.get("title") or "").strip(),
            content=(result.get("content") or "").strip(),
            image_url=(result.get("image_url") or "").strip(),
            source_url=(result.get("source_url") or source_url).strip(),
        )
