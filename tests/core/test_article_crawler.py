import responses

from core.article_crawler import extract_article_from_url, extract_wp_post_id, parse_wp_post_payload


class FakeAI:
    def __init__(self):
        self.calls = []

    def extract_article(self, clean_html, article_url, language="Ukrainian"):
        self.calls.append((clean_html, article_url, language))
        return {
            "title": "Clean Title",
            "content": "Clean content",
            "caption": "Clean caption",
            "image_url": "https://source.test/image.jpg",
        }


class TranslatingAI(FakeAI):
    def __init__(self):
        super().__init__()
        self.translation_calls = []

    def translate_article_fields(self, title, content, image_url="", language="Ukrainian"):
        self.translation_calls.append((title, content, image_url, language))
        return {
            "title": f"{title} translated",
            "content": f"{content} translated",
            "caption": "",
            "image_url": image_url,
        }


def test_extract_wp_post_id_from_rest_link_and_shortlink():
    html = '<link rel="alternate" href="https://source.test/wp-json/wp/v2/posts/59423">'
    assert extract_wp_post_id(html, "https://source.test/story") == "59423"

    html = '<link rel="shortlink" href="https://source.test/?p=123">'
    assert extract_wp_post_id(html, "https://source.test/story") == "123"


def test_parse_wp_post_payload_prefers_embedded_image():
    payload = {
        "title": {"rendered": "Article <b>Title</b>"},
        "content": {"rendered": "<p>First paragraph.</p><p>Second paragraph.</p>"},
        "_embedded": {"wp:featuredmedia": [{"source_url": "https://source.test/image.jpg"}]},
    }

    article = parse_wp_post_payload(payload)

    assert article == {
        "title": "Article Title",
        "content": "First paragraph.\n\nSecond paragraph.",
        "image_url": "https://source.test/image.jpg",
    }


@responses.activate
def test_extract_article_from_url_fetches_cleans_html_and_adds_source_url():
    responses.add(
        responses.GET,
        "https://source.test/article",
        body="""
        <html>
          <head><title>Noise</title><script>alert('x')</script></head>
          <body>
            <nav>Menu noise</nav>
            <article>
              <h1>Clean Title</h1>
              <p>Clean paragraph.</p>
              <img src="/image.jpg">
            </article>
            <footer>Footer noise</footer>
          </body>
        </html>
        """,
        status=200,
        content_type="text/html",
    )
    ai = FakeAI()

    article = extract_article_from_url("https://source.test/article", ai)

    assert article["source_url"] == "https://source.test/article"
    assert article["title"] == "Clean Title"
    clean_html, article_url, language = ai.calls[0]
    assert article_url == "https://source.test/article"
    assert language == "Ukrainian"
    assert "Clean paragraph" in clean_html
    assert "https://source.test/image.jpg" in clean_html
    assert "Menu noise" not in clean_html
    assert "Footer noise" not in clean_html
    assert "alert" not in clean_html


@responses.activate
def test_extract_article_from_url_uses_wp_rest_when_post_id_exists():
    responses.add(
        responses.GET,
        "https://source.test/article",
        body="""
        <html>
          <head>
            <link rel="alternate" type="application/json" href="https://source.test/wp-json/wp/v2/posts/59423">
          </head>
          <body><article><h1>HTML title</h1></article></body>
        </html>
        """,
        status=200,
        content_type="text/html",
    )
    responses.add(
        responses.GET,
        "https://source.test/wp-json/wp/v2/posts?slug=article&_embed=1",
        json=[{
            "id": 59423,
            "title": {"rendered": "REST Title"},
            "content": {"rendered": "<p>REST paragraph one.</p><p>REST paragraph two.</p>"},
            "_embedded": {"wp:featuredmedia": [{"source_url": "https://source.test/rest-image.jpg"}]},
        }],
        status=200,
    )
    ai = TranslatingAI()
    log_messages = []

    article = extract_article_from_url("https://source.test/article", ai, language="Italian", log_callback=log_messages.append)

    assert article["source_url"] == "https://source.test/article"
    assert article["title"] == "REST Title translated"
    assert article["content"] == "REST paragraph one.\n\nREST paragraph two. translated"
    assert article["image_url"] == "https://source.test/rest-image.jpg"
    assert ai.calls == []
    assert ai.translation_calls == [
        (
            "REST Title",
            "REST paragraph one.\n\nREST paragraph two.",
            "https://source.test/rest-image.jpg",
            "Italian",
        )
    ]
    assert log_messages == ["Step 2: Translating article via AI..."]


