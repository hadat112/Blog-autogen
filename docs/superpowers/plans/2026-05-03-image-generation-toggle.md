# Image Generation Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add both config-level and CLI-level controls to fully enable/disable AI image generation, with CLI taking precedence.

**Architecture:** Introduce a single resolved boolean (`enable_image_generation`) in `main.py`, derived from config + CLI overrides, then pass it into `Orchestrator`. In `Orchestrator.process_prompt`, gate the image generation block on this boolean so image generation is fully skipped when disabled while keeping current text-only fallback behavior for WP/FB.

**Tech Stack:** Python, argparse, pytest, unittest.mock, existing providers/publishers.

---

## File Structure and Responsibilities

- `main.py`
  - Add CLI flags `--no-image` and `--with-image`.
  - Resolve effective toggle with priority: CLI > config > default `True`.
  - Pass resolved toggle into `Orchestrator` constructor.
- `core/config_manager.py`
  - Add onboarding prompt for `enable_image_generation` (boolean select).
  - Persist value in config.
- `core/orchestrator.py`
  - Accept `enable_image_generation` in constructor.
  - Skip `self.ai.generate_image(...)` entirely when disabled.
- `tests/test_orchestrator.py`
  - Add tests for enabled/disabled behavior and ensure no image-call when disabled.
- `tests/test_config_manager.py`
  - Add/update onboarding assertions for stored `enable_image_generation`.

---

### Task 1: Add failing tests for orchestrator image toggle behavior

**Files:**
- Modify: `tests/test_orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test for config-disabled image generation**

```python
@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.FacebookPagePublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_skips_image_when_disabled(
    mock_storage, mock_fb, mock_wp, mock_sheets, mock_ai, mock_telegram, mock_config
):
    mock_config["enable_image_generation"] = False
    orch = Orchestrator(mock_config, enable_image_generation=False)

    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content",
        "caption": "Test Caption",
        "image_prompt": "Test Image Prompt",
    }
    orch.wp.publish.return_value = "https://wp.url/story"

    result = orch.process_prompt("Test Prompt")

    assert result["status"] == "success"
    orch.ai.generate_image.assert_not_called()
    orch.wp.publish.assert_called_once_with("Test Title", "Test Content", "")
```

- [ ] **Step 2: Write failing test for enabled image generation**

```python
@patch("core.orchestrator.send_telegram_msg")
@patch("core.orchestrator.NineRouterAI")
@patch("core.orchestrator.GoogleSheetsProvider")
@patch("core.orchestrator.WordPressPublisher")
@patch("core.orchestrator.FacebookPagePublisher")
@patch("core.orchestrator.StorageProvider")
def test_process_prompt_generates_image_when_enabled(
    mock_storage, mock_fb, mock_wp, mock_sheets, mock_ai, mock_telegram, mock_config
):
    orch = Orchestrator(mock_config, enable_image_generation=True)

    orch.ai.generate_story.return_value = {
        "title": "Test Title",
        "content": "Test Content",
        "caption": "Test Caption",
        "image_prompt": "Test Image Prompt",
    }
    orch.ai.generate_image.return_value = "https://image.url"
    orch.wp.publish.return_value = "https://wp.url/story"

    result = orch.process_prompt("Test Prompt")

    assert result["status"] == "success"
    orch.ai.generate_image.assert_called_once_with("Test Image Prompt")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py::test_process_prompt_skips_image_when_disabled tests/test_orchestrator.py::test_process_prompt_generates_image_when_enabled -v`

Expected: FAIL because `Orchestrator.__init__` does not accept `enable_image_generation` yet and/or behavior mismatch.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_orchestrator.py
git commit -m "test: add failing coverage for image generation toggle"
```

---

### Task 2: Implement orchestrator toggle logic (minimal pass)

**Files:**
- Modify: `core/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Add constructor argument and resolved property**

```python
class Orchestrator:
    def __init__(self, config, num_threads=5, limit=None, language="uk", debug=False, enable_image_generation=True):
        self.config = config
        self.num_threads = num_threads
        self.limit = limit
        self.language = language
        self.debug = debug
        self.enable_image_generation = bool(enable_image_generation)
        ...
```

- [ ] **Step 2: Gate image generation in `process_prompt`**

```python
# 2. AI Image Generation
if not self.enable_image_generation:
    image_error = "Image generation disabled"
    image_url = ""
    print(f"{task_id} Info: Image generation disabled")
elif image_prompt and str(image_prompt).strip():
    print(f"{task_id} Step 2: Generating image via AI...")
    try:
        image_url = self.ai.generate_image(image_prompt)
        print(f"{task_id} Image Success: {image_url[:50]}...")
    except Exception as e:
        image_error = str(e)
        print(f"{task_id} Warning: Image generation failed: {image_error[:100]}")
else:
    image_error = "Missing image_prompt"
    print(f"{task_id} Warning: No image_prompt from AI")
