import json

from app.db import models


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_themes",
            "description": "List available story themes with example counts.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_examples",
            "description": "Read titles and narrative structures for a theme. Original article text is never returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "n": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["theme", "n"],
                "additionalProperties": False,
            },
        },
    },
]


class StoryAgentTools:
    def __init__(self, db):
        self.db = db

    def list_themes(self):
        counts = {}
        for (tags,) in self.db.query(models.Article.theme_tags).filter(models.Article.analysis_status == "completed").all():
            for tag in tags or []:
                counts[tag] = counts.get(tag, 0) + 1
        return [{"theme": theme, "count": counts[theme]} for theme in sorted(counts)]

    def get_examples(self, theme, n):
        theme = str(theme or "").strip()
        if not theme:
            raise ValueError("theme is required")
        try:
            limit = min(10, max(1, int(n)))
        except (TypeError, ValueError) as exc:
            raise ValueError("n must be an integer") from exc
        articles = self.db.query(models.Article).filter(
            models.Article.analysis_status == "completed",
            models.Article.structure.is_not(None),
        ).order_by(models.Article.processed_at.desc()).all()
        return [
            {"title": article.original_title, "structure": article.structure}
            for article in articles if theme in (article.theme_tags or [])
        ][:limit]

    def call(self, name, arguments):
        try:
            args = json.loads(arguments or "{}") if isinstance(arguments, str) else dict(arguments or {})
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Tool arguments must be valid JSON") from exc
        if name == "list_themes":
            if args:
                raise ValueError("list_themes accepts no arguments")
            return self.list_themes()
        if name == "get_examples":
            unknown = set(args) - {"theme", "n"}
            if unknown or "theme" not in args or "n" not in args:
                raise ValueError("get_examples requires only theme and n")
            return self.get_examples(args["theme"], args["n"])
        raise ValueError(f"Unsupported agent tool: {name}")
