import pytest
from unittest.mock import MagicMock, patch
from providers.google_sheets import GoogleSheetsProvider
from utils.helpers import send_telegram_msg

def test_google_sheets_append_row():
    with patch("gspread.service_account") as mock_sa:
        mock_gc = MagicMock()
        mock_sh = MagicMock()
        mock_wks = MagicMock()
        
        mock_sa.return_value = mock_gc
        mock_gc.open_by_key.return_value = mock_sh
        mock_sh.get_worksheet.return_value = mock_wks
        
        provider = GoogleSheetsProvider("fake_creds.json", "fake_sheet_id")
        data = ["Title", "Content", "Caption", "img_url", "wp_url", "2023-10-01", "published"]
        provider.append_row(data)
        
        mock_wks.append_row.assert_called_once_with(data)

def test_send_telegram_msg():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        token = "fake_token"
        chat_id = "fake_chat_id"
        message = "Hello World"
        
        send_telegram_msg(token, chat_id, message)
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == url
        assert kwargs["json"]["chat_id"] == chat_id
        assert kwargs["json"]["text"] == message
