import pytest
from unittest.mock import patch

from core.run_options import RunOptions

from main import normalize_language
from unittest.mock import MagicMock, ANY, patch as _patch
import copy
import signal
from pathlib import Path


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


@patch("main.parse_run_tokens")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_uses_shared_run_options_parser(mock_exists, mock_config_cls, mock_orch_cls, mock_parse):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {"enable_image_generation": True}
    mock_parse.return_value = RunOptions(
        limit=2,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )
    mock_orch_cls.return_value.run.return_value = []

    from main import main
    main()

    assert mock_orch_cls.call_args.kwargs["limit"] == 2


@patch("main.parse_run_tokens")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_listener_mode_skips_orchestrator_run(
    mock_exists,
    mock_config_cls,
    mock_orch_cls,
    mock_parse,
    monkeypatch,
):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {
        "enable_image_generation": True,
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": False, "jobs": []},
    }
    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )
    monkeypatch.setattr("sys.argv", ["main.py"])

    with _patch("main.run_listener_loop", side_effect=KeyboardInterrupt) as mock_loop:
        from main import main
        main()

    mock_orch_cls.return_value.run.assert_not_called()
    mock_loop.assert_called_once()
    kwargs = mock_loop.call_args.kwargs
    assert "config" in kwargs
    assert "job_runner" in kwargs


@patch("main.parse_run_tokens")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_listener_mode_uses_scheduler_enable(
    mock_exists,
    mock_config_cls,
    mock_orch_cls,
    mock_parse,
    monkeypatch,
):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {
        "enable_image_generation": True,
        "telegram_commands": {"enabled": False},
        "scheduler": {"enabled": True, "jobs": []},
    }
    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )
    monkeypatch.setattr("sys.argv", ["main.py"])

    with _patch("main.run_listener_loop", side_effect=KeyboardInterrupt) as mock_loop:
        from main import main
        main()

    mock_orch_cls.return_value.run.assert_not_called()
    mock_loop.assert_called_once()
    kwargs = mock_loop.call_args.kwargs
    assert "config" in kwargs
    assert "job_runner" in kwargs


@patch("main.parse_run_tokens")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_cli_flags_do_not_enter_listener_mode(
    mock_exists,
    mock_config_cls,
    mock_orch_cls,
    mock_parse,
    monkeypatch,
):
    mock_exists.return_value = True
    mock_config_cls.return_value.config = {
        "enable_image_generation": True,
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=True,
    )
    mock_orch_cls.return_value.run.return_value = []
    monkeypatch.setattr("sys.argv", ["main.py", "--limit", "1", "--no-image"])

    with _patch("main.run_listener_loop") as mock_loop:
        from main import main
        main()

    mock_orch_cls.return_value.run.assert_called_once()
    mock_loop.assert_not_called()


