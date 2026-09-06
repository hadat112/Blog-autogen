import json

import pytest

from app.domain.story_agent import StoryAgent


class Tools:
    def __init__(self): self.calls = []
    def call(self, name, arguments): self.calls.append((name, arguments)); return [{"theme": "family", "count": 2}]


class AgentAI:
    def __init__(self, tool_calls=1): self.turn = 0; self.tool_calls = tool_calls
    def chat(self, messages, **kwargs):
        self.turn += 1
        if self.turn <= self.tool_calls:
            return {"tool_calls": [{"id": f"c{self.turn}", "function": {"name": "list_themes", "arguments": "{}"}}]}
        story = "opening " + "word " * 1499
        return {"content": json.dumps({"title": "Title", "story": story, "caption": "opening"})}


def test_story_agent_runs_tools_and_returns_validated_story():
    tools = Tools()
    result = StoryAgent(AgentAI(), tools).generate("English")
    assert result["tool_calls"] == 1
    assert tools.calls[0][0] == "list_themes"
    assert result["content"].startswith(result["caption"])


def test_story_agent_enforces_six_tool_call_limit():
    with pytest.raises(ValueError, match="six tool-call"):
        StoryAgent(AgentAI(tool_calls=7), Tools()).generate("English")
