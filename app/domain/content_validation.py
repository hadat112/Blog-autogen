import json
import re


def parse_json_object(value):
    text = (value or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("AI response must be a JSON object")
    return parsed


def validate_caption_prefix(content, caption):
    if not caption or not content.startswith(caption):
        raise ValueError("Caption must be an exact prefix of the story")


def validate_story_result(result, *, min_words=None, max_words=None):
    title = str(result.get("title") or "").strip()
    story = str(result.get("story") or result.get("content") or "").strip()
    caption = str(result.get("caption") or "").strip()
    if not title:
        raise ValueError("Story title is required")
    if not story:
        raise ValueError("Story content is required")
    validate_caption_prefix(story, caption)
    word_count = len(story.split())
    if min_words is not None and word_count < min_words:
        raise ValueError(f"Story must contain at least {min_words} words")
    if max_words is not None and word_count > max_words:
        raise ValueError(f"Story must contain at most {max_words} words")
    return {"title": title, "content": story, "caption": caption, "word_count": word_count}
