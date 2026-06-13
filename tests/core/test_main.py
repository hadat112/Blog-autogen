from unittest.mock import patch

from core.run_options import RunOptions
def test_resolve_disabled_steps_prefers_new_config_key():
    from main import _resolve_disabled_steps

    options = RunOptions(limit=None, threads=1, language="en", debug=False, with_image=False, no_image=False)
    resolved = _resolve_disabled_steps(options, {"disabled_steps": ["ai_image_generation", "telegram_notify"]})
    assert resolved == ["ai_image_generation", "telegram_notify"]


def test_resolve_disabled_steps_no_image_adds_image_step():
    from main import _resolve_disabled_steps

    options = RunOptions(limit=None, threads=1, language="en", debug=False, with_image=False, no_image=True)
    resolved = _resolve_disabled_steps(options, {"disabled_steps": []})
    assert resolved == ["ai_image_generation"]


def test_resolve_disabled_steps_with_image_removes_image_step():
    from main import _resolve_disabled_steps

    options = RunOptions(limit=None, threads=1, language="en", debug=False, with_image=True, no_image=False)
    resolved = _resolve_disabled_steps(options, {"disabled_steps": ["ai_image_generation", "telegram_notify"]})
    assert resolved == ["telegram_notify"]


@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_cli_runs_once_even_if_old_listener_config_exists(mock_exists, mock_config_cls, mock_orch_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {
        "disabled_steps": [],
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    mock_orch_cls.return_value.run.return_value = []

    monkeypatch.setattr("sys.argv", ["main.py"])

    from main import main

    main()

    mock_orch_cls.return_value.run.assert_called_once()


@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_passes_custom_language_through_unchanged(
    mock_exists,
    mock_config_cls,
    mock_orch_cls,
    monkeypatch,
):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {"disabled_steps": []}
    mock_orch_cls.return_value.run.return_value = []
    monkeypatch.setattr("sys.argv", ["main.py", "--language", "abc"])

    from main import main

    main()

    assert mock_orch_cls.call_args.kwargs["language"] == "abc"


@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_update_mode_exits_after_saving_config(mock_exists, mock_config_cls, mock_orch_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {"disabled_steps": []}

    monkeypatch.setattr("sys.argv", ["main.py", "--update"])

    from main import main

    main()

    mock_config_cls.return_value.run_onboarding.assert_called_once_with(update=True)
    mock_orch_cls.assert_not_called()
