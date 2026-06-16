import responses
import json
from pathlib import Path
import pytest
from adapters.ai.ninerouter import (
    NineRouterAI,
    _get_ai_request_timeout,
    _parse_story_json,
    CINEMATIC_NATURALISM_STYLE_PROMPT,
)

EXPECTED_STYLE_PROMPT = (
    "Naturalistic high-key daylight lighting, vivid and clean color palette, neutral white balance, "
    "realistic skin tones with zero color tint, sharp clarity, 8k professional photography, "
    "shot on full-frame sensor for authentic color reproduction, no moody color grading, "
    "no teal-orange look, no heavy shadows, no dramatic dark tone."
)

assert CINEMATIC_NATURALISM_STYLE_PROMPT == EXPECTED_STYLE_PROMPT

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_ai_request_timeout_defaults_to_300_seconds(monkeypatch):
    monkeypatch.delenv("AI_REQUEST_TIMEOUT", raising=False)

    assert _get_ai_request_timeout() == 300


def test_ai_request_timeout_can_be_overridden(monkeypatch):
    monkeypatch.setenv("AI_REQUEST_TIMEOUT", "300")

    assert _get_ai_request_timeout() == 300


def test_ai_request_timeout_uses_config_default(monkeypatch):
    monkeypatch.delenv("AI_REQUEST_TIMEOUT", raising=False)

    assert _get_ai_request_timeout(450) == 450


def test_translate_article_fields_uses_configured_chunk_size(monkeypatch):
    ai = NineRouterAI(
        "test_key",
        "gpt-4o",
        "dall-e-3",
        translation_chunk_size=1200,
    )
    translated_texts = []

    def fake_translate(text, language, **kwargs):
        translated_texts.append(text)
        if text == "Source title":
            return "Translated title"
        return f"translated:{len(text)}"

    monkeypatch.setattr(ai, "_translate_text_with_retry", fake_translate)
    content = "a" * 1300

    ai.translate_article_fields("Source title", content, language="Italian")

    assert translated_texts[1:] == ["a" * 1200, "a" * 100]


def _load_raw_content(filename: str) -> str:
    path = ROOT_DIR / "debug" / filename
    if not path.exists():
        pytest.skip(f"Missing debug fixture: {filename}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "raw_content" in payload:
        return payload["raw_content"]
    return json.dumps(payload, ensure_ascii=False)


def test_parse_real_fail_debug_file():
    raw = _load_raw_content("fail_0502_005054.json")
    parsed = _parse_story_json(raw)

    assert parsed["title"]
    assert parsed["content"]
    assert parsed["caption"]
    assert parsed["image_prompt"]


def test_parse_real_fail_debug_file_005614():
    raw = _load_raw_content("fail_0502_005614.json")
    parsed = _parse_story_json(raw)

    assert parsed["title"]
    assert parsed["content"]
    assert parsed["caption"]
    assert parsed["image_prompt"]


def test_parse_real_success_debug_file():
    raw = _load_raw_content("story_0502_003640.json")
    parsed = _parse_story_json(raw)

    assert parsed["title"]
    assert parsed["content"]
    assert parsed["caption"]
    assert parsed["image_prompt"]




from adapters.ai.ninerouter import NineRouterAI

@responses.activate
def test_generate_story():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model, base_url="https://api.9router.ai/v1")
    
    mock_response = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "title": "Test Title",
                    "content": "Test Content",
                    "caption": "Test Caption",
                    "image_prompt": "Test Image Prompt"
                })
            }
        }]
    }
    
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json=mock_response,
        status=200
    )
    
    story = ai.generate_story("Tell me a story")
    
    assert story["title"] == "Test Title"
    assert story["content"] == "Test Content"
    assert story["caption"] == "Test Caption"
    assert story["image_prompt"] == "Test Image Prompt"

