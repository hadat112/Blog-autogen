from unittest.mock import MagicMock

from core.pipeline import (
    ArticlePayload,
    PipelineCore,
    PipelinePorts,
    PipelineState,
    create_step,
    get_step_class,
)
import core.pipeline.steps  # noqa: F401 - registers built-in steps


def test_pipeline_core_runs_plugins_and_exposes_outputs():
    wp = MagicMock()
    wp.publish.return_value = "https://wp.test/post"
    sheets = MagicMock()
    events = []

    state = PipelineState(
        article=ArticlePayload(
            title="Title",
            content="Short content for publishing",
            caption="short",
            image_url="https://image.test/a.jpg",
        ),
        disabled_steps=set(),
        language_name="English",
        caption_cta="Read more",
        log_task_id="[test]",
    )
    ports = PipelinePorts(wp=wp, wp_config={}, sheets=sheets)
    core = PipelineCore([
        create_step("prepare_caption", step_index=2),
        create_step("wordpress_publish", step_index=3),
        create_step("google_sheets_log", step_index=4),
    ])

    result = core.run(state, ports, lambda *args: events.append(args))

    assert result["status"] == "success"
    assert result["outputs"]["wordpress_url"] == "https://wp.test/post"
    assert [plugin["name"] for plugin in result["outputs"]["plugins"]] == [
        "prepare_caption",
        "wordpress_publish",
        "google_sheets_log",
    ]
    wp.publish.assert_called_once_with(
        "Title",
        "Short content for publishing",
        "https://image.test/a.jpg",
        category_id=None,
    )
    sheets.append_row.assert_called_once()
    assert events


def test_pipeline_registry_creates_builtin_step():
    step = create_step("wordpress_publish", step_index=3)

    assert step.name == "wordpress_publish"
    assert get_step_class("wordpress_publish").__name__ == "WordPressPublishPlugin"
