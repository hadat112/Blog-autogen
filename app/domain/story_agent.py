import json

import requests

from app.domain.content_validation import parse_json_object, validate_story_result
from app.domain.story_agent_tools import TOOL_DEFINITIONS


class StoryAgent:
    def __init__(self, ai_client, tools, max_tool_calls=6):
        self.ai = ai_client
        self.tools = tools
        self.max_tool_calls = max_tool_calls

    def generate(self, language, progress=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Create one original dramatic story using narrative patterns, never copied source prose. "
                    f"Write title, story, and caption entirely in {language}. Use the tools to choose a theme and examples. "
                    "The final story must contain 1500–4000 words. Return final JSON only with title, story, caption. "
                    "Caption must be an exact prefix copied from the beginning of story and end at suspense."
                ),
            },
            {"role": "user", "content": "Choose useful patterns and write a new story."},
        ]
        calls_used = 0
        while True:
            try:
                message = self.ai.chat(messages, tools=TOOL_DEFINITIONS, temperature=0.8)
            except requests.HTTPError as exc:
                response = getattr(exc, "response", None)
                body = getattr(response, "text", "") or ""
                if getattr(response, "status_code", None) in {400, 404, 422} and "tool" in body.lower():
                    raise ValueError("Selected model does not support tool calling; choose another model") from exc
                raise
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls})
                for call in tool_calls:
                    calls_used += 1
                    if calls_used > self.max_tool_calls:
                        raise ValueError("Story agent exceeded the six tool-call limit")
                    function = call.get("function") or {}
                    result = self.tools.call(function.get("name"), function.get("arguments"))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                    if progress:
                        progress(calls_used, function.get("name"))
                continue
            result = validate_story_result(parse_json_object(message.get("content")), min_words=1500, max_words=4000)
            result["tool_calls"] = calls_used
            return result
