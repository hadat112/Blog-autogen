from typing import Any, Dict, Sequence

from .base import BaseStep
from .context import PipelinePorts, PipelineState, ProgressEmitter


class PipelineCore:
    def __init__(self, plugins: Sequence[BaseStep]):
        self.plugins = list(plugins)

    def run(self, state: PipelineState, ports: PipelinePorts, emit: ProgressEmitter) -> Dict[str, Any]:
        if not state.article.title or not state.article.content:
            raise ValueError("Article payload must include title and content")

        for plugin in self.plugins:
            result = plugin.run(state, ports, emit)
            state.plugin_results.append(result)

        return state.result_dict()
