import pytest
from unittest.mock import MagicMock, patch
from app.domain.story_orchestrator import StoryOrchestrator

def test_story_orchestrator_initialization_with_configs():
    ai_config = {
        "api_key": "test_ai_key",
        "text_model": "test_text_model",
        "fallback_text_model": "test_fallback_text_model",
        "image_model": "test_image_model",
        "base_url": "http://test_ai_url"
    }
    wp_config = {
        "url": "http://test_wp_url",
        "username": "test_wp_user",
        "password": "test_wp_password"
    }
    fb_config = {
        "page_id": "test_fb_id",
        "access_token": "test_fb_token",
        "graph_version": "v99.0"
    }
    tg_config = {
        "bot_token": "test_tg_token",
        "chat_id": "test_tg_chat_id"
    }

    with patch("app.domain.story_orchestrator.NineRouterAI") as MockAI, \
         patch("app.domain.story_orchestrator.WordPressPublisher") as MockWP, \
         patch("app.domain.story_orchestrator.FacebookPagePublisher") as MockFB:

        story_orchestrator = StoryOrchestrator(
            ai_config=ai_config,
            wp_config=wp_config,
            fb_config=fb_config,
            tg_config=tg_config
        )

        # Verify AI initialization
        assert MockAI.call_count == 1
        assert MockAI.call_args.kwargs["api_key"] == "test_ai_key"
        assert MockAI.call_args.kwargs["text_model"] == "test_text_model"
        assert MockAI.call_args.kwargs["fallback_text_model"] == "test_fallback_text_model"
        assert MockAI.call_args.kwargs["image_model"] == "test_image_model"
        assert MockAI.call_args.kwargs["base_url"] == "http://test_ai_url"
        assert story_orchestrator.ai == MockAI.return_value

        # Verify WP initialization
        MockWP.assert_called_once_with(
            url="http://test_wp_url",
            username="test_wp_user",
            app_password="test_wp_password"
        )
        assert story_orchestrator.wp == MockWP.return_value

        # Verify FB initialization
        MockFB.assert_called_once_with(
            page_id="test_fb_id",
            access_token="test_fb_token",
            graph_version="v99.0"
        )
        assert story_orchestrator.fb == MockFB.return_value

        # Verify TG config is stored
        assert story_orchestrator.tg_config == tg_config

def test_story_orchestrator_initialization_with_none_configs():
    with patch("app.domain.story_orchestrator.NineRouterAI") as MockAI, \
         patch("app.domain.story_orchestrator.WordPressPublisher") as MockWP, \
         patch("app.domain.story_orchestrator.FacebookPagePublisher") as MockFB:

        story_orchestrator = StoryOrchestrator(
            ai_config=None,
            wp_config=None,
            fb_config=None,
            tg_config=None
        )

        MockAI.assert_not_called()
        MockWP.assert_not_called()
        MockFB.assert_not_called()

        assert story_orchestrator.ai is None
        assert story_orchestrator.wp is None
        assert story_orchestrator.fb is None
        assert story_orchestrator.tg_config is None
