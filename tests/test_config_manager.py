import yaml
from core.config_manager import ConfigManager, _effective_disabled_steps
from unittest.mock import call


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    data = {
        "api_key": "test_key",
        "model": "test_model"
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    manager = ConfigManager(config_path=str(config_file))
    assert manager.config["api_key"] == "test_key"
    assert manager.config["model"] == "test_model"
    assert manager.config["disabled_steps"] == []


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
    mock_checkbox = mocker.patch("questionary.checkbox")
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
        "Enabled",    # scheduler enabled
        "Fixed",      # schedule mode
        "Enabled",    # schedule with image
    ]
    mock_confirm.return_value.ask.return_value = True
    mock_checkbox.return_value.ask.return_value = []

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
    assert manager.config["disabled_steps"] == []
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
    mock_checkbox = mocker.patch("questionary.checkbox")
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
        "Disabled",   # scheduler disabled
    ]
    mock_confirm.return_value.ask.return_value = True
    mock_checkbox.return_value.ask.return_value = []

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
    assert manager.config["disabled_steps"] == []
    assert mock_ask.call_count == 11


def test_effective_disabled_steps_prefers_disabled_steps_key():
    config = {"disabled_steps": ["ai_image_generation", "telegram_notify"], "enable_image_generation": True}
    assert _effective_disabled_steps(config) == ["ai_image_generation", "telegram_notify"]


def test_effective_disabled_steps_legacy_false_maps_to_image_step():
    config = {"enable_image_generation": False}
    assert _effective_disabled_steps(config) == ["ai_image_generation"]


def test_effective_disabled_steps_legacy_true_maps_to_empty_list():
    config = {"enable_image_generation": True}
    assert _effective_disabled_steps(config) == []


def test_config_manager_init_migrates_legacy_key(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"enable_image_generation": False}, f)

    manager = ConfigManager(config_path=str(config_file))

    assert manager.config["disabled_steps"] == ["ai_image_generation"]
    assert "enable_image_generation" not in manager.config


def test_update_mode_only_updates_selected_category(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    initial = {
        "ninerouter_api_key": "old_key",
        "telegram_bot_token": "old_token",
        "telegram_chat_id": "old_chat",
        "telegram_commands": {"enabled": False},
        "disabled_steps": ["ai_image_generation"],
    }
    with open(config_file, "w") as f:
        yaml.dump(initial, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_text = mocker.patch("questionary.text")

    mock_select.return_value.ask.side_effect = [
        "Telegram",     # category
        "Change",       # bot token
        "Change",       # chat id
        "Enabled",      # telegram commands
    ]
    mock_confirm.return_value.ask.side_effect = [False]
    mock_text.return_value.ask.side_effect = ["new_token", "new_chat"]
    mocker.patch("requests.get", return_value=mocker.MagicMock(status_code=200, json=lambda: {"result": {"username": "bot"}}, text="ok"))

    manager.run_onboarding(update=True)

    assert manager.config["telegram_bot_token"] == "new_token"
    assert manager.config["telegram_chat_id"] == "new_chat"
    assert manager.config["telegram_commands"]["enabled"] is True
    assert manager.config["ninerouter_api_key"] == "old_key"
    assert manager.config["disabled_steps"] == ["ai_image_generation"]


def test_update_mode_keep_current_skips_reprompt(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"telegram_bot_token": "old_token", "telegram_chat_id": "old_chat", "telegram_commands": {"enabled": True}}, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_text = mocker.patch("questionary.text")

    mock_select.return_value.ask.side_effect = [
        "Telegram",      # category
        "Keep current",  # bot token
        "Keep current",  # chat id
        "Enabled",       # commands toggle
    ]
    mock_confirm.return_value.ask.side_effect = [False]
    mocker.patch("requests.get", return_value=mocker.MagicMock(status_code=200, json=lambda: {"result": {"username": "bot"}}, text="ok"))

    manager.run_onboarding(update=True)

    mock_text.assert_not_called()
    assert manager.config["telegram_bot_token"] == "old_token"
    assert manager.config["telegram_chat_id"] == "old_chat"


def test_update_mode_validates_category_then_continue_to_next(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"wordpress_url": "https://wp.com", "wordpress_username": "u", "wordpress_password": "p", "image_mode": "Direct", "disabled_steps": []}, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_checkbox = mocker.patch("questionary.checkbox")

    mock_select.return_value.ask.side_effect = [
        "WordPress",     # category1
        "Keep current",  # wp url
        "Keep current",  # wp username
        "Keep current",  # wp password
        "Disabled steps",  # category2
        "Keep current",         # image mode
        "Finish update",        # finish
    ]
    mock_confirm.return_value.ask.side_effect = [True, False]
    mock_checkbox.return_value.ask.return_value = ["telegram_notify"]

    resp = mocker.MagicMock()
    resp.status_code = 200
    resp.text = "ok"
    mocker.patch("requests.get", return_value=resp)

    manager.run_onboarding(update=True)

    assert manager.config["disabled_steps"] == ["telegram_notify"]


def test_update_mode_validation_failure_retry_category(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"telegram_bot_token": "old", "telegram_chat_id": "old", "telegram_commands": {"enabled": True}}, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_text = mocker.patch("questionary.text")

    mock_select.return_value.ask.side_effect = [
        "Telegram",      # category
        "Change",        # token
        "Change",        # chat
        "Enabled",       # commands
        "Retry category",# validation fail action
        "Keep current",  # token on retry
        "Keep current",  # chat on retry
        "Enabled",       # commands on retry
        "Finish update", # finish
    ]
    mock_confirm.return_value.ask.side_effect = [False]
    mock_text.return_value.ask.side_effect = ["new_token", "new_chat"]

    bad_resp = mocker.MagicMock(status_code=500, text="bad")
    good_resp = mocker.MagicMock(status_code=200, text="ok", json=lambda: {"result": {"username": "bot"}})
    mocker.patch("requests.get", side_effect=[bad_resp, good_resp])

    manager.run_onboarding(update=True)

    assert manager.config["telegram_bot_token"] == "new_token"
    assert manager.config["telegram_chat_id"] == "new_chat"


def test_run_onboarding_respects_existing_disabled_steps_default(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"ninerouter_api_key": "existing_key", "disabled_steps": ["ai_image_generation"]}, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_checkbox = mocker.patch("questionary.checkbox")

    mock_select.return_value.ask.side_effect = [
        "Disabled steps",  # category
        "Keep current",         # image_mode
    ]
    mock_confirm.return_value.ask.side_effect = [False]
    mock_checkbox.return_value.ask.return_value = ["ai_image_generation", "telegram_notify"]

    manager.run_onboarding(update=True)

    assert manager.config["disabled_steps"] == ["ai_image_generation", "telegram_notify"]
    kwargs = mock_checkbox.call_args.kwargs
    checked_values = [choice.value for choice in kwargs["choices"] if getattr(choice, "checked", False)]
    assert checked_values == ["ai_image_generation"]
    assert "enable_image_generation" not in manager.config
