import responses
import json
from pathlib import Path
import pytest
from providers.ai_9router import (
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




from providers.ai_9router import NineRouterAI

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
    assert "Write title, content, and caption in Vietnamese." in request_payload["messages"][0]["content"]
