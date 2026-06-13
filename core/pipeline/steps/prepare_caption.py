from core.pipeline.base import BaseStep
from core.pipeline.context import PipelinePorts, PipelineState, ProgressEmitter
from core.pipeline.registry import register_step
from core.pipeline.result import PluginResult


@register_step("prepare_caption")
class PrepareCaptionPlugin(BaseStep):
    def __init__(self, step_index: int):
        self.step_index = step_index

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        if not state.auto_caption or len(state.article.caption.split()) >= 300:
            return PluginResult(self.name, "skipped")

        words = state.article.content.split()
        start = 0
        if len(words) > 650:
            start = max(0, min(len(words) - 450, int(len(words) * 0.45)))
        excerpt = " ".join(words[start:start + 450])
        state.article.caption = (
            f"{excerpt}...\n\n{state.caption_cta}"
            if state.caption_cta
            else f"{excerpt}..."
        )
        self._log(
            emit,
            state,
            self.step_index,
            "Prepare assets",
            100,
            f"{state.log_task_id} Info: Caption too short, auto-generating excerpt from content...",
        )
        return PluginResult(self.name, "success", {"caption_generated": True})