```

- [ ] **Step 3: Run target tests to verify pass**

Run: `pytest tests/test_orchestrator.py::test_process_prompt_skips_image_when_disabled tests/test_orchestrator.py::test_process_prompt_generates_image_when_enabled -v`

Expected: PASS.

- [ ] **Step 4: Commit orchestrator changes**

```bash
git add core/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: support disabling image generation in orchestrator"
```

---

### Task 3: Add CLI flags and resolve effective toggle

**Files:**
- Modify: `main.py`
- Test: `tests/test_orchestrator.py` (existing behavior validation)

- [ ] **Step 1: Add CLI flags (failing behavior expectation via tests first)**

Add arguments:

```python
parser.add_argument("--no-image", action="store_true", help="Disable AI image generation")
parser.add_argument("--with-image", action="store_true", help="Force-enable AI image generation")
```

- [ ] **Step 2: Add failing test for CLI-over-config priority**

Create a new unit test in `tests/test_orchestrator.py` (or a dedicated `tests/test_main.py` if preferred by repo style) that validates:
- config false + CLI `--with-image` => enable true
- config true + CLI `--no-image` => enable false

Example minimal assertion style (if testing main orchestration by mocking `Orchestrator`):

```python
@patch("main.Orchestrator")
@patch("main.ConfigManager")
def test_main_cli_overrides_image_toggle(mock_cfg_cls, mock_orch_cls, monkeypatch):
    mock_cfg = mock_cfg_cls.return_value
    mock_cfg.config = {"enable_image_generation": False}

    monkeypatch.setattr("sys.argv", ["main.py", "--with-image"])
    from main import main
    main()

    assert mock_orch_cls.call_args.kwargs["enable_image_generation"] is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_main_cli_overrides_image_toggle -v`

Expected: FAIL until resolution logic is implemented.

- [ ] **Step 4: Implement minimal resolution logic in `main.py`**

```python
config_enable_image = config.get("enable_image_generation", True)

if args.no_image and args.with_image:
    print("Error: --no-image and --with-image cannot be used together.")
    sys.exit(1)

if args.no_image:
    effective_enable_image_generation = False
elif args.with_image:
    effective_enable_image_generation = True
else:
    effective_enable_image_generation = bool(config_enable_image)

orchestrator = Orchestrator(
    config=config,
    num_threads=args.threads,
    limit=args.limit,
    language=language,
    debug=args.debug,
    enable_image_generation=effective_enable_image_generation,
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_main_cli_overrides_image_toggle -v`

Expected: PASS.

- [ ] **Step 6: Commit CLI toggle support**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add CLI overrides for image generation toggle"
```

---

### Task 4: Add onboarding config for `enable_image_generation`

**Files:**
- Modify: `core/config_manager.py`
- Modify: `tests/test_config_manager.py`
- Test: `tests/test_config_manager.py`

- [ ] **Step 1: Add failing test assertions for new config key**

In existing onboarding test(s), assert:

```python
assert manager.config["enable_image_generation"] is True
```

or `False` depending on mocked select choice.

- [ ] **Step 2: Update mocked onboarding answers to include new select answer**

Example adjustment in `test_run_onboarding`:

```python
mock_select.return_value.ask.side_effect = [
    "text_model_val",
    "image_model_val",
    "Local",
    "Enabled",  # new toggle prompt choice
]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config_manager.py::test_run_onboarding -v`

Expected: FAIL because config manager does not set key yet.

- [ ] **Step 4: Implement onboarding prompt and persistence**

Add near other config selections:

```python
enable_image_choice = ask_with_validation(
    "Enable AI image generation?",
    "enable_image_generation",
    is_select=True,
    choices=["Enabled", "Disabled"],
    default_val_override="Enabled",
)
self.config["enable_image_generation"] = (enable_image_choice == "Enabled")
```

If existing config value is boolean, map it to select defaults (`Enabled`/`Disabled`) before rendering.

- [ ] **Step 5: Run onboarding tests to verify pass**

Run: `pytest tests/test_config_manager.py::test_run_onboarding tests/test_config_manager.py::test_run_onboarding_no_update -v`

Expected: PASS.

- [ ] **Step 6: Commit config toggle support**

```bash
git add core/config_manager.py tests/test_config_manager.py
git commit -m "feat: add config toggle for image generation"
```

---

### Task 5: Full verification and cleanup

**Files:**
- Modify: none (unless fixes needed)
- Test: `tests/test_orchestrator.py`, `tests/test_config_manager.py`, `tests/test_main.py`

- [ ] **Step 1: Run focused suite for changed behavior**

Run: `pytest tests/test_orchestrator.py tests/test_config_manager.py tests/test_main.py -v`

Expected: PASS.

- [ ] **Step 2: Run full suite**

Run: `pytest -v`

Expected: PASS with no regressions.

- [ ] **Step 3: Manual CLI smoke checks**

Run:
- `python main.py --no-image --limit 1`
- `python main.py --with-image --limit 1`

Expected:
- `--no-image`: no `generate_image` step, WP/FB text-only fallback path.
- `--with-image`: image generation step runs as before.

- [ ] **Step 4: Final commit for any verification-driven fixes**

```bash
git add <only-files-changed-during-verification>
git commit -m "test: finalize image toggle behavior verification"
```

(Only if additional fixes were needed.)

---

## Spec Coverage Check

- Config toggle exists and defaults to enabled: covered in Task 4.
- CLI override flags exist: covered in Task 3.
- Priority CLI > config > default true: covered in Task 3 tests + implementation.
- Full disable skips image generation call entirely: covered in Task 1/Task 2 tests + implementation.
- Existing WP/FB fallback behavior preserved: covered by Task 2 assertions and Task 5 manual checks.

## Placeholder/Consistency Check

- No TODO/TBD placeholders.
- `enable_image_generation` naming is consistent across plan tasks.
- Constructor and call sites use same parameter name.