@patch("main.time.sleep")
@patch("main.TelegramService")
@patch("main.SchedulerService")
def test_run_listener_loop_ticks_services(mock_scheduler_cls, mock_telegram_cls, mock_sleep):
    scheduler = MagicMock()
    telegram = MagicMock()
    mock_scheduler_cls.return_value = scheduler
    mock_telegram_cls.return_value = telegram

    from main import run_listener_loop

    run_listener_loop(
        config={"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True}},
        job_runner=MagicMock(),
    )

    telegram.run.assert_called_once()
    scheduler.tick.assert_not_called()
    mock_sleep.assert_not_called()
    mock_telegram_cls.assert_called_once()
    mock_scheduler_cls.assert_called_once()

@patch("main.time.sleep")
@patch("main.TelegramService")
@patch("main.SchedulerService")
def test_run_listener_loop_skips_disabled_services(mock_scheduler_cls, mock_telegram_cls, mock_sleep):
    scheduler = MagicMock()
    telegram = MagicMock()
    mock_scheduler_cls.return_value = scheduler
    mock_telegram_cls.return_value = telegram

    mock_sleep.side_effect = KeyboardInterrupt

    from main import run_listener_loop

    with pytest.raises(KeyboardInterrupt):
        run_listener_loop(
            config={"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False}},
            job_runner=MagicMock(),
        )

    scheduler.tick.assert_not_called()
    telegram.tick.assert_not_called()
    mock_sleep.assert_called_once_with(2)


@patch("main.parse_run_tokens")
@patch("main.TelegramService")
@patch("main.SchedulerService")
@patch("main.JobRunner")
@patch("main.Orchestrator")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_starts_listener_mode_without_prompts_file(
    mock_exists,
    mock_config_cls,
    mock_orch_cls,
    _mock_job_runner,
    _mock_scheduler,
    _mock_telegram,
    mock_parse,
    monkeypatch,
):
    mock_exists.side_effect = lambda p: p == "config.yaml"
    mock_config_cls.return_value.config = {
        "enable_image_generation": True,
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": False, "jobs": []},
    }
    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )
    monkeypatch.setattr("sys.argv", ["main.py"])

    with _patch("main.time.sleep", side_effect=KeyboardInterrupt):
        from main import main
        main()

    mock_orch_cls.return_value.run.assert_not_called()


@patch("main.start_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_start_enables_listener_and_starts_daemon(mock_exists, mock_config_cls, mock_parse, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    config = {
        "telegram_commands": {"enabled": False},
        "scheduler": {"enabled": False, "jobs": []},
    }
    manager = mock_config_cls.return_value
    manager.config = config
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "start"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent started" in out
    assert manager.config["telegram_commands"]["enabled"] is True
    assert manager.config["scheduler"]["enabled"] is True
    manager.save_config.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_start_prints_already_started_when_daemon_exists(mock_exists, mock_config_cls, mock_parse, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False, "jobs": []}}
    manager.save_config = MagicMock()

    mock_start_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "start"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent already started" in out


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_prints_already_stopped_when_no_pid(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent already stopped" in out


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_disables_listener_and_stops_daemon(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    config = {
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    manager = mock_config_cls.return_value
    manager.config = config
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent stopped" in out
    assert manager.config["telegram_commands"]["enabled"] is False
    assert manager.config["scheduler"]["enabled"] is False
    manager.save_config.assert_called_once()
    mock_stop_daemon.assert_called_once()


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_reports_already_stopped_when_stop_returns_false(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent already stopped" in out
    mock_stop_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_toggles_off_then_on_and_restarts_daemon(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    base_config = {
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    manager = mock_config_cls.return_value
    manager.config = copy.deepcopy(base_config)
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent restarted" in out
    assert manager.config["telegram_commands"]["enabled"] is True
    assert manager.config["scheduler"]["enabled"] is True
    assert manager.save_config.call_count == 2
    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_reports_start_status_if_already_started(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = True
    mock_start_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent already started" in out
    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_reports_restart_when_started_successfully(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = True
    mock_start_daemon.return_value = True
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent restarted" in out
    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_reports_already_stopped_if_stop_fails(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = False
    mock_start_daemon.return_value = True
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent restarted" in out
    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_start_reports_started_when_start_returns_true(mock_exists, mock_config_cls, mock_parse, mock_start_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False, "jobs": []}}
    manager.save_config = MagicMock()

    mock_start_daemon.return_value = True
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "start"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent started" in out


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_reports_stopped_when_stop_returns_true(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch, capsys):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = True
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    out = capsys.readouterr().out
    assert "agent stopped" in out


@patch("main._is_process_alive", return_value=False)
@patch("main.os.kill")
def test_stop_daemon_returns_true_on_success(mock_kill, _mock_alive, tmp_path):
    from main import stop_daemon
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("23456")

    assert stop_daemon(pid_file) is True
    mock_kill.assert_called_once_with(23456, signal.SIGTERM)


@patch("main.os.kill")
def test_start_daemon_returns_false_when_already_running(mock_kill, tmp_path):
    from main import start_daemon

    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("22222")

    assert start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file) is False
    mock_kill.assert_called_once_with(22222, 0)


@patch("main.run_listener_loop")
@patch("main.os._exit")
@patch("main.os.getpid", return_value=99999)
@patch("main.os.setsid")
@patch("main.os.fork", side_effect=[0, 0])
def test_start_daemon_returns_true_when_started(mock_fork, mock_setsid, mock_getpid, mock_exit, mock_loop, tmp_path):
    from main import start_daemon

    pid_file = tmp_path / "agent.pid"
    assert start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file) is True
    assert pid_file.read_text().strip() == "99999"
    mock_loop.assert_called_once()
    mock_exit.assert_not_called()


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_calls_stop_even_when_already_disabled(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    mock_stop_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_start_calls_start_even_when_already_enabled(mock_exists, mock_config_cls, mock_parse, mock_start_daemon, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_start_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "start"])

    from main import main
    main()

    mock_start_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_always_calls_stop_then_start(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": True}, "scheduler": {"enabled": True, "jobs": []}}
    manager.save_config = MagicMock()

    mock_stop_daemon.return_value = False
    mock_start_daemon.return_value = False
    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


@patch("main.os.kill")
def test_stop_daemon_returns_false_when_pid_missing_file(mock_kill, tmp_path):
    from main import stop_daemon
    assert stop_daemon(tmp_path / "missing.pid") is False
    mock_kill.assert_not_called()


@patch("main.os.kill", side_effect=ProcessLookupError())
def test_stop_daemon_returns_false_when_process_missing(mock_kill, tmp_path):
    from main import stop_daemon
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("23456")

    assert stop_daemon(pid_file) is False
    assert not pid_file.exists()


@patch("main.os.kill", side_effect=PermissionError())
def test_start_daemon_treats_permission_error_as_running(mock_kill, tmp_path):
    from main import start_daemon
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("12345")

    assert start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file) is False


@patch("main.os.kill", side_effect=OSError())
@patch("main.run_listener_loop")
@patch("main.os._exit")
@patch("main.os.getpid", return_value=99999)
@patch("main.os.setsid")
@patch("main.os.fork", side_effect=[0, 0])
def test_start_daemon_cleans_stale_pid_and_starts(mock_fork, mock_setsid, mock_getpid, mock_exit, mock_loop, mock_kill, tmp_path):
    from main import start_daemon
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("12345")

    assert start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file) is True
    assert pid_file.read_text().strip() == "99999"
    mock_loop.assert_called_once()


@patch("main.os._exit")
@patch("main.os.fork", return_value=123)
def test_start_daemon_parent_exits_after_first_fork(mock_fork, mock_exit, tmp_path):
    from main import start_daemon

    mock_exit.side_effect = SystemExit(0)
    with pytest.raises(SystemExit):
        start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=tmp_path / "agent.pid")
    mock_exit.assert_called_once_with(0)


@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_stop_disables_listener_and_stops_daemon(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, monkeypatch):
    mock_exists.return_value = True
    config = {
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    manager = mock_config_cls.return_value
    manager.config = config
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "stop"])

    from main import main
    main()

    assert manager.config["telegram_commands"]["enabled"] is False
    assert manager.config["scheduler"]["enabled"] is False
    manager.save_config.assert_called_once()
    mock_stop_daemon.assert_called_once()


@patch("main.start_daemon")
@patch("main.stop_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_restart_toggles_off_then_on_and_restarts_daemon(mock_exists, mock_config_cls, mock_parse, mock_stop_daemon, mock_start_daemon, monkeypatch):
    mock_exists.return_value = True
    base_config = {
        "telegram_commands": {"enabled": True},
        "scheduler": {"enabled": True, "jobs": []},
    }
    manager = mock_config_cls.return_value
    manager.config = copy.deepcopy(base_config)
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "restart"])

    from main import main
    main()

    assert manager.config["telegram_commands"]["enabled"] is True
    assert manager.config["scheduler"]["enabled"] is True
    assert manager.save_config.call_count == 2
    mock_stop_daemon.assert_called_once()
    mock_start_daemon.assert_called_once()


def test_read_pid_returns_none_when_missing(tmp_path):
    from main import read_pid
    assert read_pid(tmp_path / "missing.pid") is None


def test_read_pid_returns_int(tmp_path):
    from main import read_pid
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("12345")
    assert read_pid(pid_file) == 12345


def test_remove_pid_file_if_exists(tmp_path):
    from main import remove_pid_file
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("12345")
    remove_pid_file(pid_file)
    assert not pid_file.exists()


@patch("main._is_process_alive", return_value=False)
@patch("main.os.kill")
def test_stop_daemon_kills_process_and_removes_pid(mock_kill, _mock_alive, tmp_path):
    from main import stop_daemon
    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("23456")

    stop_daemon(pid_file)

    mock_kill.assert_called_once_with(23456, signal.SIGTERM)
    assert not pid_file.exists()


def test_stop_daemon_no_pid_file_noop(tmp_path):
    from main import stop_daemon
    stop_daemon(tmp_path / "missing.pid")


@patch("main._is_process_alive", side_effect=[True, True, False])
@patch("main.time.sleep")
@patch("main.os.kill")
def test_stop_daemon_waits_until_process_exits(mock_kill, mock_sleep, mock_alive, tmp_path):
    from main import stop_daemon

    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("12345")

    assert stop_daemon(pid_file=pid_file) is True
    assert not pid_file.exists()
    mock_kill.assert_called_once_with(12345, signal.SIGTERM)
    assert mock_alive.call_count == 3
    mock_sleep.assert_any_call(0.2)
    mock_sleep.assert_any_call(0.2)
    assert mock_sleep.call_count == 2


@patch("main.run_listener_loop")
@patch("main.os._exit")
@patch("main.os.getpid", return_value=99999)
@patch("main.os.setsid")
@patch("main.os.fork", side_effect=[0, 0])
def test_start_daemon_writes_pid_and_runs_loop(mock_fork, mock_setsid, mock_getpid, mock_exit, mock_loop, tmp_path):
    from main import start_daemon

    pid_file = tmp_path / "agent.pid"
    start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file)

    assert pid_file.read_text().strip() == "99999"
    mock_loop.assert_called_once()
    mock_exit.assert_not_called()


@patch("main.os.kill")
def test_start_daemon_refuses_if_already_running(mock_kill, tmp_path):
    from main import start_daemon

    pid_file = tmp_path / "agent.pid"
    pid_file.write_text("22222")

    start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=pid_file)

    mock_kill.assert_called_once_with(22222, 0)


