from core.run_options import parse_run_tokens


def _tokens_from_message(message: str):
    if message.startswith("/run"):
        return message.split()[1:]
    if message.startswith("/crawl"):
        tokens = message.split()[1:]
        if not tokens or tokens[0].startswith("--"):
            raise ValueError("Usage: /crawl <article_url> [--lang ukraina] [--debug]")
        return ["--crawl", tokens[0], *tokens[1:]]
    raise ValueError("Unsupported command. Use /run ... or /crawl <article_url> ...")


def handle_telegram_message(text: str, config: dict, job_runner) -> str:
    message = (text or "").strip()

    try:
        options = parse_run_tokens(_tokens_from_message(message))
        options.resolve_enable_image(config.get("enable_image_generation", True))
    except Exception as e:
        return f"Error: {e}"

    return "Run accepted. Starting..."


def parse_run_options_from_message(text: str, config: dict):
    message = (text or "").strip()
    options = parse_run_tokens(_tokens_from_message(message))
    options.resolve_enable_image(config.get("enable_image_generation", True))
    return options
