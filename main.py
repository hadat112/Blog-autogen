import os
import sys
import time
import signal
import logging
from pathlib import Path

from core.config_manager import ConfigManager
from core.orchestrator import Orchestrator
from core.run_options import parse_run_tokens
from core.job_runner import JobRunner
from core.scheduler_service import SchedulerService
from core.telegram_service import TelegramService
from core.language import normalize_language


DEFAULT_PID_FILE = Path(".blog-agent.pid")


def read_pid(pid_file: Path):
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except Exception:
        return None


def remove_pid_file(pid_file: Path):
    if pid_file.exists():
        pid_file.unlink()


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def start_daemon(config: dict, pid_file: Path = DEFAULT_PID_FILE):
    existing_pid = read_pid(pid_file)
    if existing_pid is not None:
        if _is_process_alive(existing_pid):
            return False
        remove_pid_file(pid_file)

    first_fork = os.fork()
    if first_fork > 0:
        os._exit(0)

    os.setsid()

    second_fork = os.fork()
    if second_fork > 0:
        os._exit(0)

    pid_file.write_text(str(os.getpid()))
    job_runner = JobRunner(config=config)
    run_listener_loop(config=config, job_runner=job_runner)
    return True


def stop_daemon(pid_file: Path = DEFAULT_PID_FILE):
    pid = read_pid(pid_file)
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        remove_pid_file(pid_file)
        return False

    for _ in range(25):
        if not _is_process_alive(pid):
            break
        time.sleep(0.2)

    remove_pid_file(pid_file)
    return True


def run_listener_loop(config: dict, job_runner: JobRunner):
    scheduler_service = SchedulerService(config=config, job_runner=job_runner)
    telegram_service = TelegramService(config=config, job_runner=job_runner)

    if config.get("telegram_commands", {}).get("enabled", False):
        telegram_service.run()
        return

    while True:
        if config.get("scheduler", {}).get("enabled", False):
            scheduler_service.tick()
        time.sleep(2)

def main():
    raw_tokens = sys.argv[1:]

    if raw_tokens and raw_tokens[0].strip().lower() in {"start", "stop", "restart"}:
        action = raw_tokens[0].strip().lower()

        pid_file = DEFAULT_PID_FILE
        if len(raw_tokens) >= 3 and raw_tokens[1] == "--pid-file":
            pid_file = Path(raw_tokens[2])

        config_manager = ConfigManager()
        config = config_manager.config or {}
        telegram_cfg = config.get("telegram_commands", {})
        scheduler_cfg = config.get("scheduler", {})

        def set_listener_state(enabled: bool):
            telegram_cfg["enabled"] = enabled
            scheduler_cfg["enabled"] = enabled
            scheduler_cfg.setdefault("jobs", [])
            config["telegram_commands"] = telegram_cfg
            config["scheduler"] = scheduler_cfg
            config_manager.config = config
            config_manager.save_config()

        if action == "start":
            set_listener_state(True)
            started = start_daemon(config=config, pid_file=pid_file)
            print("agent started" if started else "agent already started")
            return

        if action == "stop":
            set_listener_state(False)
            stopped = stop_daemon(pid_file=pid_file)
            print("agent stopped" if stopped else "agent already stopped")
            return

        set_listener_state(False)
        stop_daemon(pid_file=pid_file)
        set_listener_state(True)
        started = start_daemon(config=config, pid_file=pid_file)
        print("agent restarted" if started else "agent already started")
        return

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

    config = config_manager.config
    if not config:
        print("Error: Configuration is empty. Please run with --update to set up.")
        sys.exit(1)

    listener_enabled = config.get("telegram_commands", {}).get("enabled", False) or config.get("scheduler", {}).get("enabled", False)
    should_enter_listener_mode = listener_enabled and len(raw_tokens) == 0

    if should_enter_listener_mode:
        print("Listener mode enabled. Waiting for Telegram commands and scheduler jobs...")
        job_runner = JobRunner(config=config)
        try:
            run_listener_loop(config=config, job_runner=job_runner)
        except KeyboardInterrupt:
            print("\nListener interrupted by user. Exiting...")
        return

    try:
        effective_enable_image_generation = options.resolve_enable_image(
            config.get("enable_image_generation", True)
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    orchestrator = Orchestrator(
        config=config,
        num_threads=options.threads,
        limit=options.limit,
        language=language,
        debug=options.debug,
        enable_image_generation=effective_enable_image_generation,
    )

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
