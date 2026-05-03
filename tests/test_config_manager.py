import yaml
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
    mock_confirm = mocker.patch("questionary.confirm")
    mock_requests_get = mocker.patch("requests.get")

    mock_ask.return_value.ask.side_effect = [
        "http://localhost:20128/v1",  # 9router base url
        "api_key_val",                # 9router API Key
        "https://wp.com",             # WordPress URL
        "wp_user",                    # Username
        "wp_pass",                    # Application Password
        "sheets_id",                  # Google Sheets ID
        "creds.json",                 # Google Credentials JSON Path
        "bot_token",                  # Telegram Bot Token
        "chat_id",                    # Chat ID
        "123456789",                  # Facebook Page ID
        "EAAB_TOKEN",                 # Facebook Page Access Token
        "v23.0",                      # Facebook Graph version
        "08:00",                      # scheduler time
        "1",                          # scheduler limit
    ]

    mock_select.return_value.ask.side_effect = [
        "text_model_val",
        "image_model_val",
        "Enabled",    # telegram_commands
        "Local",      # image_mode
        "Enabled",    # enable_image_generation
        "Enabled",    # scheduler enabled
        "Fixed",      # schedule mode
        "Enabled",    # schedule with image
    ]
    mock_confirm.return_value.ask.return_value = True

    resp = mocker.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [{"id": "text_model_val"}, {"id": "image_model_val"}],
        "result": {"username": "bot"},
    }
    resp.text = "ok"
    mock_requests_get.return_value = resp

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
    assert manager.config["facebook_page_id"] == "123456789"
    assert manager.config["facebook_page_access_token"] == "EAAB_TOKEN"
    assert manager.config["facebook_graph_version"] == "v23.0"
    assert manager.config["image_mode"] == "Local"
    assert manager.config["enable_image_generation"] is True
    assert manager.config["telegram_commands"]["enabled"] is True
    assert manager.config["scheduler"]["enabled"] is True
    assert len(manager.config["scheduler"]["jobs"]) == 1
    assert manager.config["scheduler"]["jobs"][0]["mode"] == "fixed"


def test_run_onboarding_no_update(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    initial_data = {"ninerouter_api_key": "existing_key"}
    with open(config_file, "w") as f:
        yaml.dump(initial_data, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_ask = mocker.patch("questionary.text")
    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_requests_get = mocker.patch("requests.get")

    mock_ask.return_value.ask.side_effect = [
        "http://localhost:20128/v1",  # ninerouter_base_url
        "https://wp.com",             # wordpress_url
        "wp_user",                    # wordpress_username
        "wp_pass",                    # wordpress_password
        "sheets_id",                  # google_sheets_id
        "creds.json",                 # google_creds_path
        "bot_token",                  # telegram_bot_token
        "chat_id",                    # telegram_chat_id
        "123456789",                  # facebook_page_id
        "EAAB_TOKEN",                 # facebook_page_access_token
        "v23.0",                      # facebook_graph_version
    ]
    mock_select.return_value.ask.side_effect = [
        "text_model_val",
        "image_model_val",
        "Enabled",    # telegram commands
        "Local",      # image_mode
        "Enabled",    # image generation
        "Disabled",   # scheduler disabled
    ]
    mock_confirm.return_value.ask.return_value = True

    resp = mocker.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [{"id": "text_model_val"}, {"id": "image_model_val"}],
        "result": {"username": "bot"},
    }
    resp.text = "ok"
    mock_requests_get.return_value = resp

    manager.run_onboarding(update=False)

    assert manager.config["ninerouter_api_key"] == "existing_key"
    assert mock_ask.call_count == 11
