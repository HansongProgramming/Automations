"""
Google Drive file upload utility.
Handles uploading PDF files to Google Drive and returning shareable links.
"""

import logging
import io
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleDriveUploader:
    """Handle uploads to Google Drive"""
    
    def __init__(self, credentials_path: str, folder_id: Optional[str] = None):
        """
        Initialize Google Drive uploader.
        
        Args:
            credentials_path: Path to Google service account credentials JSON file
            folder_id: Optional Google Drive folder ID to upload files to
        """
        self.credentials_path = credentials_path
        self.folder_id = folder_id
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {str(e)}", exc_info=True)
            raise
    
    async def upload_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        folder_id: Optional[str] = None
    ) -> dict:
        """
        Upload a PDF file to Google Drive.
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Name for the file (e.g., "Report.pdf")
            folder_id: Optional folder ID (overrides instance folder_id)
            
        Returns:
            dict with:
                - file_id: Google Drive file ID
                - web_view_link: Link to view file in browser
                - web_content_link: Direct download link
                - success: boolean
                - error: error message if failed
        """
        try:
            # Use provided folder_id or instance folder_id
            target_folder = folder_id or self.folder_id
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'mimeType': 'application/pdf'
            }
            
            # If folder_id is specified, add it to parents
            if target_folder:
                file_metadata['parents'] = [target_folder]
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            # Make file publicly accessible (optional - adjust permissions as needed)
            try:
                self.service.permissions().create(
                    fileId=file['id'],
                    body={
                        'type': 'anyone',
                        'role': 'reader'
                    }
                ).execute()
                logger.info(f"File {filename} uploaded and made publicly accessible")
            except HttpError as e:
                logger.warning(f"Could not set public permissions for {filename}: {str(e)}")
            
            logger.info(f"Successfully uploaded {filename} to Google Drive (ID: {file['id']})")
            
            return {
                'success': True,
                'file_id': file['id'],
                'web_view_link': file.get('webViewLink', ''),
                'web_content_link': file.get('webContentLink', ''),
                'filename': filename
            }
            
        except HttpError as e:
            error_msg = f"Google Drive API error: {str(e)}"
            logger.error(f"Failed to upload {filename}: {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to upload {filename}: {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'filename': filename
            }
    
    async def upload_multiple_pdfs(
        self,
        pdf_files: list[dict],
        folder_id: Optional[str] = None
    ) -> list[dict]:
        """
        Upload multiple PDF files to Google Drive.
        
        Args:
            pdf_files: List of dicts with 'pdf_bytes' and 'filename' keys
            folder_id: Optional folder ID for all files
            
        Returns:
            List of upload results
        """
        results = []
        for pdf_file in pdf_files:
            result = await self.upload_pdf(
                pdf_bytes=pdf_file['pdf_bytes'],
                filename=pdf_file['filename'],
                folder_id=folder_id
            )
            results.append(result)
        
        return results
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Successfully deleted file {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {str(e)}", exc_info=True)
            return False
