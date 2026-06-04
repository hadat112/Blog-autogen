from unittest.mock import patch

import pytest

from core.run_options import RunOptions
from main import normalize_language


def test_normalize_language_full_names_and_codes():
    assert normalize_language("ukraina") == "uk"
    assert normalize_language("ukrainian") == "uk"
    assert normalize_language("english") == "en"
    assert normalize_language("litva") == "lt"
    assert normalize_language("lithuanian") == "lt"
    assert normalize_language("estonia") == "et"
    assert normalize_language("estonian") == "et"
    assert normalize_language("uk") == "uk"
    assert normalize_language("en") == "en"
    assert normalize_language("lt") == "lt"
    assert normalize_language("et") == "et"


def test_normalize_language_rejects_unknown_language():
    with pytest.raises(ValueError):
        normalize_language("japanese")


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
def test_main_update_mode_exits_after_saving_config(mock_exists, mock_config_cls, mock_orch_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {"disabled_steps": []}

    monkeypatch.setattr("sys.argv", ["main.py", "--update"])

    from main import main

    main()

    mock_config_cls.return_value.run_onboarding.assert_called_once_with(update=True)
    mock_orch_cls.assert_not_called()