@responses.activate
def test_generate_story_with_unescaped_newline_in_json_string():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model, base_url="https://api.9router.ai/v1")

    malformed_story_json = '{\n "title": "Test Title",\n "content": "Line 1\nLine 2",\n "caption": "Test Caption",\n "image_prompt": "Test Image Prompt"\n}'
    mock_response = {
        "choices": [{
            "message": {
                "content": malformed_story_json
            }
        }]
    }

    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json=mock_response,
        status=200
    )

    story = ai.generate_story("Tell me a story")

    assert story["title"] == "Test Title"
    assert story["content"] == "Line 1\nLine 2"
    assert story["caption"] == "Test Caption"
    assert story["image_prompt"] == "Test Image Prompt"


@responses.activate
def test_generate_story_with_broken_json_and_extra_text_extracts_fields():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model, base_url="https://api.9router.ai/v1")

    malformed_story_json = """Here is your story:
```json
{
 \"title\": \"Broken But Recoverable\",
 \"content\": \"First paragraph with newline
second line and more text\",
 \"caption\": \"Teaser line with suspense\",
 \"image_prompt\": \"Cinematic scene of cliffhanger\"
}
```
Thanks!"""

    mock_response = {
        "choices": [{
            "message": {
                "content": malformed_story_json
            }
        }]
    }

    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json=mock_response,
        status=200
    )

    story = ai.generate_story("Tell me a story")

    assert story["title"] == "Broken But Recoverable"
    assert "First paragraph" in story["content"]
    assert "suspense" in story["caption"]
    assert "Cinematic scene" in story["image_prompt"]


@responses.activate
def test_generate_image_appends_cinematic_style_prompt():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model, base_url="https://api.9router.ai/v1")

    mock_response = {
        "data": [{
            "url": "https://image.url/test.png"
        }]
    }

    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/images/generations",
        json=mock_response,
        status=200
    )

    image_url = ai.generate_image("A beautiful sunset")

    assert image_url == "https://image.url/test.png"

    request_payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert request_payload["prompt"] == f"A beautiful sunset\n\n{CINEMATIC_NATURALISM_STYLE_PROMPT}"


@responses.activate
def test_generate_image_uses_style_prompt_when_base_prompt_empty():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model, base_url="https://api.9router.ai/v1")

    mock_response = {
        "data": [{
            "url": "https://image.url/test.png"
        }]
    }

    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/images/generations",
        json=mock_response,
        status=200
    )

    image_url = ai.generate_image("   ")

    assert image_url == "https://image.url/test.png"

    request_payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert request_payload["prompt"] == CINEMATIC_NATURALISM_STYLE_PROMPT


@responses.activate
def test_extract_article_returns_title_content_caption_and_image_url():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    mock_response = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "title": "Article Title",
                    "content": "Article body",
                    "caption": "Article caption",
                    "image_url": "https://example.com/image.jpg"
                })
            }
        }]
    }
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json=mock_response,
        status=200,
    )

    article = ai.extract_article("<article><h1>Article Title</h1><p>Body</p></article>", "https://example.com/article")

    assert article == {
        "title": "Article Title",
        "content": "Article body",
        "caption": "Article caption",
        "image_url": "https://example.com/image.jpg",
    }
    request_payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert request_payload["model"] == "gpt-4o"
    assert "image_url" in request_payload["messages"][0]["content"]



@responses.activate
def test_extract_article_prompt_includes_output_language():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "title": "Tiêu đề",
                        "content": "Nội dung",
                        "caption": "Chú thích",
                        "image_url": ""
                    })
                }
            }]
        },
        status=200,
    )

    ai.extract_article("<article>Body</article>", "https://example.com/article", language="Vietnamese")

    request_payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    prompt = request_payload["messages"][0]["content"]
    assert "caption must be 300-500 words" in prompt
    assert "cut from the article content itself" in prompt
    assert "read more in the comments below" in prompt
    assert "mandatory target language is exactly: Vietnamese" in prompt
    assert "reader-facing word in title, content, caption, and caption CTA in Vietnamese only" in prompt
    assert "verify that title, content, caption, and the caption CTA are entirely in Vietnamese" in prompt


