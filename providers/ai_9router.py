import json
import re

import requests

from .base_ai import BaseAI


REQUIRED_STORY_KEYS = ("title", "content", "caption", "image_prompt")


def _escape_newlines_inside_json_strings(text: str) -> str:
    result = []
    in_string = False
    escaped = False

    for ch in text:
        if ch == '"' and not escaped:
            in_string = not in_string
            result.append(ch)
            continue

        if in_string and ch == '\n':
            result.append('\\n')
            escaped = False
            continue

        result.append(ch)

        if ch == '\\' and not escaped:
            escaped = True
        else:
            escaped = False

    return ''.join(result)


def _has_required_story_keys(value) -> bool:
    return isinstance(value, dict) and all(k in value for k in REQUIRED_STORY_KEYS)


def _extract_first_balanced_json_object(text: str):
    start = text.find('{')
    if start == -1:
        return None

    in_string = False
    escaped = False
    depth = 0

    for i in range(start, len(text)):
        ch = text[i]

        if ch == '"' and not escaped:
            in_string = not in_string

        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        if ch == '\\' and not escaped:
            escaped = True
        else:
            escaped = False

    return None


def _extract_between_markers(text: str, start_marker: str, end_markers):
    start = text.find(start_marker)
    if start == -1:
        return None
    start += len(start_marker)

    end_positions = []
    for marker in end_markers:
        idx = text.find(marker, start)
        if idx != -1:
            end_positions.append(idx)

    if end_positions:
        return text[start:min(end_positions)]

    return text[start:]


def _extract_story_fields_with_regex(text: str):
    found = {}

    pattern_normal = re.compile(
        r'"(?P<key>title|content|caption|image_prompt)"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"',
        re.DOTALL,
    )
    pattern_escaped = re.compile(
        r'\\"(?P<key>title|content|caption|image_prompt)\\"\s*:\s*\\"(?P<value>(?:\\\\.|[^\\"])*)\\"',
        re.DOTALL,
    )

    for pattern in (pattern_normal, pattern_escaped):
        for match in pattern.finditer(text):
            key = match.group("key")
            value = match.group("value")
            value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            found[key] = value

    if "title" not in found:
        v = _extract_between_markers(text, '"title": "', ['",\n "content"'])
        if v is not None:
            found["title"] = v

    if "content" not in found:
        v = _extract_between_markers(text, '"content": "', ['",\n "caption"', '\\",\\n \\"caption\\"'])
        if v is not None:
            found["content"] = v

    if "caption" not in found:
        v = _extract_between_markers(text, '"caption": "', ['",\n "image_prompt"', '\\",\\n \\"image_prompt\\"'])
        if v is not None:
            found["caption"] = v

    if "image_prompt" not in found:
        v = _extract_between_markers(text, '"image_prompt": "', ['"\n}', '"}'])
        if v is None:
            v = _extract_between_markers(text, '\\"image_prompt\\": \\"', ['\\"\\n}', '\\"}'])
        if v is not None:
            found["image_prompt"] = v

    for key, value in list(found.items()):
        value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').strip()
        if value.endswith('"'):
            value = value[:-1]
        found[key] = value

    if _has_required_story_keys(found):
        return found
    return None


def _parse_json_candidate(candidate: str):
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        repaired = _escape_newlines_inside_json_strings(candidate)
        return json.loads(repaired)


def _parse_story_json(content_str: str) -> dict:
    last_error = None

    try:
        parsed = _parse_json_candidate(content_str)
        if _has_required_story_keys(parsed):
            return parsed
    except Exception as e:
        last_error = e

    fenced = re.search(r'```(?:json)?\s*(.*?)\s*```', content_str, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            parsed = _parse_json_candidate(fenced.group(1))
            if _has_required_story_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    sliced = _extract_first_balanced_json_object(content_str)
    if sliced:
        try:
            parsed = _parse_json_candidate(sliced)
            if _has_required_story_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    extracted = _extract_story_fields_with_regex(content_str)
    if extracted:
        return extracted

    if last_error:
        raise last_error
    raise ValueError("Failed to parse story JSON from model output.")


class NineRouterAI(BaseAI):
    def __init__(self, api_key, text_model, image_model, base_url="http://localhost:20128/v1"):
        self.api_key = api_key
        self.text_model = text_model
        self.image_model = image_model
        self.base_url = base_url.rstrip('/')

    def generate_story(self, prompt: str) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "You are a creative writer. Generate a story based on the user's prompt. "
            "Respond ONLY with a JSON object containing these keys: "
            "'title', 'content', 'caption', 'image_prompt'. "
            "The 'image_prompt' should be a descriptive prompt for an AI image generator."
        )
        data = {
            "model": self.text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "stream": False
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        try:
            result = response.json()
        except Exception:
            raise ValueError(f"AI API returned non-JSON response: {response.text}")

        try:
            content_str = result['choices'][0]['message']['content']
            if not content_str:
                raise ValueError("AI returned empty content.")
            return _parse_story_json(content_str)
        except (KeyError, IndexError):
            raise ValueError(f"Unexpected AI response structure: {result}")
        except Exception:
            raise ValueError(f"Failed to parse AI response as JSON. Raw content: {content_str}")

    def generate_image(self, image_prompt: str) -> str:
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.image_model,
            "prompt": image_prompt,
            "n": 1,
            "size": "auto",
            "quality": "auto",
            "background": "auto",
            "image_detail": "high",
            "output_format": "png"
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            import logging
            logging.error(f"AI Image API Error: {response.status_code} - {response.text}")
        response.raise_for_status()
        result = response.json()

        return result['data'][0]['url']
