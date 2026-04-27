import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
from core.orchestrator import Orchestrator

@pytest.fixture
def mock_config():
    return {
        "ninerouter_api_key": "test_key",
        "ninerouter_text_model": "text_model",
        "ninerouter_image_model": "image_model",
        "wordpress_url": "https://test.wp",
        "wordpress_username": "user",
        "wordpress_password": "pass",
        "google_sheets_id": "sheet_id",
        "google_creds_path": "creds.json",
        "telegram_bot_token": "bot_token",
        "telegram_chat_id": "chat_id",
        "image_mode": "Direct"
    }

@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_orchestrator_init(mock_storage, mock_wp, mock_sheets, mock_ai, mock_config):
    orch = Orchestrator(mock_config)
    
    mock_ai.assert_called_once_with(
        api_key="test_key",
        text_model="text_model",
        image_model="image_model"
    )
    mock_sheets.assert_called_once_with(
        credentials_json="creds.json",
        sheet_id="sheet_id"
    )
    mock_wp.assert_called_once_with(
        url="https://test.wp",
        username="user",
        app_password="pass"
    )
    mock_storage.assert_called_once()
    assert orch.image_mode == "direct"

@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_success(mock_storage, mock_wp, mock_sheets, mock_ai, mock_telegram, mock_config):
    orch = Orchestrator(mock_config)
    
    # Mock AI responses
    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content",
        "caption": "Test Caption",
        "image_prompt": "Test Image Prompt"
    }
    orch.ai.generate_image.return_value = "https://image.url"
    orch.wp.publish.return_value = "https://wp.url/story"
    
    result = orch.process_prompt("Test Prompt")
    
    assert result["status"] == "success"
    assert result["title"] == "Test Title"
    assert result["url"] == "https://wp.url/story"
    
    orch.ai.generate_story.assert_called_once_with("Test Prompt")
    orch.ai.generate_image.assert_called_once_with("Test Image Prompt")
    orch.wp.publish.assert_called_once_with("Test Title", "Test Content", "https://image.url")
    orch.sheets.append_row.assert_called_once()
    mock_telegram.assert_called_once()

@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_failure(mock_storage, mock_wp, mock_sheets, mock_ai, mock_telegram, mock_config):
    orch = Orchestrator(mock_config)
    
    orch.ai.generate_story.side_effect = Exception("AI Error")
    
    result = orch.process_prompt("Test Prompt")
    
    assert result["status"] == "error"
    assert "AI Error" in result["error"]
    
    orch.sheets.append_row.assert_called_once()
    mock_telegram.assert_called_once()

@patch("core.orchestrator.os.path.exists")
@patch("core.orchestrator.ThreadPoolExecutor")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.StorageProvider")
def test_orchestrator_run(mock_storage, mock_wp, mock_sheets, mock_ai, mock_executor, mock_exists, mock_config):
    mock_exists.return_value = True
    orch = Orchestrator(mock_config)
    
    # Mock prompts file content
    m = mock_open(read_data="prompt1\nprompt2\n")
    with patch("builtins.open", m):
        orch.run("prompts.txt")
    
    # Verify ThreadPoolExecutor was used
    mock_executor.assert_called_once_with(max_workers=5)
    executor_instance = mock_executor.return_value.__enter__.return_value
    # In my implementation, I use list(tqdm(executor.map(...)))
    # So map should be called
    executor_instance.map.assert_called_once()
