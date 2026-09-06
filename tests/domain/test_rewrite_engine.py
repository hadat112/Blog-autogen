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


def test_rewrite_keeps_only_current_original_chunk_and_prior_assistant_output():
    ai = FakeAI()
    source = "original-one\n\noriginal-two"
    result = RewriteEngine(ai, chunk_size=12).rewrite("Old", source, "Italian")
    assert result["caption"] == "First rewrite"
    second_messages = ai.calls[1]
    assert any(message["role"] == "assistant" and message["content"] == "First rewrite" for message in second_messages)
    assert "original-one" not in second_messages[-1]["content"]
    assert "original-two" in second_messages[-1]["content"]
    assert [message["role"] for message in second_messages] == ["system", "user", "assistant", "user"]
    final_roles = [message["role"] for message in ai.calls[-1]]
    assert final_roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert "original-one" not in str(ai.calls[-1])
    assert "original-two" not in str(ai.calls[-1])


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
