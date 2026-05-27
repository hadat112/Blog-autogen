from typing import Optional

from .context import PipelinePorts, PipelineState, ProgressEmitter
from .result import PluginResult


class BaseStep:
    step_id = "base"

    @property
    def name(self):
        return self.step_id

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> PluginResult:
        raise NotImplementedError

    def _ticks(self, emit: ProgressEmitter, step_index: int, step_name: str, task_id: Optional[str]):
        for progress in (0, 20, 40, 60, 80, 100):
            emit(step_index, step_name, progress, "working", task_id)

    def _log(
        self,
        emit: ProgressEmitter,
        state: PipelineState,
        step_index: int,
        step_name: str,
        progress: int,
        detail: str,
    ):
        emit(step_index, step_name, progress, detail, state.task_id)
