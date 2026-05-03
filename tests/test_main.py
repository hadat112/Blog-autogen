import pytest
from unittest.mock import patch

from main import normalize_language


def test_normalize_language_full_names_and_codes():
    assert normalize_language("ukraina") == "uk"
    assert normalize_language("ukrainian") == "uk"
    assert normalize_language("english") == "en"
    assert normalize_language("uk") == "uk"
    assert normalize_language("en") == "en"


def test_normalize_language_rejects_unknown_language():
    with pytest.raises(ValueError):
        normalize_language("japanese")


@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_cli_with_image_overrides_config_false(mock_exists, mock_config_cls, mock_orch_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config = mock_config_cls.return_value
    mock_config.config = {"enable_image_generation": False}
    mock_orch_cls.return_value.run.return_value = []

    monkeypatch.setattr("sys.argv", ["main.py", "--with-image"])

    from main import main
    main()

    assert mock_orch_cls.call_args.kwargs["enable_image_generation"] is True


@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_cli_no_image_overrides_config_true(mock_exists, mock_config_cls, mock_orch_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config = mock_config_cls.return_value
    mock_config.config = {"enable_image_generation": True}
    mock_orch_cls.return_value.run.return_value = []

    monkeypatch.setattr("sys.argv", ["main.py", "--no-image"])

    from main import main
    main()

    assert mock_orch_cls.call_args.kwargs["enable_image_generation"] is False


@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_cli_conflicting_image_flags_exits(mock_exists, mock_config_cls, monkeypatch):
    mock_exists.return_value = True
    mock_config = mock_config_cls.return_value
    mock_config.config = {"enable_image_generation": True}

    monkeypatch.setattr("sys.argv", ["main.py", "--no-image", "--with-image"])

    from main import main
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
