from types import SimpleNamespace

import app.domain.article_importer as importer


def test_raw_source_callback_runs_before_translation_and_cannot_fail_parent(monkeypatch):
    response = SimpleNamespace(url="https://source.test/story", text="<html></html>")
    monkeypatch.setattr(importer, "fetch_wp_post_by_slug", lambda *args: {"slug": "story", "title": {"rendered": "Original"}, "content": {"rendered": "<p>Original body long enough</p>"}, "featured_media": 0})
    monkeypatch.setattr(importer, "parse_wp_post_payload", lambda *args, **kwargs: {"title": "Original", "content": "Original body", "image_url": "https://img.test/a.jpg"})
    events = []

    class AI:
        def translate_article_fields(self, title, content, image, **kwargs):
            events.append("translated")
            return {"title": "Translated", "content": "Translated body", "caption": "", "image_url": image}

    def callback(raw):
        events.append(raw["title"])
        raise RuntimeError("pattern storage failed")

    result = importer._extract_wp_article_from_response(response, AI(), "Italian", source_callback=callback)
    assert events == ["Original", "translated"]
    assert result["title"] == "Translated"
