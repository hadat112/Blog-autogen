import json

import pytest

from app.domain.rewrite_engine import RewriteEngine


class FakeAI:
    def __init__(self):
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        if "Return JSON only" in messages[-1]["content"]:
            return {"content": json.dumps({"title": "New title", "caption": "First rewrite"})}
        return {"content": "First rewrite" if len(self.calls) == 1 else "Second rewrite"}

    def translate_title(self, title, language):
        return f"Translated {title}"


def test_rewrite_keeps_full_source_and_rewritten_message_history():
    ai = FakeAI()
    source = "original-one\n\noriginal-two"
    result = RewriteEngine(ai, chunk_size=12).rewrite("Old", source, "Italian")
    assert result["title"] == "Translated Old"
    assert result["caption"] == "First rewrite"
    second_messages = ai.calls[1]
    assert any(message["role"] == "assistant" and message["content"] == "First rewrite" for message in second_messages)
    assert "original-one" in str(second_messages)
    assert "original-two" in second_messages[-1]["content"]
    assert [message["role"] for message in second_messages] == ["system", "user", "assistant", "user"]
    final_roles = [message["role"] for message in ai.calls[-1]]
    assert final_roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert "original-one" in str(ai.calls[-1])
    assert "original-two" in str(ai.calls[-1])


def test_rewrite_keeps_non_prefix_caption_as_review_warning():
    class BadAI(FakeAI):
        def chat(self, messages, **kwargs):
            if "Return JSON only" in messages[-1]["content"]:
                return {"content": '{"title":"New","caption":"not copied"}'}
            return {"content": "Story opening"}

    result = RewriteEngine(BadAI()).rewrite("Old", "source", "English")
    assert result["caption_matches_prefix"] is False
    assert "Caption differs from story opening" in result["warnings"]


def test_rewrite_still_rejects_empty_caption():
    class EmptyCaptionAI(FakeAI):
        def chat(self, messages, **kwargs):
            if "Return JSON only" in messages[-1]["content"]:
                return {"content": '{"title":"New","caption":""}'}
            return {"content": "Story opening"}

    with pytest.raises(ValueError, match="empty rewritten caption"):
        RewriteEngine(EmptyCaptionAI()).rewrite("Old", "source", "English")


def test_rewrite_reports_metadata_phase_after_all_chunks():
    ai = FakeAI()
    phases = []

    RewriteEngine(ai).rewrite("Old", "source", "English", lambda index, total, phase, meta: phases.append(phase))

    assert phases == ["rewriting", "rewriting", "metadata"]


def test_rewrite_normalizes_dialogue_quotes():
    class QuotesAI(FakeAI):
        def chat(self, messages, **kwargs):
            if "Return JSON only" in messages[-1]["content"]:
                return {"content": '{"title":"New","caption":"„Ahoj,“ řekla."}'}
            return {"content": '"Ahoj," řekla.'}

    res = RewriteEngine(QuotesAI()).rewrite("Old", "source", "Czech")
    assert res["content"] == "„Ahoj,“ řekla."
    assert res["caption"] == "„Ahoj,“ řekla."
