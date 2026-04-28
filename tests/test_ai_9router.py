import responses
import json
import pytest
from providers.ai_9router import NineRouterAI

@responses.activate
def test_generate_story_openai_style():
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
        "http://localhost:20128/v1/responses",
        json=mock_response,
        status=200
    )
    
    story = ai.generate_story("Tell me a story")
    assert story["title"] == "Test Title"

@responses.activate
def test_generate_story_flat_response():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model)
    
    mock_response = {
        "response": json.dumps({
            "title": "Flat Title",
            "content": "Flat Content",
            "caption": "Flat Caption",
            "image_prompt": "Flat Prompt"
        })
    }
    
    responses.add(
        responses.POST,
        "http://localhost:20128/v1/responses",
        json=mock_response,
        status=200
    )
    
    story = ai.generate_story("Tell me a story")
    assert story["title"] == "Flat Title"

@responses.activate
def test_generate_story_direct_json():
    api_key = "test_key"
    text_model = "gpt-4o"
    image_model = "dall-e-3"
    ai = NineRouterAI(api_key, text_model, image_model)
    
    mock_response = {
        "title": "Direct Title",
        "content": "Direct Content",
        "caption": "Direct Caption",
        "image_prompt": "Direct Prompt"
    }
    
    responses.add(
        responses.POST,
        "http://localhost:20128/v1/responses",
        json=mock_response,
        status=200
    )
    
    story = ai.generate_story("Tell me a story")
    assert story["title"] == "Direct Title"
    assert story["content"] == "Direct Content"

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
        "http://localhost:20128/v1/images/generations",
        json=mock_response,
        status=200
    )
    
    image_url = ai.generate_image("A beautiful sunset")
    
    assert image_url == "https://image.url/test.png"
