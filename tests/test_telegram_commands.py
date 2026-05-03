from unittest.mock import MagicMock

from core.telegram_commands import handle_telegram_message


def test_handle_run_command_submits_job_with_cli_flags():
    runner = MagicMock()
    config = {"enable_image_generation": False}

    reply = handle_telegram_message(
        text="/run --limit 2 --with-image --threads 3 --language en --debug",
        config=config,
        job_runner=runner,
    )

    assert "accepted" in reply.lower()
    runner.submit_manual_run.assert_not_called()


def test_parse_run_options_from_message_parses_cli_flags():
    from core.telegram_commands import parse_run_options_from_message

    config = {"enable_image_generation": False}

    submitted = parse_run_options_from_message(
        text="/run --limit 2 --with-image --threads 3 --language en --debug",
        config=config,
    )

    assert submitted.limit == 2
    assert submitted.with_image is True
    assert submitted.threads == 3
    assert submitted.language == "en"
    assert submitted.debug is True


def test_handle_run_command_returns_parse_error_on_conflict():
    runner = MagicMock()

    reply = handle_telegram_message(
        text="/run --with-image --no-image",
        config={"enable_image_generation": True},
        job_runner=runner,
    )

    assert "error" in reply.lower()
    runner.submit_manual_run.assert_not_called()


def test_handle_non_run_command_rejected():
    runner = MagicMock()

    reply = handle_telegram_message(
        text="/status",
        config={"enable_image_generation": True},
        job_runner=runner,
    )

    assert "unsupported" in reply.lower()
    runner.submit_manual_run.assert_not_called()
