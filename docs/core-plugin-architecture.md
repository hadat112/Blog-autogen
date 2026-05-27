# Core Plugin Architecture

Runtime shape:

1. Entry layer receives a prompt, URL, or API request.
2. `application/` services coordinate DB access and execution.
3. `Orchestrator` prepares normalized input and adapter instances.
4. `PipelineCore` runs ordered plugins.
5. Each plugin owns one external arm and writes its output into `PipelineState`.
6. The final result exposes stable top-level compatibility fields plus detailed `outputs`.

## Top-Level Layout

- `apps/api/`: FastAPI app, schemas, and route modules.
- `application/`: use-case services called by API or future entrypoints.
- `core/`: business flow, pipeline contracts, language/crawl/story orchestration.
- `core/pipeline/steps/`: one plugin file per pipeline step.
- `adapters/`: external integrations such as AI, WordPress, Facebook, Sheets, storage.
- `infrastructure/db/`: SQLAlchemy session and database models.
- `tests/`: grouped by `api`, `adapters`, and `core`.

## Core

`core/pipeline/` contains the shared runtime contract:

- `context.py`: normalized input, mutable state, injected ports, progress emitter.
- `result.py`: status/output/error emitted by one plugin.
- `executor.py`: sequential plugin runner.
- `registry.py`: step registration and creation by `step_id`.

The pipeline core does not know about FastAPI, CLI arguments, SQLite, or account forms.

## Plugins

Current publication plugins:

- `PrepareCaptionPlugin`: creates fallback caption from article content.
- `WordPressPublishPlugin`: publishes article and records `wordpress_url`.
- `GoogleSheetsLogPlugin`: appends reporting row.
- `FacebookPublishPlugin`: posts caption/image and optional comment.
- `TelegramNotifyPlugin`: sends final notification only; no listener or polling loop.

Each plugin lives in `core/pipeline/steps/<step>.py` and registers itself with:

```python
@register_step("wordpress_publish")
class WordPressPublishPlugin(BaseStep):
    ...
```

Each plugin does one job. A missing provider or disabled step returns `skipped`
instead of branching the whole pipeline.

## Outputs

Pipeline output keeps old fields:

```json
{
  "status": "success",
  "title": "...",
  "url": "https://wordpress/post"
}
```

Detailed outputs live under `outputs`:

```json
{
  "outputs": {
    "wordpress_url": "...",
    "facebook_post_id": "...",
    "facebook_comment_state": "success",
    "image_url": "...",
    "final_status": "Success",
    "plugins": [
      {"name": "wordpress_publish", "status": "success", "output": {"url": "..."}}
    ]
  }
}
```

This lets the UI/API show exactly what each external arm did without parsing logs.
