import os
import yaml
import pytest
from core.config_manager import ConfigManager

def test_load_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    data = {
        "api_key": "test_key",
        "model": "test_model"
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)
    
    manager = ConfigManager(config_path=str(config_file))
    assert manager.config == data

def test_save_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=str(config_file))
    manager.config = {"key": "value"}
    manager.save_config()
    
    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data == {"key": "value"}

def test_run_onboarding(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=str(config_file))
    
    mock_ask = mocker.patch("questionary.text")
    mock_select = mocker.patch("questionary.select")
    
    # Mocking questionary responses
    mock_ask.return_value.ask.side_effect = [
        "api_key_val", # 9router API Key
        "text_model_val", # 9router Model (Text)
        "image_model_val", # 9router Model (Image)
        "https://wp.com", # WordPress URL
        "wp_user", # Username
        "wp_pass", # Application Password
        "sheets_id", # Google Sheets ID
        "creds.json", # Google Credentials JSON Path
        "bot_token", # Telegram Bot Token
        "chat_id", # Chat ID
    ]
    mock_select.return_value.ask.return_value = "Local" # Image Mode
    
    manager.run_onboarding()
    
    assert manager.config["ninerouter_api_key"] == "api_key_val"
    assert manager.config["ninerouter_text_model"] == "text_model_val"
    assert manager.config["ninerouter_image_model"] == "image_model_val"
    assert manager.config["wordpress_url"] == "https://wp.com"
    assert manager.config["wordpress_username"] == "wp_user"
    assert manager.config["wordpress_password"] == "wp_pass"
    assert manager.config["google_sheets_id"] == "sheets_id"
    assert manager.config["google_creds_path"] == "creds.json"
    assert manager.config["telegram_bot_token"] == "bot_token"
    assert manager.config["telegram_chat_id"] == "chat_id"
    assert manager.config["image_mode"] == "Local"

def test_run_onboarding_no_update(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    initial_data = {"ninerouter_api_key": "existing_key"}
    with open(config_file, "w") as f:
        yaml.dump(initial_data, f)
    
    manager = ConfigManager(config_path=str(config_file))
    
    mock_ask = mocker.patch("questionary.text")
    # Should only ask for keys NOT in config
    # 10 keys total (9 text, 1 select). ninerouter_api_key is already there.
    # So 8 text questions should be asked.
    mock_ask.return_value.ask.side_effect = ["v"] * 9 
    mocker.patch("questionary.select").return_value.ask.return_value = "Local"
    
    manager.run_onboarding(update=False)
    
    assert manager.config["ninerouter_api_key"] == "existing_key"
    assert mock_ask.call_count == 9 # total text questions is 10, minus 1 already existing = 9
