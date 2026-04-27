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
        def ask_with_default(prompt, key, is_select=False, choices=None):
            if not update and key in self.config:
                return self.config[key]
            
            default_val = self.config.get(key, "")
            if is_select:
                return questionary.select(prompt, choices=choices, default=default_val).ask()
            else:
                return questionary.text(prompt, default=default_val).ask()

        self.config["ninerouter_api_key"] = ask_with_default("9router API Key:", "ninerouter_api_key")
        self.config["ninerouter_text_model"] = ask_with_default("9router Model (Text):", "ninerouter_text_model")
        self.config["ninerouter_image_model"] = ask_with_default("9router Model (Image):", "ninerouter_image_model")
        self.config["wordpress_url"] = ask_with_default("WordPress URL:", "wordpress_url")
        self.config["wordpress_username"] = ask_with_default("WordPress Username:", "wordpress_username")
        self.config["wordpress_password"] = ask_with_default("WordPress Application Password:", "wordpress_password")
        self.config["google_sheets_id"] = ask_with_default("Google Sheets ID:", "google_sheets_id")
        self.config["google_creds_path"] = ask_with_default("Google Credentials JSON Path:", "google_creds_path")
        self.config["telegram_bot_token"] = ask_with_default("Telegram Bot Token:", "telegram_bot_token")
        self.config["telegram_chat_id"] = ask_with_default("Telegram Chat ID:", "telegram_chat_id")
        self.config["image_mode"] = ask_with_default("Image Mode:", "image_mode", is_select=True, choices=["Local", "Direct"])
        
        self.save_config()