def test_parse_article_json_repairs_concatenated_string_segments():
    from adapters.ai.ninerouter import _parse_article_json

    raw = '{\n "title": "Article Title",\n "content": "First part " +\n "second part with suspense",\n "caption": "Short caption",\n "image_url": "https://example.com/image.jpg"\n}'

    parsed = _parse_article_json(raw)

    assert parsed["title"] == "Article Title"
    assert parsed["content"] == "First part second part with suspense"
    assert parsed["caption"] == "Short caption"
    assert parsed["image_url"] == "https://example.com/image.jpg"


@responses.activate
def test_translate_article_fields_returns_standard_article_payload():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated title"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated paragraph"}}]},
        status=200,
    )

    article = ai.translate_article_fields(
        "Source title",
        "Source paragraph",
        "https://source.test/image.jpg",
        language="Italian",
    )

    assert article == {
        "title": "Translated title",
        "content": "Translated paragraph",
        "caption": "",
        "image_url": "https://source.test/image.jpg",
    }
    assert len(responses.calls) == 2
    first_payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert first_payload["temperature"] == 0.2
    assert first_payload["messages"][0]["role"] == "system"
    assert "deterministic translation engine" in first_payload["messages"][0]["content"]
    assert "dialogue inside quotation marks" in first_payload["messages"][0]["content"]
    assert "Never expose analysis, reasoning, self-correction" in first_payload["messages"][0]["content"]
    first_prompt = first_payload["messages"][1]["content"]
    assert "TARGET LANGUAGE (authoritative, preserve exactly as written): Italian" in first_prompt
    assert "Translate all content inside <source_text> into Italian" in first_prompt
    assert "Translate every narration sentence and every quoted line of dialogue" in first_prompt
    assert "Quotation marks do not make text exempt from translation" in first_prompt
    assert '"Note:", "Wait:", "Inconsistent:", "Correction:"' in first_prompt
    assert "Never apologize, refuse, discuss copyright or permission" in first_prompt
    assert "Use exactly Italian" in first_prompt
    assert "Source paragraph count: 1" in first_prompt
    assert "<source_text>" in first_prompt
    assert "exactly 1 paragraphs" in first_prompt
    assert "Preserve every event, fact, name, relationship" in first_prompt
    assert "Do not summarize, expand, omit, reorder" in first_prompt
    assert "If the source text is a title or headline" in first_prompt
    assert "source length and sentence-by-sentence structure" in first_prompt
    assert "SILENT FINAL CHECK" in first_prompt


@responses.activate
def test_translation_prompt_preserves_custom_language_text():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Custom output"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Custom paragraph"}}]},
        status=200,
    )

    ai.translate_article_fields("Title", "Paragraph", language="abc")

    payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert payload["temperature"] == 0.2
    prompt = payload["messages"][1]["content"]
    assert "TARGET LANGUAGE (authoritative, preserve exactly as written): abc" in prompt
    assert "Translate all content inside <source_text> into abc" in prompt
    assert "Use exactly abc" in prompt


