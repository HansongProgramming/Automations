"""
Google Sheets tracker utility.
Handles writing analysis results and file links to Google Sheets.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsTracker:
    """Handle writing tracker data to Google Sheets"""
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        Initialize Google Sheets tracker.
        
        Args:
            credentials_path: Path to Google service account credentials JSON file
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets API service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}", exc_info=True)
            raise
    
    async def initialize_sheet(self, sheet_name: str = "Tracker"):
        """
        Initialize sheet with headers if not exists.
        
        Args:
            sheet_name: Name of the sheet/tab
        """
        try:
            # Check if sheet exists
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_exists = any(
                sheet['properties']['title'] == sheet_name
                for sheet in spreadsheet.get('sheets', [])
            )
            
            # Create sheet if it doesn't exist
            if not sheet_exists:
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': [request]}
                ).execute()
                logger.info(f"Created new sheet: {sheet_name}")
            
            # Set headers
            headers = [
                'Timestamp',
                'Client Name',
                'Credit Report URL',
                'Analysis Status',
                'Total Score',
                'Risk Level',
                'Flagged Indicators',
                'PDF Report Link',
                'File ID',
                'Error Message'
            ]
            
            # Write headers to first row
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:J1",
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            
            # Format header row (bold)
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': self._get_sheet_id(sheet_name),
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Initialized sheet '{sheet_name}' with headers")
            
        except Exception as e:
            logger.error(f"Failed to initialize sheet: {str(e)}", exc_info=True)
            raise
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get sheet ID by name"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            raise ValueError(f"Sheet '{sheet_name}' not found")
        except Exception as e:
            logger.error(f"Failed to get sheet ID: {str(e)}")
            raise
    
    async def append_record(
        self,
        client_name: str,
        credit_url: str,
        analysis_result: Dict[str, Any],
        drive_result: Dict[str, Any],
        sheet_name: str = "Tracker"
    ):
        """
        Append a single tracking record to the sheet.
        
        Args:
            client_name: Name of the client
            credit_url: Original credit report URL
            analysis_result: Result from credit analysis
            drive_result: Result from Google Drive upload
            sheet_name: Name of the sheet/tab
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Extract analysis data
            if 'error' in analysis_result or not analysis_result.get('credit_analysis'):
                status = "Failed"
                total_score = ""
                risk_level = ""
                flagged_count = ""
                error_msg = analysis_result.get('error', 'Unknown error')
            else:
                status = "Success"
                analysis = analysis_result.get('credit_analysis', {})
                total_score = analysis.get('total_score', 0)
                risk_level = analysis.get('risk_assessment', {}).get('level', 'Unknown')
                
                # Count flagged indicators
                indicators = analysis.get('affordability_indicators', {})
                flagged_count = sum(
                    1 for indicator in indicators.values()
                    if isinstance(indicator, dict) and indicator.get('flagged', False)
                )
                error_msg = ""
            
            # Extract Drive data
            if drive_result.get('success'):
                pdf_link = f'=HYPERLINK("{drive_result.get("web_view_link", "")}", "View PDF")'
                file_id = drive_result.get('file_id', '')
            else:
                pdf_link = "Upload Failed"
                file_id = ""
                error_msg = error_msg or drive_result.get('error', 'Upload failed')
            
            # Prepare row data
            row = [
                timestamp,
                client_name,
                credit_url,
                status,
                total_score,
                risk_level,
                flagged_count,
                pdf_link,
                file_id,
                error_msg
            ]
            
            # Append row
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:J",
                valueInputOption='USER_ENTERED',  # Allows formulas like HYPERLINK
                body={'values': [row]}
            ).execute()
            
            logger.info(f"Appended record for {client_name} to sheet '{sheet_name}'")
            
        except Exception as e:
            logger.error(f"Failed to append record: {str(e)}", exc_info=True)
            raise
    
    async def append_multiple_records(
        self,
        records: List[Dict[str, Any]],
        sheet_name: str = "Tracker"
    ):
        """
        Append multiple tracking records to the sheet.
        
        Args:
            records: List of dicts with:
                - client_name
                - credit_url
                - analysis_result
                - drive_result
            sheet_name: Name of the sheet/tab
        """
        for record in records:
            await self.append_record(
                client_name=record['client_name'],
                credit_url=record['credit_url'],
                analysis_result=record['analysis_result'],
                drive_result=record['drive_result'],
                sheet_name=sheet_name
            )
        
        logger.info(f"Appended {len(records)} records to sheet '{sheet_name}'")
    
    async def clear_sheet(self, sheet_name: str = "Tracker", keep_headers: bool = True):
        """
        Clear all data from sheet.
        
        Args:
            sheet_name: Name of the sheet/tab
            keep_headers: If True, keeps the header row
        """
        try:
            start_row = 2 if keep_headers else 1
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A{start_row}:J"
            ).execute()
            
            logger.info(f"Cleared sheet '{sheet_name}'")
        except Exception as e:
            logger.error(f"Failed to clear sheet: {str(e)}", exc_info=True)
            raise
