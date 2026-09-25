from app.domain.pipeline.base import BaseStep
from app.domain.pipeline.context import PipelinePorts, PipelineState, ProgressEmitter
from app.domain.pipeline.registry import register_step
from app.domain.pipeline.result import PluginResult


@register_step("wordpress_publish")
class WordPressPublishPlugin(BaseStep):
    def __init__(self, step_index: int):
        self.step_index = step_index

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        step_name = "Publish to WordPress"
        self._ticks(emit, self.step_index, step_name, state.task_id)
        self._log(emit, state, self.step_index, step_name, 0, f"{state.log_task_id} Step {self.step_index}: Publishing to WordPress...")

        if self.name in state.disabled_steps or not ports.wp:
            self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Info: WordPress publish disabled or not configured")
            return PluginResult(self.name, "skipped")

        try:
            category_id = (ports.wp_config or {}).get("category_id")
            state.wp_url = ports.wp.publish(
                state.article.title,
                state.article.content,
                state.article.image_url,
                category_id=category_id,
            )
            warnings = []
            if getattr(ports.wp, "last_warning", ""):
                warnings.append(ports.wp.last_warning)
                self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Warning: {ports.wp.last_warning}")
            self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} WP Success: {state.wp_url}")
            return PluginResult(self.name, "success", {"url": state.wp_url, "warnings": warnings})
        except Exception as e:
            state.status = "Partial Success (WP Error)"
            state.error_msg = str(e)
            self._log(emit, state, self.step_index, step_name, 100, f"{state.log_task_id} Warning: WordPress publishing failed: {state.error_msg[:100]}")
            return PluginResult(self.name, "error", error=state.error_msg)
