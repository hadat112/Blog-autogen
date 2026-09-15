import json

import requests

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


def test_story_agent_allows_twelve_tool_calls():
    result = StoryAgent(AgentAI(tool_calls=12), Tools()).generate("English")
    assert result["tool_calls"] == 12


def test_story_agent_enforces_twelve_tool_call_limit():
    with pytest.raises(ValueError, match="twelve tool-call"):
        StoryAgent(AgentAI(tool_calls=13), Tools()).generate("English")


def test_story_agent_accepts_non_empty_caption_mismatch_as_metadata():
    class MismatchAI:
        def chat(self, messages, **kwargs):
            story = "opening " + "word " * 1499
            return {"content": json.dumps({"title": "Title", "story": story, "caption": "Independent caption"})}

    result = StoryAgent(MismatchAI(), Tools()).generate("English")
    assert result["caption_matches_prefix"] is False


def test_story_agent_rejects_empty_caption():
    class EmptyCaptionAI:
        def chat(self, messages, **kwargs):
            story = "opening " + "word " * 1499
            return {"content": json.dumps({"title": "Title", "story": story, "caption": ""})}

    with pytest.raises(ValueError, match="caption is required"):
        StoryAgent(EmptyCaptionAI(), Tools()).generate("English")


def test_story_agent_reports_clear_error_and_stops_on_empty_final_response():
    class AlwaysEmptyAI:
        def __init__(self): self.calls = 0

        def chat(self, messages, **kwargs):
            self.calls += 1
            return {"content": ""}

    ai = AlwaysEmptyAI()
    with pytest.raises(ValueError, match="empty final story response.*Generation stopped"):
        StoryAgent(ai, Tools()).generate("English")
    assert ai.calls == 1


def test_story_agent_accepts_valid_json_fence_with_trailing_commentary():
    class FencedAI:
        def chat(self, messages, **kwargs):
            story = "opening " + "word " * 1499
            payload = json.dumps({"title": "Title", "story": story, "caption": "opening"})
            return {"content": f"```json\n{payload}\n```\nThis extra explanation is ignored."}

    result = StoryAgent(FencedAI(), Tools()).generate("English")

    assert result["title"] == "Title"


def test_story_agent_falls_back_when_provider_rejects_json_mode():
    class JsonModeUnsupportedAI:
        def __init__(self):
            self.calls = []

        def chat(self, messages, **kwargs):
            self.calls.append(kwargs)
            if "response_format" in kwargs:
                response = requests.Response()
                response.status_code = 400
                response._content = b"response_format is not supported"
                raise requests.HTTPError("bad request", response=response)
            story = "opening " + "word " * 1499
            return {"content": json.dumps({"title": "Title", "story": story, "caption": "opening"})}

    ai = JsonModeUnsupportedAI()
    result = StoryAgent(ai, Tools()).generate("English")

    assert result["title"] == "Title"
    assert "response_format" in ai.calls[0]
    assert "response_format" not in ai.calls[1]
