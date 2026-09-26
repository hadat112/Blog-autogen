from app.domain.text_story_prompts import (
    build_enhance_messages,
    build_image_prompt_messages,
    build_rewrite_messages,
    build_title_messages,
)


def test_enhance_history_preserves_source_and_distinct_instructions():
    messages = build_enhance_messages("Original plot", "Rewritten opening.", "Polish")
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "user"]
    assert "Original plot" in messages[1]["content"]
    assert "550" in messages[1]["content"]
    assert messages[2]["content"] == "Rewritten opening."
    assert "continuation" in messages[3]["content"].lower()
    assert "3,000" in messages[3]["content"]
    assert "Polish" in messages[0]["content"]


def test_metadata_requests_only_need_rewrite_and_target_language():
    for builder in (build_title_messages, build_image_prompt_messages):
        messages = builder("Saved rewrite", "Romanian")
        assert "Saved rewrite" in messages[-1]["content"]
        assert "Romanian" in messages[0]["content"]


def test_rewrite_prompt_uses_pipeline_language_and_source():
    messages = build_rewrite_messages("Source plot", "Czech")
    assert "Source plot" in messages[-1]["content"]
    assert "550" in messages[-1]["content"]
    assert "Czech" in messages[0]["content"]
