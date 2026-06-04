import os
import sys
import logging

from core.config_manager import ConfigManager
from core.orchestrator import Orchestrator
from core.run_options import parse_run_tokens
from core.language import normalize_language
from core.article_crawler import extract_article_from_url


IMAGE_STEP_ID = "ai_image_generation"


def _normalize_disabled_steps(value):
    if not isinstance(value, list):
        return []
    normalized = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            continue
        step = item.strip()
        if not step or step in seen:
            continue
        seen.add(step)
        normalized.append(step)
    return normalized


def _effective_disabled_steps_from_config(config: dict) -> list[str]:
    if "disabled_steps" in config:
        return _normalize_disabled_steps(config.get("disabled_steps"))
    if bool(config.get("enable_image_generation", True)):
        return []
    return [IMAGE_STEP_ID]


def _language_name_from_code(language_code: str) -> str:
    if language_code == "uk":
        return "Ukrainian"
    if language_code == "en":
        return "English"
    if language_code == "vi":
        return "Vietnamese"
    if language_code == "lt":
        return "Lithuanian"
    if language_code == "et":
        return "Estonian"
    return language_code


def _resolve_disabled_steps(options, config: dict) -> list[str]:
    disabled_steps = _effective_disabled_steps_from_config(config)

    if options.with_image and options.no_image:
        raise ValueError("--with-image and --no-image cannot be used together")

    if options.no_image and IMAGE_STEP_ID not in disabled_steps:
        disabled_steps.append(IMAGE_STEP_ID)
    if options.with_image:
        disabled_steps = [step for step in disabled_steps if step != IMAGE_STEP_ID]

    return disabled_steps


def main():
    raw_tokens = sys.argv[1:]

    try:
        options = parse_run_tokens(raw_tokens)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except SystemExit:
        print("Error: invalid arguments")
        sys.exit(1)

    try:
        language = normalize_language(options.language)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("story_autogen.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    print("--- Story Auto-Generator Starting ---")

    config_manager = ConfigManager()

    config_file = "config.yaml"
    if not os.path.exists(config_file) or options.update:
        print("Starting onboarding/update process...")
        config_manager.run_onboarding(update=options.update)
        print("Configuration saved.")
        if options.update:
            return

    config = config_manager.config
    if not config:
        print("Error: Configuration is empty. Please run with --update to set up.")
        sys.exit(1)

    try:
        effective_disabled_steps = _resolve_disabled_steps(options, config)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    orchestrator = Orchestrator(
        config=config,
        num_threads=options.threads,
        limit=options.limit,
        language=language,
        debug=options.debug,
        disabled_steps=effective_disabled_steps,
    )

    if options.crawl_url:
        print(f"Crawling article from {options.crawl_url}...")
        article_data = extract_article_from_url(options.crawl_url, orchestrator.ai, language=_language_name_from_code(language))
        orchestrator.process_article_data(article_data)
        return

    prompts_file = "prompts.txt"
    if not os.path.exists(prompts_file):
        base_path = os.path.dirname(os.path.abspath(__file__))
        prompts_file = os.path.join(base_path, "prompts.txt")

    if not os.path.exists(prompts_file):
        print("Error: Prompts file 'prompts.txt' not found in current directory or tool directory.")
        sys.exit(1)

    print(f"Processing stories from {prompts_file}...")
    try:
        results = orchestrator.run(prompts_file)

        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = len(results) - success_count

        print("\n--- Processing Complete ---")
        print(f"Total stories attempted: {len(results)}")
        print(f"Successfully published: {success_count}")
        print(f"Errors encountered: {error_count}")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        logging.exception("Unexpected error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
