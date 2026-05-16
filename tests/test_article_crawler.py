import responses

from core.article_crawler import extract_article_from_url


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
