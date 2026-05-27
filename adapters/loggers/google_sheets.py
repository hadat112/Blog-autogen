import gspread

class GoogleSheetsProvider:
    def __init__(self, credentials_json, sheet_id):
        """
        Setup gspread and open the sheet.
        :param credentials_json: Path to service account JSON file.
        :param sheet_id: ID of the Google Sheet.
        """
        self.gc = gspread.service_account(filename=credentials_json)
        self.sh = self.gc.open_by_key(sheet_id)
        self.wks = self.sh.get_worksheet(0)

    def append_row(self, data_list):
        """
        Appends a row to the first worksheet.
        Expected columns: title, content, caption, image_url, wordpress_url, date_added, status.
        """
        self.wks.append_row(data_list)
