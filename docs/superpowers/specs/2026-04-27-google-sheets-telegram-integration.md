# Design Spec: Google Sheets & Telegram Integration

## 1. Introduction
This feature adds the ability to log story generation results to a Google Sheet and send notifications via Telegram.

## 2. Architecture

### 2.1 Google Sheets Provider (`providers/google_sheets.py`)
- **Class**: `GoogleSheetsProvider`
- **Responsibilities**:
    - Authenticate with Google Sheets API using service account credentials.
    - Append rows to a specific Google Sheet.
- **Methods**:
    - `__init__(self, credentials_json, sheet_id)`: Initializes the `gspread` client and opens the spreadsheet.
    - `append_row(self, data_list)`: Appends a list of values to the first worksheet.
- **Data Format**: The expected columns are `title`, `content`, `caption`, `image_url`, `wordpress_url`, `date_added`, `status`.

### 2.2 Telegram Helper (`utils/helpers.py`)
- **Function**: `send_telegram_msg(token, chat_id, message)`
- **Responsibilities**:
    - Send a text message to a Telegram chat using the Telegram Bot API.
- **Implementation**: Uses the `requests` library to POST to `https://api.telegram.org/bot<token>/sendMessage`.

### 2.3 Testing (`tests/test_integrations.py`)
- **Mocking**:
    - Mock `gspread.service_account` and the resulting sheet/worksheet objects.
    - Mock `requests.post` for Telegram API calls.
- **Test Cases**:
    - Verify `append_row` calls the `gspread` append method with correct data.
    - Verify `send_telegram_msg` calls `requests.post` with the correct URL and payload.

## 3. Implementation Plan
1. Implement `GoogleSheetsProvider` in `providers/google_sheets.py`.
2. Implement `send_telegram_msg` in `utils/helpers.py`.
3. Create unit tests in `tests/test_integrations.py`.
4. Run tests and verify success.
