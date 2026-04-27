import argparse
import os
import sys
import logging
from core.config_manager import ConfigManager
from core.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Story Auto-Generator CLI")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of stories to generate")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent threads (default: 5)")
    parser.add_argument("--update", action="store_true", help="Update existing configuration")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("story_autogen.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    print("--- Story Auto-Generator Starting ---")

    # 1. Initialize ConfigManager
    config_manager = ConfigManager()
    
    # 2. Check for config or update flag
    config_file = "config.yaml"
    if not os.path.exists(config_file) or args.update:
        print("Starting onboarding/update process...")
        config_manager.run_onboarding(update=args.update)
        print("Configuration saved.")

    # 3. Instantiate Orchestrator
    config = config_manager.config
    if not config:
        print("Error: Configuration is empty. Please run with --update to set up.")
        sys.exit(1)

    orchestrator = Orchestrator(
        config=config,
        num_threads=args.threads,
        limit=args.limit
    )

    # 4. Run the tool
    prompts_file = "prompts.txt"
    if not os.path.exists(prompts_file):
        # Try to find it in the script's directory
        base_path = os.path.dirname(os.path.abspath(__file__))
        prompts_file = os.path.join(base_path, "prompts.txt")
        
    if not os.path.exists(prompts_file):
        print(f"Error: Prompts file 'prompts.txt' not found in current directory or tool directory.")
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
