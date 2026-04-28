import responses
import json
import pytest
from providers.ai_9router import NineRouterAI

@responses.activate
def test_generate_story():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model)
    
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
def test_generate_image():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model)
    
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
