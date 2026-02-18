"""
Google Sheets tracker utility.
Uses requests-based transport to avoid httplib2 timeout issues.
Records per-client Drive folder links alongside analysis results.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import google.auth.transport.requests
from google.oauth2 import service_account
import requests as req_lib

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEETS_API = 'https://sheets.googleapis.com/v4/spreadsheets'


class GoogleSheetsTracker:
    """
    Handle writing tracker data to Google Sheets.
    Uses requests transport instead of httplib2 to avoid Windows timeout issues.

    Sheet columns:
        A  Timestamp
        B  Client Name
        C  Credit Report URL
        D  Analysis Status
        E  Risk Level
        F  Flagged Indicators
        G  PDF Link          (clickable)
        H  HTML Link         (clickable)
        I  LOC Folder Link   (clickable)
        J  Client Folder     (clickable - top-level Drive folder)
        K  Error Message
    """

    HEADERS = [
        'Timestamp',
        'Client Name',
        'Credit Report URL',
        'Analysis Status',
        'Risk Level',
        'Flagged Indicators',
        'PDF Report',
        'HTML Report',
        'LOC Documents',
        'Client Drive Folder',
        'Error Message',
    ]

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._creds = None
        self._sheet_id_cache: dict[str, int] = {}
        self._initialize()

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _initialize(self):
        self._creds = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=SCOPES
        )
        self._refresh_token()
        logger.info("Google Sheets tracker initialised (requests transport)")

    def _refresh_token(self):
        auth_request = google.auth.transport.requests.Request()
        self._creds.refresh(auth_request)

    def _headers(self) -> dict:
        if not self._creds.valid:
            self._refresh_token()
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
        """Create sheet tab if missing, write bold headers."""
        try:
            if not self._sheet_exists(sheet_name):
                self._batch_update([{
                    'addSheet': {'properties': {'title': sheet_name}}
                }])
                logger.info(f"Created sheet tab: {sheet_name}")

            sheet_id = self._get_sheet_id(sheet_name)

            # Write headers
            resp = req_lib.put(
                f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A1:{self._col_letter(len(self.HEADERS))}1",
                headers=self._headers(),
                params={'valueInputOption': 'RAW'},
                json={'values': [self.HEADERS]}
            )
            resp.raise_for_status()

            # Bold header row
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
        """Convert 1-based column number to letter (1→A, 11→K)."""
        result = ''
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result

    def _hyperlink(self, url: str, label: str) -> str:
        if url:
            return f'=HYPERLINK("{url}","{label}")'
        return ''

    def _build_row(
        self,
        client_name: str,
        credit_url: str,
        analysis_result: Dict[str, Any],
        drive_result: Dict[str, Any],
    ) -> list:
        """
        Build a single sheet row from analysis + drive results.

        drive_result shape (from uploader):
            {
                'client_folder_link': str,   # link to ClientName/ folder
                'pdf_link':  str,
                'html_link': str,
                'loc_link':  str,            # link to LOC/ subfolder
                'success':   bool,
                'error':     str
            }
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- Analysis fields ---
        if 'error' in analysis_result or not analysis_result.get('credit_analysis'):
            status = 'Failed'
            risk_level = ''
            flagged_count = ''
            error_msg = analysis_result.get('error', 'Unknown error')
        else:
            status = 'Success'
            analysis = analysis_result.get('credit_analysis', {})
            risk_level = analysis.get('risk_assessment', {}).get('level', 'Unknown')
            indicators = analysis.get('affordability_indicators', {})
            flagged_count = sum(
                1 for v in indicators.values()
                if isinstance(v, dict) and v.get('flagged', False)
            )
            error_msg = ''

        # --- Drive link fields ---
        if drive_result.get('success'):
            pdf_cell     = self._hyperlink(drive_result.get('pdf_link', ''),    'View PDF')
            html_cell    = self._hyperlink(drive_result.get('html_link', ''),   'View HTML')
            loc_cell     = self._hyperlink(drive_result.get('loc_link', ''),    'Open LOC Folder')
            folder_cell  = self._hyperlink(drive_result.get('client_folder_link', ''), 'Open Client Folder')
        else:
            pdf_cell = html_cell = loc_cell = folder_cell = ''
            error_msg = error_msg or drive_result.get('error', 'Upload failed')

        return [
            timestamp,
            client_name,
            credit_url,
            status,
            risk_level,
            flagged_count,
            pdf_cell,
            html_cell,
            loc_cell,
            folder_cell,
            error_msg,
        ]

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    async def append_record(
        self,
        client_name: str,
        credit_url: str,
        analysis_result: Dict[str, Any],
        drive_result: Dict[str, Any],
        sheet_name: str = "Tracker"
    ):
        row = self._build_row(client_name, credit_url, analysis_result, drive_result)
        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A:K:append",
            headers=self._headers(),
            params={'valueInputOption': 'USER_ENTERED', 'insertDataOption': 'INSERT_ROWS'},
            json={'values': [row]}
        )
        resp.raise_for_status()
        logger.info(f"Appended row for '{client_name}'")

    async def append_multiple_records(
        self,
        records: List[Dict[str, Any]],
        sheet_name: str = "Tracker"
    ):
        """
        Batch-append multiple records.

        Each record must have:
            client_name, credit_url, analysis_result, drive_result
        """
        rows = []
        for record in records:
            row = self._build_row(
                client_name=record['client_name'],
                credit_url=record['credit_url'],
                analysis_result=record['analysis_result'],
                drive_result=record['drive_result'],
            )
            rows.append(row)

        if not rows:
            return

        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A:K:append",
            headers=self._headers(),
            params={'valueInputOption': 'USER_ENTERED', 'insertDataOption': 'INSERT_ROWS'},
            json={'values': rows}
        )
        resp.raise_for_status()
        logger.info(f"Batch-appended {len(rows)} rows to '{sheet_name}'")

    async def clear_sheet(self, sheet_name: str = "Tracker", keep_headers: bool = True):
        start_row = 2 if keep_headers else 1
        resp = req_lib.post(
            f"{SHEETS_API}/{self.spreadsheet_id}/values/{sheet_name}!A{start_row}:K:clear",
            headers=self._headers(),
            json={}
        )
        resp.raise_for_status()
        logger.info(f"Cleared sheet '{sheet_name}' (keep_headers={keep_headers})")