import responses
import json
from pathlib import Path
import pytest
from providers.ai_9router import NineRouterAI, _parse_story_json

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_raw_content(filename: str) -> str:
    payload = json.loads((ROOT_DIR / "debug" / filename).read_text(encoding="utf-8"))
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
def test_generate_image():
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
