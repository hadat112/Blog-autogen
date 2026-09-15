import json
import logging
import sys

import requests

from app.domain.content_validation import parse_json_object, validate_story_result
from app.domain.story_agent_tools import TOOL_DEFINITIONS


logger = logging.getLogger("story_autogen.generate_story")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
logger.propagate = False


def _debug_payload(value):
    return json.dumps(value, ensure_ascii=False, default=str)


class StoryAgent:
    def __init__(self, ai_client, tools, max_tool_calls=12):
        self.ai = ai_client
        self.tools = tools
        self.max_tool_calls = max_tool_calls

    def generate(self, language, progress=None):
        messages = [
            {
                "role": "system",
                "content": (
                    "Create one original dramatic story using narrative patterns, never copied source prose. "
                    f"Write the title, story, and caption entirely in {language}. "
                    "Use the tools to choose a suitable theme and narrative examples. "
                    "Write a complete, immersive dramatic story between 1500 and 4000 words. "
                    "Begin with a strong emotional or suspenseful hook and introduce the central conflict early. "
                    "Build tension naturally through meaningful actions, sensory details, and behavioral clues. "
                    "Reveal important information at an appropriate pace without forcing a specific plot pattern. "
                    "Keep characters, relationships, names, timeline, locations, and important objects logically consistent. "
                    "Distinguish names and nicknames clearly when relevant, and maintain natural language agreement. "
                    "Do not rush the ending; give the characters believable emotional consequences before resolution. "
                    "Return only one valid JSON object with exactly the keys title, story, and caption. "
                    "Do not include Markdown, explanations, or any text outside the JSON object. "
                    "Caption must be an exact verbatim prefix copied from the beginning of story, "
                    "approximately 45–70 words, ending at a suspenseful breakpoint with proper punctuation."
                ),
            },
            {"role": "user", "content": "Choose useful patterns and write a new story."},
        ]
        calls_used = 0
        request_number = 0
        json_mode_available = True
        while True:
            request_number += 1
            request_payload = _debug_payload(messages)
            tools_payload = _debug_payload(TOOL_DEFINITIONS)
            response_format = {"type": "json_object"} if json_mode_available else None
            print(
                f"[Generate Story AI REQUEST {request_number}] messages={request_payload} "
                f"tools={tools_payload} temperature=0.8 response_format={response_format}",
                file=sys.stderr,
                flush=True,
            )
            logger.info(
                "[Generate Story AI REQUEST %s] messages=%s tools=%s temperature=0.8 response_format=%s",
                request_number,
                request_payload,
                tools_payload,
                response_format,
            )
            try:
                chat_kwargs = {
                    "tools": TOOL_DEFINITIONS,
                    "temperature": 0.8,
                }
                if json_mode_available:
                    chat_kwargs["response_format"] = {"type": "json_object"}
                message = self.ai.chat(messages, **chat_kwargs)
            except requests.HTTPError as exc:
                logger.exception(
                    "[Generate Story AI ERROR %s] status=%s body=%s",
                    request_number,
                    getattr(getattr(exc, "response", None), "status_code", None),
                    getattr(getattr(exc, "response", None), "text", "")[:2000],
                )
                response = getattr(exc, "response", None)
                body = getattr(response, "text", "") or ""
                status_code = getattr(response, "status_code", None)
                body_lower = body.lower()
                if (
                    json_mode_available
                    and status_code in {400, 404, 422}
                    and "response_format" in body_lower
                ):
                    json_mode_available = False
                    logger.warning(
                        "AI provider does not support response_format=json_object; "
                        "retrying this request with parser fallback"
                    )
                    continue
                if status_code in {400, 404, 422} and "tool" in body_lower:
                    raise ValueError("Selected model does not support tool calling; choose another model") from exc
                raise
            except Exception:
                logger.exception("[Generate Story AI ERROR %s] unexpected request failure", request_number)
                raise
            logger.info(
                "[Generate Story AI RESPONSE %s] message=%s",
                request_number,
                _debug_payload(message),
            )
            print(
                f"[Generate Story AI RESPONSE {request_number}] message={_debug_payload(message)}",
                file=sys.stderr,
                flush=True,
            )
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls})
                for call in tool_calls:
                    calls_used += 1
                    if calls_used > self.max_tool_calls:
                        raise ValueError("Story agent exceeded the twelve tool-call limit")
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
            content = message.get("content") or ""
            try:
                parsed = parse_json_object(content)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                response_kind = "empty" if not content.strip() else "invalid JSON"
                raise ValueError(
                    f"AI returned an {response_kind} final story response. "
                    "Generation stopped. Check that the selected model returns JSON "
                    "with title, story, and caption."
                ) from exc
            result = validate_story_result(parsed, min_words=1500, max_words=4000)
            result["tool_calls"] = calls_used
            return result
