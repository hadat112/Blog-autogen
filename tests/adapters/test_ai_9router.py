import responses
import json
from pathlib import Path
import pytest
from adapters.ai.ninerouter import (
    NineRouterAI,
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
    assert "Write title, content, caption, and the caption CTA entirely in Vietnamese." in prompt


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
    assert first_payload["messages"][0]["role"] == "system"
    assert "professional translation processor" in first_payload["messages"][0]["content"]
    first_prompt = first_payload["messages"][1]["content"]
    assert "Target language: Italian" in first_prompt
    assert "Source paragraph count: 1" in first_prompt
    assert "<source_text>" in first_prompt
    assert "Every sentence and paragraph" in first_prompt
    assert "exactly 1 paragraphs" in first_prompt
    assert "Do not leave any ordinary source-language sentence unchanged" in first_prompt
    assert "Preserve every event, fact, name, relationship" in first_prompt
    assert "Do not summarize, expand, omit, reorder" in first_prompt
    assert "If the source text is a title or headline" in first_prompt
    assert "source length and sentence-by-sentence structure" in first_prompt
    assert "Do not mention copyright" in first_prompt
    assert "Never answer with refusal wording" in first_prompt
    assert "Internal completion check" in first_prompt


@responses.activate
def test_translate_article_fields_includes_previous_source_context_for_later_chunks():
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
    first = "First paragraph " + ("a" * 2400)
    second = "Second paragraph with follow-up context. " + ("b" * 200)

    article = ai.translate_article_fields("Source title", f"{first}\n\n{second}", language="Italian")

    assert article["content"] == "Translated first chunk\n\nTranslated second chunk"
    second_payload = json.loads(responses.calls[2].request.body.decode("utf-8"))
    second_prompt = second_payload["messages"][1]["content"]
    assert "Previous source context for continuity only" in second_prompt
    assert "First paragraph" in second_prompt
    assert "Second paragraph with follow-up context." in second_prompt


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
