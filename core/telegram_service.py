import asyncio
from typing import Optional

from core.telegram_commands import handle_telegram_message, parse_run_options_from_message
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler


class TelegramService:
    START_MESSAGE = (
        "How to use this bot:\n"
        "- /run --limit 1\n"
        "- /run --limit 1 --no-image\n"
        "- /run --limit 3 --language vi\n\n"
        "Note: bot only accepts commands from configured telegram_chat_id."
    )

    STEP_NAME_MAP = {
        1: "Generate story text",
        2: "Generate image",
        3: "Publish to WordPress",
        4: "Log to Google Sheets",
        5: "Publish to Facebook",
    }

    def _render_progress_text(self, state: dict) -> str:
        if not state:
            return "Run status unavailable."

        status = state.get("status")
        step_index = state.get("step_index")
        step_name = state.get("step_name") or self.STEP_NAME_MAP.get(step_index) or "Waiting"
        step_progress = state.get("step_progress", 0)
        detail = state.get("detail", "")

        if status == "success":
            return "Done"
        if status == "error":
            return f"Failed\nStep {step_index or '-'} {step_name}\nReason: {detail or 'unknown error'}"
        if status == "queued":
            return "Run queued..."
        return f"Step {step_index or '-'} {step_name}: {step_progress}%\n{detail}".strip()

    async def _safe_edit_text(self, message, text: str):
        try:
            await message.edit_text(text)
        except Exception:
            return

    async def _poll_and_edit_progress(self, progress_msg, job_id: str):
        last_text = ""
        while True:
            state = self.job_runner.get_job_status(job_id)
            rendered = self._render_progress_text(state)
            if rendered != last_text:
                await self._safe_edit_text(progress_msg, rendered)
                last_text = rendered

            if not state or state.get("status") in {"success", "error"}:
                break

            await asyncio.sleep(1)

    def _is_error_reply(self, reply: str) -> bool:
        return (reply or "").lower().startswith("error:") or "unsupported command" in (reply or "").lower()

    async def _on_run_with_progress(self, update, message, text: str, chat_id: str):
        reply = self._build_reply(text=text, chat_id=chat_id)
        if not reply:
            return

        if self._is_error_reply(reply):
            await message.reply_text(reply)
            return

        try:
            options = parse_run_options_from_message(text=text, config=self.config)
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            return

        job_id = self.job_runner.submit_manual_run(options=options)
        progress_msg = await message.reply_text("Run accepted. Starting...")
        await self._poll_and_edit_progress(progress_msg, job_id)

    def __init__(self, config: dict, job_runner):
        self.config = config
        self.job_runner = job_runner

    def _build_reply(self, text: str, chat_id: str) -> Optional[str]:
        allowed_chat_id = str(self.config.get("telegram_chat_id", ""))
        if not text:
            return None
        if allowed_chat_id and chat_id != allowed_chat_id:
            return None
        return handle_telegram_message(text=text, config=self.config, job_runner=self.job_runner)

    async def _on_run(self, update, context):
        message = update.effective_message
        if not message:
            return
        text = message.text or ""
        chat_id = str(update.effective_chat.id) if update.effective_chat else ""
        await self._on_run_with_progress(update, message, text, chat_id)

    async def _on_start(self, update, context):
        message = update.effective_message
        if not message:
            return
        await message.reply_text(self.START_MESSAGE)

    def run(self):
        if not self.config.get("telegram_commands", {}).get("enabled", False):
            return

        async def _post_init(app):
            await app.bot.set_my_commands([
                BotCommand("start", "How to use this bot"),
                BotCommand("run", "Run pipeline manually"),
            ])

        token = self.config.get("telegram_bot_token")
        app = ApplicationBuilder().token(token).post_init(_post_init).build()
        app.add_handler(CommandHandler("start", self._on_start))
        app.add_handler(CommandHandler("run", self._on_run))
        app.run_polling(drop_pending_updates=True)