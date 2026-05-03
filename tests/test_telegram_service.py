from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from core.telegram_service import TelegramService


def test_telegram_service_build_reply_for_allowed_chat():
    config = {
        "telegram_bot_token": "tkn",
        "telegram_chat_id": "123",
        "enable_image_generation": False,
        "telegram_commands": {"enabled": True},
    }
    runner = MagicMock()
    service = TelegramService(config=config, job_runner=runner)

    reply = service._build_reply(text="/run --limit 1 --with-image", chat_id="123")

    assert "accepted" in reply.lower()
    runner.submit_manual_run.assert_not_called()


def test_telegram_service_build_reply_blocks_other_chat():
    config = {
        "telegram_bot_token": "tkn",
        "telegram_chat_id": "123",
        "enable_image_generation": False,
        "telegram_commands": {"enabled": True},
    }
    runner = MagicMock()
    service = TelegramService(config=config, job_runner=runner)

    reply = service._build_reply(text="/run --limit 1", chat_id="999")

    assert reply is None
    runner.submit_manual_run.assert_not_called()


def test_telegram_service_run_registers_handler_sets_commands_and_starts_polling():
    config = {
        "telegram_bot_token": "tkn",
        "telegram_chat_id": "123",
        "enable_image_generation": False,
        "telegram_commands": {"enabled": True},
    }
    runner = MagicMock()
    service = TelegramService(config=config, job_runner=runner)

    app = MagicMock()
    app.bot.set_my_commands = AsyncMock()
    builder = MagicMock()
    builder.token.return_value.post_init.return_value.build.return_value = app

    with patch("core.telegram_service.ApplicationBuilder") as ab:
        ab.return_value = builder
        service.run()

    assert app.add_handler.call_count == 2
    builder.token.return_value.post_init.assert_called_once()
    post_init_cb = builder.token.return_value.post_init.call_args.args[0]
    asyncio.run(post_init_cb(app))
    app.bot.set_my_commands.assert_called_once()
    command_args = app.bot.set_my_commands.call_args.args[0]
    assert len(command_args) == 2
    assert command_args[0].command == "start"
    assert command_args[1].command == "run"
    app.run_polling.assert_called_once_with(drop_pending_updates=True)


def test_telegram_service_run_disabled_noop():
    config = {
        "telegram_bot_token": "tkn",
        "telegram_commands": {"enabled": False},
    }
    service = TelegramService(config=config, job_runner=MagicMock())

    with patch("core.telegram_service.ApplicationBuilder") as ab:
        service.run()

    ab.assert_not_called()


@patch("core.telegram_service.TelegramService._build_reply", return_value="Run accepted. Starting...")
def test_on_run_edits_single_message_until_done(_mock_build):
    config = {
        "telegram_bot_token": "tkn",
        "telegram_commands": {"enabled": True},
    }
    runner = MagicMock()
    runner.get_job_status.side_effect = [
        {"status": "running", "step_index": 1, "step_name": "Generate story text", "step_progress": 20, "detail": "working"},
        {"status": "running", "step_index": 1, "step_name": "Generate story text", "step_progress": 100, "detail": "done"},
        {"status": "success", "step_index": 5, "step_name": "Publish to Facebook", "step_progress": 100, "detail": "done"},
    ]
    runner.submit_manual_run.return_value = "job-1"
    service = TelegramService(config=config, job_runner=runner)

    message = MagicMock()
    message.text = "/run --limit 1"
    message.reply_text = AsyncMock()
    progress_msg = MagicMock()
    progress_msg.edit_text = AsyncMock()
    message.reply_text.return_value = progress_msg

    update = MagicMock()
    update.effective_message = message
    update.effective_chat.id = 123

    asyncio.run(service._on_run(update, MagicMock()))

    progress_msg.edit_text.assert_awaited()
    runner.submit_manual_run.assert_called_once()
    assert runner.get_job_status.call_count >= 1


def test_telegram_service_on_start_replies_with_usage_help():
    config = {
        "telegram_bot_token": "tkn",
        "telegram_commands": {"enabled": True},
    }
    service = TelegramService(config=config, job_runner=MagicMock())

    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.effective_message = message

    import asyncio
    asyncio.run(service._on_start(update, MagicMock()))

    sent_text = message.reply_text.await_args.args[0]
    assert "How to use this bot" in sent_text
    assert "/run --limit 1" in sent_text
    assert "/run --limit 1 --no-image" in sent_text
    assert "/run --limit 3 --language vi" in sent_text
    assert "telegram_chat_id" in sent_text
    message.reply_text.assert_awaited_once()