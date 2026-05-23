import pytest
from unittest.mock import MagicMock, patch
from core.orchestrator import Orchestrator

def test_orchestrator_initialization_with_configs():
    ai_config = {
        "api_key": "test_ai_key",
        "text_model": "test_text_model",
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
    gs_config = {
        "credentials_json": "test_creds.json",
        "sheet_id": "test_sheet_id"
    }
    tg_config = {
        "bot_token": "test_tg_token",
        "chat_id": "test_tg_chat_id"
    }

    with patch("core.orchestrator.NineRouterAI") as MockAI, \
         patch("core.orchestrator.WordPressPublisher") as MockWP, \
         patch("core.orchestrator.FacebookPagePublisher") as MockFB, \
         patch("core.orchestrator.GoogleSheetsProvider") as MockGS:
        
        orchestrator = Orchestrator(
            ai_config=ai_config,
            wp_config=wp_config,
            fb_config=fb_config,
            gs_config=gs_config,
            tg_config=tg_config
        )

        # Verify AI initialization
        MockAI.assert_called_once_with(
            api_key="test_ai_key",
            text_model="test_text_model",
            image_model="test_image_model",
            base_url="http://test_ai_url"
        )
        assert orchestrator.ai == MockAI.return_value

        # Verify WP initialization
        MockWP.assert_called_once_with(
            url="http://test_wp_url",
            username="test_wp_user",
            app_password="test_wp_password"
        )
        assert orchestrator.wp == MockWP.return_value

        # Verify FB initialization
        MockFB.assert_called_once_with(
            page_id="test_fb_id",
            access_token="test_fb_token",
            graph_version="v99.0"
        )
        assert orchestrator.fb == MockFB.return_value

        # Verify GS initialization
        MockGS.assert_called_once_with(
            credentials_json="test_creds.json",
            sheet_id="test_sheet_id"
        )
        assert orchestrator.sheets == MockGS.return_value

        # Verify TG config is stored
        assert orchestrator.tg_config == tg_config

def test_orchestrator_initialization_with_none_configs():
    with patch("core.orchestrator.NineRouterAI") as MockAI, \
         patch("core.orchestrator.WordPressPublisher") as MockWP, \
         patch("core.orchestrator.FacebookPagePublisher") as MockFB, \
         patch("core.orchestrator.GoogleSheetsProvider") as MockGS:
        
        orchestrator = Orchestrator(
            ai_config=None,
            wp_config=None,
            fb_config=None,
            gs_config=None,
            tg_config=None
        )

        MockAI.assert_not_called()
        MockWP.assert_not_called()
        MockFB.assert_not_called()
        MockGS.assert_not_called()

        assert orchestrator.ai is None
        assert orchestrator.wp is None
        assert orchestrator.fb is None
        assert orchestrator.sheets is None
        assert orchestrator.tg_config is None
