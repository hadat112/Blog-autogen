import yaml
import os
import questionary

class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def save_config(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f)

    def run_onboarding(self, update=False):
        def ask_with_validation(prompt, key, validator=None, is_select=False, choices=None, default_val_override=None):
            if not update and key in self.config and self.config[key]:
                return self.config[key]
            
            while True:
                default_val = default_val_override or self.config.get(key, "")
                if is_select:
                    if default_val not in choices:
                        default_val = choices[0]
                    value = questionary.select(prompt, choices=choices, default=default_val).ask()
                else:
                    value = questionary.text(prompt, default=default_val).ask()
                
                if not value:
                    print(f"Value for {key} cannot be empty.")
                    continue

                if validator:
                    print(f"Validating {key}...")
                    success, message = validator(value, self.config)
                    if success:
                        print(f"✅ {message}")
                        return value
                    else:
                        print(f"❌ Validation failed: {message}")
                        action = questionary.select(
                            "What would you like to do?",
                            choices=["Retry", "Skip (use this value anyway)", "Cancel"]
                        ).ask()
                        if action == "Retry":
                            continue
                        elif action == "Skip (use this value anyway)":
                            return value
                        else:
                            import sys
                            sys.exit(0)
                return value

        # Validators
        def validate_9router_key(val, config):
            try:
                import requests
                base_url = config.get("ninerouter_base_url", "https://api.9router.ai/v1").rstrip('/')
                headers = {"Authorization": f"Bearer {val}"}
                resp = requests.get(f"{base_url}/models", headers=headers, timeout=10)
                if resp.status_code == 200:
                    return True, "9router connection successful."
                return False, f"API returned {resp.status_code}: {resp.text}"
            except Exception as e:
                return False, str(e)

        def fetch_models(api_key, base_url):
            try:
                import requests
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=10)
                if resp.status_code == 200:
                    models = [m['id'] for m in resp.json().get('data', [])]
                    return sorted(models)
            except:
                pass
            return []

        def ask_model(prompt, key, models):
            choices = models + ["--- Enter Custom Model Name ---"]
            default_val = self.config.get(key, "")
            if default_val not in choices:
                default_val = choices[0] if choices else ""

            choice = questionary.select(prompt, choices=choices, default=default_val).ask()
            if choice == "--- Enter Custom Model Name ---":
                return questionary.text(f"Enter custom name for {key}:").ask()
            return choice

        def validate_wp(val, config, type="url"):
            # Simple check since we need multiple fields to test fully
            if type == "url" and not val.startswith("http"):
                return False, "URL must start with http:// or https://"
            return True, "Format looks okay."

        def validate_wp_full(config):
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                url = f"{config['wordpress_url'].rstrip('/')}/wp-json/wp/v2/users/me"
                resp = requests.get(
                    url, 
                    auth=HTTPBasicAuth(config['wordpress_username'], config['wordpress_password']),
                    timeout=10
                )
                if resp.status_code == 200:
                    return True, "WordPress credentials are valid."
                return False, f"WordPress returned {resp.status_code}: {resp.text}"
            except Exception as e:
                return False, str(e)

        def validate_telegram(config):
            try:
                import requests
                token = config['telegram_bot_token']
                chat_id = config['telegram_chat_id']
                url = f"https://api.telegram.org/bot{token}/getMe"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    # Optional: test send message
                    return True, f"Telegram Bot '{resp.json()['result']['username']}' is valid."
                return False, f"Telegram returned {resp.status_code}: {resp.text}"
            except Exception as e:
                return False, str(e)

        self.config["ninerouter_base_url"] = ask_with_validation(
            "9router Base URL:", 
            "ninerouter_base_url",
            default_val_override="http://localhost:20128/v1"
        )
        
        self.config["ninerouter_api_key"] = ask_with_validation(
            "9router API Key:", 
            "ninerouter_api_key", 
            validator=validate_9router_key
        )

        print("Fetching available models from 9router...")
        available_models = fetch_models(self.config["ninerouter_api_key"], self.config["ninerouter_base_url"])
        
        self.config["ninerouter_text_model"] = ask_model("Select 9router Model (Text):", "ninerouter_text_model", available_models)
        self.config["ninerouter_image_model"] = ask_model("Select 9router Model (Image):", "ninerouter_image_model", available_models)
        
        self.config["wordpress_url"] = ask_with_validation("WordPress URL:", "wordpress_url", validator=lambda v, c: validate_wp(v, c, "url"))
        self.config["wordpress_username"] = ask_with_validation("WordPress Username:", "wordpress_username")
        self.config["wordpress_password"] = ask_with_validation("WordPress Application Password:", "wordpress_password")
        
        print("Testing WordPress connection...")
        success, msg = validate_wp_full(self.config)
        if not success:
            print(f"⚠️ WordPress connection failed: {msg}")
            if not questionary.confirm("Continue anyway?").ask():
                return self.run_onboarding(update=True) # Restart or let them fix

        self.config["google_sheets_id"] = ask_with_validation("Google Sheets ID:", "google_sheets_id")
        self.config["google_creds_path"] = ask_with_validation("Google Credentials JSON Path:", "google_creds_path")
        
        self.config["telegram_bot_token"] = ask_with_validation("Telegram Bot Token:", "telegram_bot_token")
        self.config["telegram_chat_id"] = ask_with_validation("Telegram Chat ID:", "telegram_chat_id")
        
        print("Testing Telegram connection...")
        success, msg = validate_telegram(self.config)
        if not success:
            print(f"⚠️ Telegram connection failed: {msg}")
            if not questionary.confirm("Continue anyway?").ask():
                return self.run_onboarding(update=True)

        self.config["image_mode"] = ask_with_validation("Image Mode:", "image_mode", is_select=True, choices=["Local", "Direct"])
        
        self.save_config()
