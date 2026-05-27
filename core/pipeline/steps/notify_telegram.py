from core.pipeline.base import BaseStep
from core.pipeline.context import PipelinePorts, PipelineState, ProgressEmitter
from core.pipeline.registry import register_step
from core.pipeline.result import PluginResult


@register_step("telegram_notify")
class TelegramNotifyPlugin(BaseStep):
    def __init__(self, step_index: int):
        self.step_index = step_index

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        step_name = "Telegram Notification"
        self._log(emit, state, self.step_index, step_name, 0, f"{state.log_task_id} Step {self.step_index}: Telegram Notification...")

        if self.name in state.disabled_steps or not ports.tg_config:
            self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Info: Telegram notify disabled or missing config")
            return PluginResult(self.name, "skipped")

        try:
            step_lines = list(state.notification_prefix_lines or [])
            step_lines.append("✅ WordPress" if state.wp_url else f"❌ WordPress: {state.error_msg[:80] or 'Failed to publish'}")
            step_lines.append("✅ Google Sheets" if "google_sheets_log" not in state.disabled_steps and ports.sheets else "⚪ Google Sheets disabled/missing")
            step_lines.append("✅ Facebook post" if state.fb_post_id else f"❌ Facebook post: {state.fb_post_error[:80] or 'Failed'}")

            if state.fb_comment_state == "success":
                step_lines.append("✅ FB comment wp_url")
            elif state.fb_comment_state == "error":
                step_lines.append(f"❌ FB comment: {state.fb_comment_error[:80]}")
            elif "facebook_comment" in state.disabled_steps:
                step_lines.append("⚪ FB comment disabled")
            else:
                step_lines.append("⚪ FB comment skipped (no wp_url)")

            msg = (
                f"✅ <b>Story Processed [{state.language_name}]</b>\n\n"
                f"📝 Title: {state.article.title}\n"
                + "\n".join(step_lines)
                + f"\n\n🔗 WP Link: {state.wp_url or 'N/A'}"
                + f"\n📱 FB Post: {state.fb_post_id or 'N/A'}"
            )

            sender = ports.telegram_sender
            if not sender:
                return PluginResult(self.name, "skipped", error="Missing Telegram sender")

            sender(
                ports.tg_config.get("bot_token"),
                ports.tg_config.get("chat_id"),
                msg,
            )
            return PluginResult(self.name, "success")
        except Exception as e:
            return PluginResult(self.name, "error", error=str(e))