@responses.activate
def test_translate_article_fields_uses_previous_translation_for_later_chunks():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated title"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated first chunk"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated second chunk"}}]},
        status=200,
    )
    first = "First paragraph " + ("a" * 5800)
    second = "Second paragraph with follow-up context. " + ("b" * 200)

    progress_messages = []
    article = ai.translate_article_fields(
        "Source title",
        f"{first}\n\n{second}",
        language="Italian",
        progress_callback=progress_messages.append,
    )

    assert article["content"] == "Translated first chunk\n\nTranslated second chunk"
    assert progress_messages[0] == "Step 2: chunk1 start (3 words)"
    assert progress_messages[1].startswith("Step 2: chunk1 done in ")
    assert progress_messages[1].endswith(" 33% (3/9 words)")
    assert progress_messages[2] == "Step 2: chunk2 start (6 words)"
    assert progress_messages[3].startswith("Step 2: chunk2 done in ")
    assert progress_messages[3].endswith(" 100% (9/9 words)")
    second_payload = json.loads(responses.calls[2].request.body.decode("utf-8"))
    second_prompt = second_payload["messages"][1]["content"]
    assert "Previous translated context already written in Italian" in second_prompt
    assert "Translated first chunk" in second_prompt
    assert "Do not repeat, rewrite, summarize" in second_prompt
    assert "First paragraph" not in second_prompt
    assert "Second paragraph with follow-up context." in second_prompt


@responses.activate
def test_translate_text_with_source_context_writes_prompt_clearly():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated current chunk"}}]},
        status=200,
    )

    translated = ai._translate_text(
        "Current source paragraph.",
        "Italian",
        article_title="Translated title",
        previous_source_context="Previous source paragraph.",
    )

    assert translated == "Translated current chunk"
    payload = json.loads(responses.calls[0].request.body.decode("utf-8"))
    prompt = payload["messages"][1]["content"]
    assert "Previous source context from the original article, not translated yet" in prompt
    assert "Do not translate, repeat, rewrite, summarize" in prompt
    assert "Previous source paragraph." in prompt


def test_parallel_translation_preserves_chunk_order_and_uses_source_context(monkeypatch):
    ai = NineRouterAI(
        "test_key",
        "gpt-4o",
        "dall-e-3",
        translation_mode="parallel",
        translation_max_concurrency=2,
    )
    calls = []

    def fake_translate(text, language, *, article_title="", previous_translation_context="", previous_source_context=""):
        calls.append(
            {
                "text": text,
                "previous_translation_context": previous_translation_context,
                "previous_source_context": previous_source_context,
            }
        )
        if text == "Source title":
            return "Translated title"
        if text.startswith("First paragraph"):
            return "Translated first chunk"
        return "Translated second chunk"

    monkeypatch.setattr(ai, "_translate_text_with_retry", fake_translate)
    first = "First paragraph " + ("a" * 5800)
    second = "Second paragraph with follow-up context. " + ("b" * 200)

    article = ai.translate_article_fields(
        "Source title",
        f"{first}\n\n{second}",
        language="Italian",
    )

    assert article["content"] == "Translated first chunk\n\nTranslated second chunk"
    first_call = next(call for call in calls if call["text"].startswith("First paragraph"))
    second_call = next(call for call in calls if call["text"].startswith("Second paragraph"))
    assert first_call["previous_translation_context"] == ""
    assert second_call["previous_translation_context"] == ""
    assert first_call["previous_source_context"] == ""
    assert second_call["previous_source_context"].startswith("First paragraph")


@responses.activate
def test_translate_article_fields_cleans_extra_translation_prefix():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translation: Titolo tradotto"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Here is the translation: Paragrafo tradotto"}}]},
        status=200,
    )

    article = ai.translate_article_fields("Source title", "Source paragraph", language="Italian")

    assert article["title"] == "Titolo tradotto"
    assert article["content"] == "Paragrafo tradotto"


@responses.activate
def test_translate_article_fields_does_not_retry_refusal_output():
    ai = NineRouterAI("test_key", "gpt-4o", "dall-e-3", base_url="https://api.9router.ai/v1")
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "Translated title"}}]},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.9router.ai/v1/chat/completions",
        json={"choices": [{"message": {"content": "I'm sorry, but I can't provide copyrighted text."}}]},
        status=200,
    )

    article = ai.translate_article_fields("Source title", "Source paragraph", language="Italian")

    assert article["content"] == "I'm sorry, but I can't provide copyrighted text."
    assert len(responses.calls) == 2
