from core.pipeline.base import BaseStep
from core.pipeline.context import PipelinePorts, PipelineState, ProgressEmitter
from core.pipeline.registry import register_step
from core.pipeline.result import PluginResult


@register_step("facebook_publish")
class FacebookPublishPlugin(BaseStep):
    def __init__(self, step_index: int):
        self.step_index = step_index

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        step_name = "Publish to Facebook"
        self._ticks(emit, self.step_index, step_name, state.task_id)
        self._log(emit, state, self.step_index, step_name, 0, f"{state.log_task_id} Step {self.step_index}: Publishing to Facebook Page...")

        has_fb_config = bool(ports.fb)
        if self.name in state.disabled_steps:
            state.fb_post_error = "Facebook publish disabled"
            return PluginResult(self.name, "skipped")
        if not has_fb_config:
            state.fb_post_error = "Missing Facebook config"
            return PluginResult(self.name, "skipped", error=state.fb_post_error)

        try:
            if state.article.image_url:
                try:
                    state.fb_post_id = ports.fb.publish_photo_caption(state.article.caption, state.article.image_url)
                except Exception:
                    state.fb_post_id = ports.fb.publish_text(state.article.caption)
            else:
                state.fb_post_id = ports.fb.publish_text(state.article.caption)

            comment_msg = "скажи «так», nếu muốn tiếp tục đọc câu chuyện này 👇"
            if state.wp_url:
                comment_msg = f"Đọc chi tiết tại link sau: {state.wp_url}"

            if "facebook_comment" in state.disabled_steps:
                state.fb_comment_state = "skipped"
            else:
                try:
                    ports.fb.comment_on_post(state.fb_post_id, comment_msg)
                    state.fb_comment_state = "success"
                except Exception as e:
                    state.fb_comment_state = "error"
                    state.fb_comment_error = str(e)

            return PluginResult(
                self.name,
                "success",
                {
                    "post_id": state.fb_post_id,
                    "comment_state": state.fb_comment_state,
                },
            )
        except Exception as e:
            state.fb_post_error = str(e)
            state.fb_comment_state = "skipped"
            return PluginResult(self.name, "error", error=state.fb_post_error)