@patch("main.os._exit")
@patch("main.os.fork", return_value=123)
def test_start_daemon_parent_exits_after_first_fork(mock_fork, mock_exit, tmp_path):
    from main import start_daemon

    mock_exit.side_effect = SystemExit(0)
    with pytest.raises(SystemExit):
        start_daemon(config={"telegram_commands": {"enabled": True}}, pid_file=tmp_path / "agent.pid")
    mock_exit.assert_called_once_with(0)


@patch("main.start_daemon")
@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_start_with_custom_pid_arg(mock_exists, mock_config_cls, mock_parse, mock_start_daemon, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False, "jobs": []}}
    manager.save_config = MagicMock()

    mock_parse.return_value = RunOptions(limit=1, threads=5, language="en", debug=False, update=False, with_image=False, no_image=False)
    monkeypatch.setattr("sys.argv", ["main.py", "start", "--pid-file", "/tmp/blog-agent.pid"])

    from main import main
    main()

    called_pid = mock_start_daemon.call_args.kwargs["pid_file"]
    assert str(called_pid) == "/tmp/blog-agent.pid"


@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_unknown_action_exits(mock_exists, mock_config_cls, mock_parse, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {}

    mock_parse.return_value = RunOptions(
        limit=1,
        threads=5,
        language="en",
        debug=False,
        update=False,
        with_image=False,
        no_image=False,
    )

    monkeypatch.setattr("sys.argv", ["main.py", "noop"])

    from main import main
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("main.parse_run_tokens")
@patch("main.ConfigManager")
@patch("main.os.path.exists")
def test_main_help_flag_still_works_for_run_mode(mock_exists, mock_config_cls, mock_parse, monkeypatch):
    mock_exists.return_value = True
    manager = mock_config_cls.return_value
    manager.config = {"telegram_commands": {"enabled": False}, "scheduler": {"enabled": False, "jobs": []}}

    monkeypatch.setattr("sys.argv", ["main.py", "--help"])

    from main import main
    with pytest.raises(SystemExit):
        main()

    mock_parse.assert_called_once()
