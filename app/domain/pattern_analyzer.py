import json
import re


REQUIRED_STRUCTURE_KEYS = {"hook", "conflict", "turning_points", "climax", "resolution"}


def parse_structure(value):
    text = (value or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    result = json.loads(text)
    if not isinstance(result, dict) or not REQUIRED_STRUCTURE_KEYS.issubset(result):
        raise ValueError("Pattern analysis returned an invalid structure")
    if not isinstance(result["turning_points"], list):
        raise ValueError("Pattern turning_points must be a list")
    return result


class PatternAnalyzer:
    def __init__(self, ai_client):
        self.ai = ai_client

    def analyze(self, title, content):
        message = self.ai.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Analyze the narrative structure. Return JSON only with hook, conflict, "
                        "turning_points (array), climax, and resolution. Do not rewrite the article."
                    ),
                },
                {"role": "user", "content": f"Title: {title}\n\nArticle:\n{content}"},
            ],
            priority="background",
            temperature=0.1,
        )
        return parse_structure(message.get("content"))
