from datetime import datetime

from core.pipeline.base import BaseStep
from core.pipeline.context import PipelinePorts, PipelineState, ProgressEmitter
from core.pipeline.registry import register_step
from core.pipeline.result import PluginResult


@register_step("google_sheets_log")
class GoogleSheetsLogPlugin(BaseStep):
    def __init__(self, step_index: int):
        self.step_index = step_index

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        step_name = "Log to Google Sheets"
        self._ticks(emit, self.step_index, step_name, state.task_id)
        self._log(emit, state, self.step_index, step_name, 0, f"{state.log_task_id} Step {self.step_index}: Logging to Google Sheets...")

        final_status = state.status if state.status == "Success" else f"{state.status}: {state.error_msg}"
        if state.status_note and state.status == "Success":
            final_status = state.status_note

        if self.name in state.disabled_steps or not ports.sheets:
            self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Info: Google Sheets log disabled or not configured")
            return PluginResult(self.name, "skipped")

        ports.sheets.append_row([
            state.article.title,
            state.article.content,
            state.article.caption,
            state.article.image_url,
            state.wp_url,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            final_status,
        ])
        self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Sheets Success.")
        return PluginResult(self.name, "success")
