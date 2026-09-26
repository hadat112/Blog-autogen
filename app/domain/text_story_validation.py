"""Mechanical checks and deterministic assembly of text story artifacts."""

import re

from app.integrations.ai.openai_compatible import AITextResult


SENTENCE_END = re.compile(r"[.!?…][\s\"'”’»\)\]👇]*$")


def _words(value: str) -> list[str]:
    return value.split()


def validate_stage(stage: str, result: AITextResult, rewrite: str = "") -> str:
    text = (result.content or "").strip()
    if not text:
        raise ValueError(f"{stage} response is empty")
    if result.finish_reason in {"length", "incomplete"}:
        raise ValueError(f"{stage} response is incomplete")
    if stage == "rewrite":
        count = len(_words(text))
        if not 550 <= count <= 650:
            raise ValueError(f"Rewrite must contain 550–650 words; received {count}")
        if not SENTENCE_END.search(text):
            raise ValueError("Rewrite must end at a sentence boundary")
    elif stage == "enhance":
        count = len(_words(text))
        if count < 3000:
            raise ValueError(f"Continuation must contain at least 3,000 words; received {count}")
        if not SENTENCE_END.search(text):
            raise ValueError("Continuation must end at a sentence boundary")
        rewrite_words = _words(rewrite)
        text_words = _words(text)
        if rewrite_words and len(rewrite_words) >= 8 and text_words[:min(20, len(rewrite_words))] == rewrite_words[:min(20, len(rewrite_words))]:
            raise ValueError("Continuation must not repeat the rewrite")
        rewrite_paragraphs = {" ".join(p.split()) for p in re.split(r"\n\s*\n", rewrite) if len(p.split()) >= 12}
        continuation_paragraphs = {" ".join(p.split()) for p in re.split(r"\n\s*\n", text)}
        if rewrite_paragraphs & continuation_paragraphs:
            raise ValueError("Continuation must not repeat rewrite paragraphs")
    elif stage not in {"title", "image_prompt"}:
        raise ValueError(f"Unknown text story stage: {stage}")
    return text


def assemble_story(rewrite: str, continuation: str) -> tuple[str, str]:
    opening = rewrite.strip()
    ending = continuation.strip()
    if not opening or not ending:
        raise ValueError("Both rewrite and continuation are required")
    content = opening + "\n\n" + ending
    words = _words(opening)
    if len(words) <= 70:
        return content, opening
    # A sentence boundary nearest the desired 45–70 word window preserves an exact prefix.
    candidates = [match.end() for match in re.finditer(r"[.!?…][\"'”’»\)\]]*(?=\s|$)", opening)]
    caption = next((opening[:end] for end in candidates if 45 <= len(_words(opening[:end])) <= 70), None)
    if caption is None:
        caption = opening[:candidates[0]] if candidates else opening
    return content, caption
