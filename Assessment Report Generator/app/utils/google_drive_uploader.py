"""
Google Drive file upload utility.
Uses OAuth credentials (personal Gmail compatible) instead of service account.
Creates per-client folder structure: ClientName / PDF | HTML | LOC
"""

import logging
import io
import os
import pickle
from typing import Optional
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import requests as req_lib

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
DRIVE_API = 'https://www.googleapis.com/drive/v3'
DRIVE_UPLOAD_API = 'https://www.googleapis.com/upload/drive/v3'


class GoogleDriveUploader:
    """
    Handle uploads to Google Drive with per-client folder structure.
    Uses OAuth user credentials — works with personal Gmail accounts.

    Folder layout created automatically:
        <root_folder>/
            <Client Name>/
                PDF/
                HTML/
                LOC/
    """

    def __init__(
        self,
        credentials_path: str,          # path to oauth-client.json (for re-auth if needed)
        folder_id: Optional[str] = None,
        token_path: str = 'credentials/oauth-token.pkl'
    ):
        self.credentials_path = credentials_path
        self.root_folder_id = folder_id
        self.token_path = token_path
        self._creds: Optional[Credentials] = None
        self._folder_cache: dict = {}
        self._initialize()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _initialize(self):
        """Load OAuth token from disk, refresh if expired, re-auth if missing."""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as f:
                self._creds = pickle.load(f)
            logger.info("Loaded OAuth token from disk")

        # Refresh if expired
        if self._creds and self._creds.expired and self._creds.refresh_token:
            try:
                self._creds.refresh(google.auth.transport.requests.Request())
                self._save_token()
                logger.info("OAuth token refreshed")
            except Exception as e:
                logger.warning(f"Token refresh failed ({e}), forcing re-auth")
                self._creds = None
        if not self._creds or not self._creds.valid:
            # Need to re-authenticate — this opens a browser
            logger.warning("OAuth token missing or invalid — starting re-auth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            self._creds = flow.run_local_server(port=0)
            self._save_token()
            logger.info("OAuth re-authentication complete")

        logger.info("Google Drive uploader initialised (OAuth transport)")

    def _save_token(self):
        with open(self.token_path, 'wb') as f:
            pickle.dump(self._creds, f)

    def _headers(self) -> dict:
        """Return auth headers, refreshing token if expired."""
        if self._creds.expired and self._creds.refresh_token:
            self._creds.refresh(google.auth.transport.requests.Request())
            self._save_token()
        return {'Authorization': f'Bearer {self._creds.token}'}

    # ------------------------------------------------------------------
    # Folder helpers
    # ------------------------------------------------------------------

    def _get_or_create_folder(self, name: str, parent_id: str) -> str:
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        escaped_name = name.replace("'", "\\'")
        query = (
            f"name='{escaped_name}' "
            f"and '{parent_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )
        resp = req_lib.get(
            f"{DRIVE_API}/files",
            headers=self._headers(),
            params={'q': query, 'fields': 'files(id,name)'}
        )
        resp.raise_for_status()
        files = resp.json().get('files', [])

        if files:
            folder_id = files[0]['id']
            logger.info(f"Found existing folder '{name}': {folder_id}")
        else:
            create_resp = req_lib.post(
                f"{DRIVE_API}/files",
                headers=self._headers(),
                json={
                    'name': name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                },
                params={'fields': 'id'}
            )
            create_resp.raise_for_status()
            folder_id = create_resp.json()['id']
            logger.info(f"Created folder '{name}': {folder_id}")

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def get_client_subfolders(self, client_name: str) -> dict:
        """
        Ensure the full folder tree exists for a client and return IDs.

        Structure:
            root_folder / client_name / PDF
                                      / HTML
                                      / LOC
        """
        if not self.root_folder_id:
            raise ValueError("root_folder_id is required to create client folders")

        safe_name = client_name.strip().replace('/', '_').replace('\\', '_')
        client_id = self._get_or_create_folder(safe_name, self.root_folder_id)
        pdf_id    = self._get_or_create_folder('PDF',  client_id)
        html_id   = self._get_or_create_folder('HTML', client_id)
        loc_id    = self._get_or_create_folder('LOC',  client_id)

        return {
            'client': client_id,
            'PDF':    pdf_id,
            'HTML':   html_id,
            'LOC':    loc_id,
        }

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------

    def _upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        parent_folder_id: str
    ) -> dict:
        """Upload using Drive multipart API with raw bytes body."""
        import json

        meta = json.dumps({
            'name': filename,
            'parents': [parent_folder_id]
        }).encode('utf-8')

        boundary = 'DRIVE_UPLOAD_BOUNDARY_xK3mP9'
        body = (
            f'--{boundary}\r\n'
            f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
        ).encode() + meta + (
            f'\r\n--{boundary}\r\n'
            f'Content-Type: {mime_type}\r\n\r\n'
        ).encode() + file_bytes + f'\r\n--{boundary}--'.encode()

        headers = {
            **self._headers(),
            'Content-Type': f'multipart/related; boundary={boundary}',
            'Content-Length': str(len(body)),
        }

        upload_resp = req_lib.post(
            f"{DRIVE_UPLOAD_API}/files",
            headers=headers,
            params={'uploadType': 'multipart', 'fields': 'id,webViewLink,webContentLink,name'},
            data=body
        )

        if not upload_resp.ok:
            logger.error(f"Upload API error {upload_resp.status_code}: {upload_resp.text[:500]}")
        upload_resp.raise_for_status()
        return upload_resp.json()

    def _set_public_readable(self, file_id: str):
        resp = req_lib.post(
            f"{DRIVE_API}/files/{file_id}/permissions",
            headers=self._headers(),
            json={'type': 'anyone', 'role': 'reader'}
        )
        if not resp.ok:
            logger.warning(f"Could not set public permission on {file_id}: {resp.text}")

    # ------------------------------------------------------------------
    # Public upload methods
    # ------------------------------------------------------------------

    async def upload_file_to_client_folder(
        self,
        file_bytes: bytes,
        filename: str,
        client_name: str,
        file_type: str,
        mime_type: str = 'application/octet-stream'
    ) -> dict:
        try:
            folders = self.get_client_subfolders(client_name)
            target_folder_id = folders.get(file_type)
            if not target_folder_id:
                raise ValueError(f"Unknown file_type '{file_type}'. Use PDF, HTML, or LOC.")

            file_meta = self._upload_file(file_bytes, filename, mime_type, target_folder_id)
            self._set_public_readable(file_meta['id'])

            folder_path = f"{client_name.strip()}/{file_type}"
            logger.info(f"Uploaded '{filename}' → {folder_path} (id={file_meta['id']})")

            return {
                'success': True,
                'file_id': file_meta['id'],
                'web_view_link': file_meta.get('webViewLink', ''),
                'web_content_link': file_meta.get('webContentLink', ''),
                'filename': filename,
                'folder_path': folder_path,
                'client_name': client_name,
                'file_type': file_type,
            }

        except Exception as e:
            logger.error(f"Upload failed for '{filename}': {e}", exc_info=True)
            return {
                'success': False,
                'filename': filename,
                'client_name': client_name,
                'file_type': file_type,
                'error': str(e)
            }

    async def upload_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        folder_id: Optional[str] = None
    ) -> dict:
        """Legacy single-file upload — keeps backwards compatibility."""
        try:
            target = folder_id or self.root_folder_id
            if not target:
                raise ValueError("No folder_id supplied and no root_folder_id configured")

            file_meta = self._upload_file(pdf_bytes, filename, 'application/pdf', target)
            self._set_public_readable(file_meta['id'])

            return {
                'success': True,
                'file_id': file_meta['id'],
                'web_view_link': file_meta.get('webViewLink', ''),
                'web_content_link': file_meta.get('webContentLink', ''),
                'filename': filename,
            }
        except Exception as e:
            logger.error(f"Legacy upload failed for '{filename}': {e}", exc_info=True)
            return {'success': False, 'filename': filename, 'error': str(e)}

    async def upload_client_files(self, files: list) -> list:
        MIME_MAP = {
            'PDF':  'application/pdf',
            'HTML': 'text/html',
            'LOC':  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        results = []
        for f in files:
            mime = f.get('mime_type') or MIME_MAP.get(f['file_type'], 'application/octet-stream')
            result = await self.upload_file_to_client_folder(
                file_bytes=f['file_bytes'],
                filename=f['filename'],
                client_name=f['client_name'],
                file_type=f['file_type'],
                mime_type=mime
            )
            results.append(result)
        return results

    def delete_file(self, file_id: str) -> bool:
        try:
            resp = req_lib.delete(
                f"{DRIVE_API}/files/{file_id}",
                headers=self._headers()
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Delete failed for {file_id}: {e}")
            return False