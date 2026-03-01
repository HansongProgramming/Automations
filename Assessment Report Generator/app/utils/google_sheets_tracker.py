"""
Google Sheets tracker utility.
Uses OAuth credentials (personal Gmail compatible) instead of service account.
Records per-client Drive folder links alongside analysis results.
"""

import logging
import json
import os
import pickle
from typing import List, Dict, Any, Optional
import google.auth.transport.requests
from app.utils.date_utils import format_sheets_timestamp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import requests as req_lib

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
SHEETS_API = 'https://sheets.googleapis.com/v4/spreadsheets'


class GoogleSheetsTracker:
    """
    Handle writing tracker data to Google Sheets.
    Uses OAuth user credentials — works with personal Gmail accounts.
    """

    HEADERS = [
        'Timestamp',
        'Title',
        'First Name',
        'Surname',
        'Date of Birth',
        'Email',
        'Phone',
        'Residence 1',
        'Residence 2',
        'Residence 3',
        'Postal Code',
        'Defendant',
        'Credit Report URL',
        'Analysis Status',
        'Case Status',
        'PDF Report Download',
        'HTML Download',
        'LOC Download',
        'Error Message',
        '',
        '',
        'Client Drive Folder',
    ]

    def __init__(
        self,
        credentials_path: str,
        spreadsheet_id: str,
        token_path: str = 'credentials/oauth-token.pkl'
    ):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.token_path = token_path
        self._creds: Optional[Credentials] = None
        self._sheet_id_cache: dict = {}
        self._initialize()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _initialize(self):
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as f:
                self._creds = pickle.load(f)
            logger.info("Loaded OAuth token from disk")

        if self._creds and self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(google.auth.transport.requests.Request())
            self._save_token()
            logger.info("OAuth token refreshed")
        elif not self._creds or not self._creds.valid:
            logger.warning("OAuth token missing or invalid — starting re-auth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            self._creds = flow.run_local_server(port=0)
            self._save_token()

        logger.info("Google Sheets tracker initialised (OAuth transport)")

    def _save_token(self):
        with open(self.token_path, 'wb') as f:
            pickle.dump(self._creds, f)

    def _headers(self) -> dict:
        if self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(google.auth.transport.requests.Request())
            self._save_token()
        return {
            'Authorization': f'Bearer {self._creds.token}',
            'Content-Type': 'application/json'
        }

    # ------------------------------------------------------------------
    # Sheet management
    # ------------------------------------------------------------------

    def _get_spreadsheet(self) -> dict:
        resp = req_lib.get(
            f"{SHEETS_API}/{self.spreadsheet_id}",
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def _get_sheet_id(self, sheet_name: str) -> int:
        if sheet_name in self._sheet_id_cache:
            return self._sheet_id_cache[sheet_name]
        spreadsheet = self._get_spreadsheet()
        for sheet in spreadsheet.get('sheets', []):
            props = sheet['properties']
            if props['title'] == sheet_name:
                self._sheet_id_cache[sheet_name] = props['sheetId']
                return props['sheetId']
        raise ValueError(f"Sheet '{sheet_name}' not found")

    def _sheet_exists(self, sheet_name: str) -> bool:
        spreadsheet = self._get_spreadsheet()
        return any(
            s['properties']['title'] == sheet_name
            for s in spreadsheet.get('sheets', [])
        )

    def _batch_update(self, requests: list):
        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}:batchUpdate",
            headers=self._headers(),
            json={'requests': requests}
        )
        resp.raise_for_status()
        return resp.json()

    async def initialize_sheet(self, sheet_name: str = "Tracker"):
        try:
            if not self._sheet_exists(sheet_name):
                self._batch_update([{
                    'addSheet': {'properties': {'title': sheet_name}}
                }])
                logger.info(f"Created sheet tab: {sheet_name}")

            sheet_id = self._get_sheet_id(sheet_name)

            resp = req_lib.put(
                f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A1:{self._col_letter(len(self.HEADERS))}1",
                headers=self._headers(),
                params={'valueInputOption': 'RAW'},
                json={'values': [self.HEADERS]}
            )
            resp.raise_for_status()

            self._batch_update([{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.06, 'green': 0.71, 'blue': 0.83}
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor'
                }
            }])

            logger.info(f"Sheet '{sheet_name}' initialised with headers")

        except Exception as e:
            logger.error(f"Failed to initialise sheet: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Record building
    # ------------------------------------------------------------------

    @staticmethod
    def _col_letter(n: int) -> str:
        result = ''
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result

    def _build_row(
        self,
        client_name: str,
        credit_url: str,
        analysis_result: Dict[str, Any],
        drive_result: Dict[str, Any],
        csv_row_data: Optional[Dict[str, Any]] = None,
    ) -> list:
        timestamp = format_sheets_timestamp()
        csv_data = csv_row_data or {}

        title         = csv_data.get('title', '')
        first_name    = csv_data.get('first_name', '')
        surname       = csv_data.get('surname', '')
        date_of_birth = csv_data.get('date_of_birth', '')
        email         = csv_data.get('email', '')
        phone         = csv_data.get('phone', '')
        residence_1   = csv_data.get('residence_1', '')
        residence_2   = csv_data.get('residence_2', '')
        residence_3   = csv_data.get('residence_3', '')
        postal_code   = csv_data.get('postal_code', '')
        defendant     = csv_data.get('defendant', '')

        _CASE_STATUS_LABELS = {'GREEN': 'Strong', 'AMBER': 'Mid', 'RED': 'Weak'}

        if 'error' in analysis_result or not analysis_result.get('credit_analysis'):
            status      = 'Failed'
            case_status = ''
            error_msg   = analysis_result.get('error', 'Unknown error')
        else:
            status      = 'Success'
            error_msg   = ''
            tl          = analysis_result['credit_analysis'].get('traffic_light', '')
            case_status = _CASE_STATUS_LABELS.get(tl, tl)

        if drive_result.get('success'):
            pdf_download_cell  = drive_result.get('pdf_download_link', '')
            html_download_cell = drive_result.get('html_download_link', '')
            loc_download_cell  = drive_result.get('loc_download_link', '')
            folder_cell        = drive_result.get('client_folder_link', '')
        else:
            pdf_download_cell = ''
            html_download_cell = ''
            loc_download_cell = ''
            folder_cell = ''
            error_msg = error_msg or drive_result.get('error', 'Upload failed')

        return [
            timestamp, title, first_name, surname, date_of_birth,
            email, phone, residence_1, residence_2, residence_3, postal_code,
            defendant, credit_url, status, case_status,
            pdf_download_cell,
            html_download_cell,
            loc_download_cell,
            error_msg,
            '', '',
            folder_cell,
        ]

    # ------------------------------------------------------------------
    # Cell colouring
    # ------------------------------------------------------------------

    _CASE_STATUS_COLORS = {
        'Strong': {'red': 0.063, 'green': 0.725, 'blue': 0.506},  # #10b981
        'Mid':    {'red': 0.961, 'green': 0.620, 'blue': 0.043},  # #f59e0b
        'Weak':   {'red': 0.937, 'green': 0.267, 'blue': 0.267},  # #ef4444
    }

    def _color_case_status_cells(self, rows: list, updated_range: str, sheet_name: str):
        """Apply background colour to Case Status cells after a successful append."""
        import re
        # Match any column letter(s) before the row number (not just 'A')
        match = re.search(r'!([A-Z]+)(\d+):', updated_range)
        if not match:
            logger.warning(f"Could not parse updatedRange for colouring: {updated_range!r}")
            return

        start_row = int(match.group(2)) - 1  # Sheets API uses 0-based row indices
        col_idx   = self.HEADERS.index('Case Status')
        sheet_id  = self._get_sheet_id(sheet_name)
        requests  = []

        for i, row in enumerate(rows):
            if len(row) <= col_idx:
                continue
            color = self._CASE_STATUS_COLORS.get(row[col_idx])
            if not color:
                continue
            row_idx = start_row + i
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId':          sheet_id,
                        'startRowIndex':    row_idx,
                        'endRowIndex':      row_idx + 1,
                        'startColumnIndex': col_idx,
                        'endColumnIndex':   col_idx + 1,
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': color,
                            'textFormat': {
                                'bold': True,
                                'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                            },
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat',
                }
            })

        if requests:
            self._batch_update(requests)

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    async def append_record(
        self,
        client_name: str,
        credit_url: str,
        analysis_result: Dict[str, Any],
        drive_result: Dict[str, Any],
        csv_row_data: Optional[Dict[str, Any]] = None,
        sheet_name: str = "Tracker"
    ):
        row = self._build_row(client_name, credit_url, analysis_result, drive_result, csv_row_data)
        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A1:append",
            headers=self._headers(),
            params={'valueInputOption': 'USER_ENTERED', 'insertDataOption': 'INSERT_ROWS'},
            json={'values': [row]}
        )
        resp.raise_for_status()
        updated_range = resp.json().get('updates', {}).get('updatedRange', '')
        self._color_case_status_cells([row], updated_range, sheet_name)
        logger.info(f"Appended row for '{client_name}'")

    async def append_multiple_records(
        self,
        records: List[Dict[str, Any]],
        sheet_name: str = "Tracker"
    ):
        rows = []
        for record in records:
            row = self._build_row(
                client_name=record['client_name'],
                credit_url=record['credit_url'],
                analysis_result=record['analysis_result'],
                drive_result=record['drive_result'],
                csv_row_data=record.get('csv_row_data'),
            )
            rows.append(row)

        if not rows:
            return

        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A1:append",
            headers=self._headers(),
            params={'valueInputOption': 'USER_ENTERED', 'insertDataOption': 'INSERT_ROWS'},
            json={'values': rows}
        )
        resp.raise_for_status()
        updated_range = resp.json().get('updates', {}).get('updatedRange', '')
        self._color_case_status_cells(rows, updated_range, sheet_name)
        logger.info(f"Batch-appended {len(rows)} rows to '{sheet_name}'")

    async def clear_sheet(self, sheet_name: str = "Tracker", keep_headers: bool = True):
        start_row = 2 if keep_headers else 1
        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A{start_row}:{self._col_letter(len(self.HEADERS))}:clear",
            headers=self._headers(),
            json={}
        )
        resp.raise_for_status()
        logger.info(f"Cleared sheet '{sheet_name}' (keep_headers={keep_headers})")