import yaml

from core.config_manager import ConfigManager, _effective_disabled_steps


def test_load_config_removes_background_listener_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    data = {
        "api_key": "test_key",
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    with open(config_file, "w") as f:
        yaml.dump(data, f)

    manager = ConfigManager(config_path=str(config_file))

    assert manager.config["api_key"] == "test_key"
    assert manager.config["disabled_steps"] == []
    assert "telegram_commands" not in manager.config
    assert "scheduler" not in manager.config


def test_save_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=str(config_file))
    manager.config = {"key": "value"}
    manager.save_config()

    with open(config_file, "r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data == {"key": "value"}


def test_run_onboarding_does_not_ask_for_background_listener_or_scheduler(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=str(config_file))

    mock_ask = mocker.patch("questionary.text")
    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_checkbox = mocker.patch("questionary.checkbox")
    mock_requests_get = mocker.patch("requests.get")

    mock_ask.return_value.ask.side_effect = [
        "http://localhost:20128/v1",
        "api_key_val",
        "https://wp.com",
        "wp_user",
        "wp_pass",
        "sheets_id",
        "creds.json",
        "bot_token",
        "chat_id",
        "123456789",
        "EAAB_TOKEN",
        "v23.0",
    ]
    mock_select.return_value.ask.side_effect = [
        "text_model_val",
        "image_model_val",
        "Local",
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

    assert manager.config["telegram_bot_token"] == "bot_token"
    assert manager.config["telegram_chat_id"] == "chat_id"
    assert manager.config["image_mode"] == "Local"
    assert manager.config["disabled_steps"] == []
    assert "telegram_commands" not in manager.config
    assert "scheduler" not in manager.config


def test_effective_disabled_steps_prefers_disabled_steps_key():
    config = {"disabled_steps": ["ai_image_generation", "telegram_notify"], "enable_image_generation": True}
    assert _effective_disabled_steps(config) == ["ai_image_generation", "telegram_notify"]


def test_effective_disabled_steps_legacy_false_maps_to_image_step():
    config = {"enable_image_generation": False}
    assert _effective_disabled_steps(config) == ["ai_image_generation"]


def test_config_manager_init_migrates_legacy_image_key(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"enable_image_generation": False}, f)

    manager = ConfigManager(config_path=str(config_file))

    assert manager.config["disabled_steps"] == ["ai_image_generation"]
    assert "enable_image_generation" not in manager.config


def test_config_manager_normalizes_ai_timeout_and_chunk_size(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"ai_request_timeout": "9999", "translation_chunk_size": "500"}, f)

    manager = ConfigManager(config_path=str(config_file))

    assert manager.config["ai_request_timeout"] == 900
    assert manager.config["translation_chunk_size"] == 1000


def test_update_mode_only_updates_telegram_notification_credentials(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    initial = {
        "ninerouter_api_key": "old_key",
        "telegram_bot_token": "old_token",
        "telegram_chat_id": "old_chat",
        "telegram_commands": {"enabled": True},
        "disabled_steps": ["ai_image_generation"],
    }
    with open(config_file, "w") as f:
        yaml.dump(initial, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_text = mocker.patch("questionary.text")

    mock_select.return_value.ask.side_effect = [
        "Telegram",
        "Change",
        "Change",
    ]
    mock_confirm.return_value.ask.side_effect = [False]
    mock_text.return_value.ask.side_effect = ["new_token", "new_chat"]
    mocker.patch("requests.get", return_value=mocker.MagicMock(status_code=200, json=lambda: {"result": {"username": "bot"}}, text="ok"))

    manager.run_onboarding(update=True)

    assert manager.config["telegram_bot_token"] == "new_token"
    assert manager.config["telegram_chat_id"] == "new_chat"
    assert "telegram_commands" not in manager.config
    assert manager.config["ninerouter_api_key"] == "old_key"
    assert manager.config["disabled_steps"] == ["ai_image_generation"]


def test_run_onboarding_respects_existing_disabled_steps_default(tmp_path, mocker):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({"ninerouter_api_key": "existing_key", "disabled_steps": ["ai_image_generation"]}, f)

    manager = ConfigManager(config_path=str(config_file))

    mock_select = mocker.patch("questionary.select")
    mock_confirm = mocker.patch("questionary.confirm")
    mock_checkbox = mocker.patch("questionary.checkbox")

    mock_select.return_value.ask.side_effect = ["Disabled steps"]
    mock_confirm.return_value.ask.side_effect = [False]
    mock_checkbox.return_value.ask.return_value = ["ai_image_generation", "telegram_notify"]

    manager.run_onboarding(update=True)

    assert manager.config["disabled_steps"] == ["ai_image_generation", "telegram_notify"]
    kwargs = mock_checkbox.call_args.kwargs
    checked_values = [choice.value for choice in kwargs["choices"] if getattr(choice, "checked", False)]
    assert checked_values == ["ai_image_generation"]
