import os

import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session

from infrastructure.db import models


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def list_accounts(self):
        return self.db.query(models.Account).all()

    def get_account(self, account_id: str):
        return self.db.query(models.Account).filter(models.Account.id == account_id).first()

    def create_account(self, account_data):
        account = models.Account(
            name=account_data.name,
            type=account_data.type,
            config=account_data.config,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_account(self, account_id: str, account_data):
        account = self.get_account(account_id)
        if not account:
            return None

        account.name = account_data.name
        account.type = account_data.type
        account.config = account_data.config
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete_account(self, account_id: str) -> bool:
        account = self.get_account(account_id)
        if not account:
            return False

        self.db.delete(account)
        self.db.commit()
        return True

    def resolve_test_payload(self, test_data: dict):
        account_id = test_data.get("id")
        account_type = test_data.get("type")
        config = test_data.get("config")

        if account_id and not account_type:
            account = self.get_account(account_id)
            if not account:
                return None, None, "not_found"
            account_type = account.type
            config = account.config

        if not account_type or config is None:
            return None, None, "missing"

        return account_type, config, None


def perform_connection_test(account_type: str, config: dict):
    try:
        if account_type == "wp":
            url = f"{config.get('url', '').rstrip('/')}/wp-json/wp/v2/users/me"
            wp_password = config.get("password") or config.get("app_password")
            auth = HTTPBasicAuth(config.get("username"), wp_password)
            resp = requests.get(url, auth=auth, timeout=10)
            resp.raise_for_status()
        elif account_type == "fb":
            page_id = config.get("page_id")
            access_token = config.get("access_token")
            graph_version = config.get("graph_version", "v23.0")
            url = f"https://graph.facebook.com/{graph_version}/{page_id}"
            params = {"access_token": access_token}
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
        elif account_type == "ai":
            base_url = config.get("base_url", "http://localhost:20128/v1").rstrip("/")
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {config.get('api_key')}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        elif account_type == "gs":
            cred_path = config.get("credentials_path") or config.get("credentials_json") or "credentials.json"
            if not os.path.exists(cred_path):
                raise Exception(f"Credentials file not found at: {cred_path}")
            try:
                import gspread

                gc = gspread.service_account(filename=cred_path)
                sh_id = config.get("spreadsheet_id") or config.get("sheet_id")
                if sh_id:
                    gc.open_by_key(sh_id)
            except ImportError:
                pass
            except Exception as ge:
                raise Exception(f"Google Sheets verification failed: {str(ge)}")
        elif account_type == "tg":
            bot_token = config.get("bot_token")
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        else:
            raise Exception(f"Unsupported account type: {account_type}")
        return True, "Credentials verified"
    except Exception as e:
        return False, str(e)


def fetch_wp_categories(config: dict):
    url = config.get("url", "").rstrip("/")
    if not url:
        raise ValueError("WordPress URL is required")

    username = config.get("username")
    password = config.get("password") or config.get("app_password")
    api_url = f"{url}/wp-json/wp/v2/categories"
    params = {"per_page": 100}
    auth = HTTPBasicAuth(username, password) if username and password else None

    resp = requests.get(api_url, auth=auth, params=params, timeout=15)
    resp.raise_for_status()

    return [
        {
            "id": cat["id"],
            "name": cat["name"],
            "count": cat["count"],
        }
        for cat in resp.json()
    ]
