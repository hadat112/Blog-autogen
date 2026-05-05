import yaml
import os
import questionary

DISABLED_STEP_CHOICES = [
    ("AI text generation", "ai_text_generation"),
    ("AI image generation", "ai_image_generation"),
    ("WordPress publish", "wordpress_publish"),
    ("Google Sheets log", "google_sheets_log"),
    ("Facebook publish", "facebook_publish"),
    ("Facebook comment", "facebook_comment"),
    ("Telegram notify", "telegram_notify"),
]


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


def _effective_disabled_steps(config):
    if "disabled_steps" in config:
        return _normalize_disabled_steps(config.get("disabled_steps"))

    if bool(config.get("enable_image_generation", True)):
        return []

    return ["ai_image_generation"]


class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.config["disabled_steps"] = _effective_disabled_steps(self.config)
        self.config.pop("enable_image_generation", None)

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
        if update:
            return self._run_update_menu_loop()
        return self._run_full_onboarding()

    def _ask_with_validation(self, prompt, key, validator=None, is_select=False, choices=None, default_val_override=None, skip_if_exists=True):
        if skip_if_exists and key in self.config and self.config[key]:
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
                print(f"❌ Validation failed: {message}")
                action = questionary.select(
                    "What would you like to do?",
                    choices=["Retry", "Skip (use this value anyway)", "Cancel"]
                ).ask()
                if action == "Retry":
                    continue
                if action == "Skip (use this value anyway)":
                    return value
                import sys
                sys.exit(0)
            return value

    def _ask_model(self, prompt, key, models):
        choices = models + ["--- Enter Custom Model Name ---"]
        default_val = self.config.get(key, "")
        if default_val not in choices:
            default_val = choices[0] if choices else ""
        choice = questionary.select(prompt, choices=choices, default=default_val).ask()
        if choice == "--- Enter Custom Model Name ---":
            return questionary.text(f"Enter custom name for {key}:").ask()
        return choice

    def _validate_9router_key(self, val, config):
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

    def _fetch_models(self, api_key, base_url):
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=10)
            if resp.status_code == 200:
                return sorted([m['id'] for m in resp.json().get('data', [])])
        except Exception:
            pass
        return []

    def _validate_wp(self, val, _config, type="url"):
        if type == "url" and not val.startswith("http"):
            return False, "URL must start with http:// or https://"
        return True, "Format looks okay."

    def _validate_wp_full(self, config):
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            url = f"{config['wordpress_url'].rstrip('/')}/wp-json/wp/v2/users/me"
            resp = requests.get(url, auth=HTTPBasicAuth(config['wordpress_username'], config['wordpress_password']), timeout=10)
            if resp.status_code == 200:
                return True, "WordPress credentials are valid."
            return False, f"WordPress returned {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, str(e)

    def _validate_telegram(self, config):
        try:
            import requests
            token = config['telegram_bot_token']
            url = f"https://api.telegram.org/bot{token}/getMe"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return True, f"Telegram Bot '{resp.json()['result']['username']}' is valid."
            return False, f"Telegram returned {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, str(e)

    def _ask_keep_or_change(self, key, label):
        has_current = bool(self.config.get(key))
        if not has_current:
            return "Change"
        return questionary.select(
            f"{label}: keep current value?",
            choices=["Keep current", "Change"],
            default="Keep current",
        ).ask()

    def _apply_field_update(self, key, prompt, validator=None, is_select=False, choices=None, default_val_override=None):
        action = self._ask_keep_or_change(key, prompt)
        if action == "Keep current":
            return
        self.config[key] = self._ask_with_validation(
            prompt,
            key,
            validator=validator,
            is_select=is_select,
            choices=choices,
            default_val_override=default_val_override,
            skip_if_exists=False,
        )

    def _update_9router_category(self):
        self._apply_field_update("ninerouter_base_url", "9router Base URL:", default_val_override="http://localhost:20128/v1")
        self._apply_field_update("ninerouter_api_key", "9router API Key:", validator=self._validate_9router_key)
        print("Fetching available models from 9router...")
        models = self._fetch_models(self.config["ninerouter_api_key"], self.config["ninerouter_base_url"])
        if self._ask_keep_or_change("ninerouter_text_model", "Select 9router Model (Text)") == "Change":
            self.config["ninerouter_text_model"] = self._ask_model("Select 9router Model (Text):", "ninerouter_text_model", models)
        if self._ask_keep_or_change("ninerouter_image_model", "Select 9router Model (Image)") == "Change":
            self.config["ninerouter_image_model"] = self._ask_model("Select 9router Model (Image):", "ninerouter_image_model", models)

    def _update_wordpress_category(self):
        self._apply_field_update("wordpress_url", "WordPress URL:", validator=lambda v, c: self._validate_wp(v, c, "url"))
        self._apply_field_update("wordpress_username", "WordPress Username:")
        self._apply_field_update("wordpress_password", "WordPress Application Password:")

    def _update_google_sheets_category(self):
        self._apply_field_update("google_sheets_id", "Google Sheets ID:")
        self._apply_field_update("google_creds_path", "Google Credentials JSON Path:")

    def _update_telegram_category(self):
        self._apply_field_update("telegram_bot_token", "Telegram Bot Token:")
        self._apply_field_update("telegram_chat_id", "Telegram Chat ID:")
        current_enabled = self.config.get("telegram_commands", {}).get("enabled", True)
        choice = questionary.select(
            "Enable Telegram /run command listener?",
            choices=["Enabled", "Disabled"],
            default="Enabled" if current_enabled else "Disabled",
        ).ask()
        self.config["telegram_commands"] = {"enabled": choice == "Enabled"}

    def _update_facebook_category(self):
        self._apply_field_update("facebook_page_id", "Facebook Page ID:")
        self._apply_field_update("facebook_page_access_token", "Facebook Page Access Token:")
        self._apply_field_update("facebook_graph_version", "Facebook Graph API Version:", default_val_override="v23.0")

    def _update_image_category(self):
        self._apply_field_update("image_mode", "Image Mode:", is_select=True, choices=["Local", "Direct"])

    def _update_disabled_steps_category(self):
        current_disabled_steps = set(_effective_disabled_steps(self.config))
        disabled_step_choices = [
            questionary.Choice(title=label, value=step, checked=step in current_disabled_steps)
            for label, step in DISABLED_STEP_CHOICES
        ]
        self.config["disabled_steps"] = _normalize_disabled_steps(
            questionary.checkbox(
                "Disabled steps (space to select multiple):",
                choices=disabled_step_choices,
            ).ask() or []
        )
        self.config.pop("enable_image_generation", None)

    def _update_scheduler_category(self):
        scheduler_enabled = questionary.select(
            "Enable scheduler?",
            choices=["Enabled", "Disabled"],
            default="Enabled" if self.config.get("scheduler", {}).get("enabled", False) else "Disabled",
        ).ask() == "Enabled"
        scheduler_jobs = []
        if scheduler_enabled:
            schedule_mode = questionary.select("Schedule mode:", choices=["Fixed", "RandomWindow"], default="Fixed").ask()
            schedule_time = self._ask_with_validation("Schedule time (HH:MM):", "schedule_time", default_val_override="08:00", skip_if_exists=False)
            schedule_limit_raw = self._ask_with_validation("Schedule --limit:", "schedule_limit", default_val_override="1", skip_if_exists=False)
            schedule_limit = int(schedule_limit_raw) if str(schedule_limit_raw).isdigit() else 1
            schedule_with_image = questionary.select("Schedule run with image?", choices=["Enabled", "Disabled"], default="Enabled").ask() == "Enabled"
            job = {
                "name": "daily-job",
                "enabled": True,
                "mode": "fixed" if schedule_mode == "Fixed" else "random_window",
                "run_options": {
                    "limit": schedule_limit,
                    "threads": 5,
                    "language": "uk",
                    "debug": False,
                    "update": False,
                    "with_image": schedule_with_image,
                    "no_image": not schedule_with_image,
                },
            }
            if job["mode"] == "fixed":
                job["time"] = schedule_time
            else:
                job["base_time"] = schedule_time
                job["jitter_min"] = 5
                job["jitter_max"] = 10
            scheduler_jobs.append(job)
        self.config["scheduler"] = {"enabled": scheduler_enabled, "jobs": scheduler_jobs}

    def _validate_category_after_save(self, category_key):
        if category_key == "wordpress":
            print("Testing WordPress connection...")
            return self._validate_wp_full(self.config)
        if category_key == "telegram":
            print("Testing Telegram connection...")
            return self._validate_telegram(self.config)
        return True, "Validation skipped for this category."

    def _handle_failed_category_validation(self, category_key, message):
        print(f"⚠️ Validation failed: {message}")
        action = questionary.select(
            "What would you like to do?",
            choices=["Retry category", "Continue anyway", "Cancel"],
        ).ask()
        if action == "Retry category":
            return "retry"
        if action == "Continue anyway":
            return "continue"
        import sys
        sys.exit(0)

    def _run_update_menu_loop(self):
        category_handlers = {
            "9router": self._update_9router_category,
            "WordPress": self._update_wordpress_category,
            "Google Sheets": self._update_google_sheets_category,
            "Telegram": self._update_telegram_category,
            "Facebook": self._update_facebook_category,
            "Image settings": self._update_image_category,
            "Disabled steps": self._update_disabled_steps_category,
            "Scheduler": self._update_scheduler_category,
        }
        validation_keys = {
            "WordPress": "wordpress",
            "Telegram": "telegram",
        }

        while True:
            category = questionary.select(
                "Select config category to update:",
                choices=list(category_handlers.keys()) + ["Finish update"],
                default="Finish update",
            ).ask()

            if category == "Finish update":
                self.save_config()
                return

            while True:
                category_handlers[category]()
                self.save_config()
                success, msg = self._validate_category_after_save(validation_keys.get(category, ""))
                if success:
                    break
                if self._handle_failed_category_validation(category, msg) == "retry":
                    continue
                break

            if not questionary.confirm("Update another category?", default=True).ask():
                self.save_config()
                return

    def _run_full_onboarding(self):
        self.config["ninerouter_base_url"] = self._ask_with_validation("9router Base URL:", "ninerouter_base_url", default_val_override="http://localhost:20128/v1", skip_if_exists=True)
        self.config["ninerouter_api_key"] = self._ask_with_validation("9router API Key:", "ninerouter_api_key", validator=self._validate_9router_key, skip_if_exists=True)

        print("Fetching available models from 9router...")
        available_models = self._fetch_models(self.config["ninerouter_api_key"], self.config["ninerouter_base_url"])
        self.config["ninerouter_text_model"] = self._ask_model("Select 9router Model (Text):", "ninerouter_text_model", available_models)
        self.config["ninerouter_image_model"] = self._ask_model("Select 9router Model (Image):", "ninerouter_image_model", available_models)

        self.config["wordpress_url"] = self._ask_with_validation("WordPress URL:", "wordpress_url", validator=lambda v, c: self._validate_wp(v, c, "url"), skip_if_exists=True)
        self.config["wordpress_username"] = self._ask_with_validation("WordPress Username:", "wordpress_username", skip_if_exists=True)
        self.config["wordpress_password"] = self._ask_with_validation("WordPress Application Password:", "wordpress_password", skip_if_exists=True)

        print("Testing WordPress connection...")
        success, msg = self._validate_wp_full(self.config)
        if not success:
            print(f"⚠️ WordPress connection failed: {msg}")
            if not questionary.confirm("Continue anyway?").ask():
                return self._run_full_onboarding()

        self.config["google_sheets_id"] = self._ask_with_validation("Google Sheets ID:", "google_sheets_id", skip_if_exists=True)
        self.config["google_creds_path"] = self._ask_with_validation("Google Credentials JSON Path:", "google_creds_path", skip_if_exists=True)

        self.config["telegram_bot_token"] = self._ask_with_validation("Telegram Bot Token:", "telegram_bot_token", skip_if_exists=True)
        print("Please send a message to your bot on Telegram, then provide the Chat ID below.")
        self.config["telegram_chat_id"] = self._ask_with_validation("Telegram Chat ID:", "telegram_chat_id", skip_if_exists=True)
        self.config["telegram_commands"] = {
            "enabled": questionary.select(
                "Enable Telegram /run command listener?",
                choices=["Enabled", "Disabled"],
                default="Enabled" if self.config.get("telegram_commands", {}).get("enabled", True) else "Disabled",
            ).ask() == "Enabled"
        }

        print("Testing Telegram connection...")
        success, msg = self._validate_telegram(self.config)
        if not success:
            print(f"⚠️ Telegram connection failed: {msg}")
            if not questionary.confirm("Continue anyway?").ask():
                return self._run_full_onboarding()

        self.config["facebook_page_id"] = self._ask_with_validation("Facebook Page ID:", "facebook_page_id", skip_if_exists=True)
        self.config["facebook_page_access_token"] = self._ask_with_validation("Facebook Page Access Token:", "facebook_page_access_token", skip_if_exists=True)
        self.config["facebook_graph_version"] = self._ask_with_validation("Facebook Graph API Version:", "facebook_graph_version", default_val_override="v23.0", skip_if_exists=True)

        self.config["image_mode"] = self._ask_with_validation("Image Mode:", "image_mode", is_select=True, choices=["Local", "Direct"], skip_if_exists=True)
        current_disabled_steps = set(_effective_disabled_steps(self.config))
        disabled_step_choices = [
            questionary.Choice(title=label, value=step, checked=step in current_disabled_steps)
            for label, step in DISABLED_STEP_CHOICES
        ]
        self.config["disabled_steps"] = _normalize_disabled_steps(
            questionary.checkbox(
                "Disabled steps (space to select multiple):",
                choices=disabled_step_choices,
            ).ask() or []
        )
        self.config.pop("enable_image_generation", None)

        self._update_scheduler_category()
        self.save_config()