@responses.activate
def test_extract_article_from_url_can_repost_wp_rest_without_translation():
    responses.add(
        responses.GET,
        "https://source.test/article-original",
        body="""
        <html>
          <head>
            <link rel="alternate" type="application/json" href="https://source.test/wp-json/wp/v2/posts/77">
          </head>
          <body><article><h1>HTML title</h1></article></body>
        </html>
        """,
        status=200,
        content_type="text/html",
    )
    responses.add(
        responses.GET,
        "https://source.test/wp-json/wp/v2/posts?slug=article-original&_embed=1",
        json=[{
            "id": 77,
            "title": {"rendered": "Original Title"},
            "content": {"rendered": "<p>Original paragraph one.</p><p>Original paragraph two.</p>"},
            "_embedded": {"wp:featuredmedia": [{"source_url": "https://source.test/original.jpg"}]},
        }],
        status=200,
    )
    ai = TranslatingAI()
    log_messages = []

    article = extract_article_from_url(
        "https://source.test/article-original",
        ai,
        language="",
        translate=False,
        log_callback=log_messages.append,
    )

    assert article == {
        "title": "Original Title",
        "content": "Original paragraph one.\n\nOriginal paragraph two.",
        "caption": "",
        "image_url": "https://source.test/original.jpg",
        "source_url": "https://source.test/article-original",
    }
    assert ai.calls == []
    assert ai.translation_calls == []
    assert log_messages == ["Step 2: Using original WordPress article without translation."]


@responses.activate
def test_extract_article_from_url_falls_back_to_post_id_when_slug_lookup_misses():
    responses.add(
        responses.GET,
        "https://source.test/category/article",
        body="""
        <html>
          <head>
            <link rel="alternate" type="application/json" href="https://source.test/wp-json/wp/v2/posts/59423">
          </head>
          <body><article><h1>HTML title</h1></article></body>
        </html>
        """,
        status=200,
        content_type="text/html",
    )
    responses.add(
        responses.GET,
        "https://source.test/wp-json/wp/v2/posts?slug=article&_embed=1",
        json=[],
        status=200,
    )
    responses.add(
        responses.GET,
        "https://source.test/wp-json/wp/v2/posts/59423?_embed=1",
        json={
            "title": {"rendered": "REST Title"},
            "content": {"rendered": "<p>REST paragraph one.</p><p>REST paragraph two.</p>"},
            "_embedded": {"wp:featuredmedia": [{"source_url": "https://source.test/rest-image.jpg"}]},
        },
        status=200,
    )
    ai = TranslatingAI()

    article = extract_article_from_url("https://source.test/category/article", ai, language="Italian")

    assert article["source_url"] == "https://source.test/category/article"
    assert article["title"] == "REST Title translated"
    assert article["content"] == "REST paragraph one.\n\nREST paragraph two. translated"
    assert article["image_url"] == "https://source.test/rest-image.jpg"
    assert ai.calls == []
    assert ai.translation_calls == [
        (
            "REST Title",
            "REST paragraph one.\n\nREST paragraph two.",
            "https://source.test/rest-image.jpg",
            "Italian",
        )
    ]


@responses.activate
def test_extract_article_from_url_falls_back_when_wp_rest_is_missing_content():
    responses.add(
        responses.GET,
        "https://source.test/article-fallback",
        body="""
        <html>
          <head>
            <link rel="alternate" href="https://source.test/wp-json/wp/v2/posts/99">
          </head>
          <body><article><h1>Clean Title</h1><p>Clean paragraph.</p></article></body>
        </html>
        """,
        status=200,
        content_type="text/html",
    )
    responses.add(
        responses.GET,
        "https://source.test/wp-json/wp/v2/posts?slug=article-fallback&_embed=1",
        json=[{"title": {"rendered": "REST Title"}, "content": {"rendered": ""}}],
        status=200,
    )
    ai = TranslatingAI()
    log_messages = []

    article = extract_article_from_url("https://source.test/article-fallback", ai, log_callback=log_messages.append)

    assert article["title"] == "Clean Title"
    assert ai.translation_calls == []
    assert len(ai.calls) == 1
    assert "Clean paragraph" in ai.calls[0][0]
    assert log_messages == ["Step 2: Extracting and translating article via AI fallback..."]


@responses.activate
def test_extract_article_from_url_passes_language_to_ai():
    responses.add(
        responses.GET,
        "https://source.test/article-lang",
        body="<article><h1>Title</h1><p>Body</p></article>",
        status=200,
        content_type="text/html",
    )
    ai = FakeAI()

    extract_article_from_url("https://source.test/article-lang", ai, language="Vietnamese")

    assert ai.calls[0][2] == "Vietnamese"
