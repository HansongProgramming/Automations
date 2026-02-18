"""
Google Drive file upload utility.
Uses requests-based transport to avoid httplib2 timeout issues.
Creates per-client folder structure: ClientName / PDF | HTML | LOC
"""

import logging
import io
from typing import Optional
import google.auth.transport.requests
from google.oauth2 import service_account
import requests as req_lib

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
DRIVE_API = 'https://www.googleapis.com/drive/v3'
DRIVE_UPLOAD_API = 'https://www.googleapis.com/upload/drive/v3'


class GoogleDriveUploader:
    """
    Handle uploads to Google Drive with per-client folder structure.

    Folder layout created automatically:
        <root_folder>/
            <Client Name>/
                PDF/
                HTML/
                LOC/

    Uses requests transport instead of httplib2 to avoid Windows timeout issues.
    All methods are async-compatible (blocking calls run fine inside FastAPI
    with run_in_executor if you need true non-blocking — but for simplicity
    they are sync internally and awaited at the call site via async wrappers).
    """

    def __init__(self, credentials_path: str, folder_id: Optional[str] = None):
        self.credentials_path = credentials_path
        self.root_folder_id = folder_id
        self._creds = None
        self._session = None
        self._folder_cache: dict[str, str] = {}  # "parent_id/name" -> folder_id
        self._initialize()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialize(self):
        self._creds = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=SCOPES
        )
        self._refresh_token()
        logger.info("Google Drive uploader initialised (requests transport)")

    def _refresh_token(self):
        auth_request = google.auth.transport.requests.Request()
        self._creds.refresh(auth_request)

    def _headers(self) -> dict:
        """Return auth headers, refreshing token if expired."""
        if not self._creds.valid:
            self._refresh_token()
        return {'Authorization': f'Bearer {self._creds.token}'}

    # ------------------------------------------------------------------
    # Folder helpers
    # ------------------------------------------------------------------

    def _get_or_create_folder(self, name: str, parent_id: str) -> str:
        """
        Return the Drive folder ID for `name` inside `parent_id`.
        Creates it if it doesn't exist. Results are cached in-process.
        """
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        # Search for existing folder
        query = (
            f"name='{name}' "
            f"and '{parent_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )
        resp = req_lib.get(
            f"{DRIVE_API}/files",
            headers=self._headers(),
            params={'q': query, 'fields': 'files(id,name)', 'spaces': 'drive'}
        )
        resp.raise_for_status()
        files = resp.json().get('files', [])

        if files:
            folder_id = files[0]['id']
            logger.info(f"Found existing folder '{name}': {folder_id}")
        else:
            # Create it
            meta = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            create_resp = req_lib.post(
                f"{DRIVE_API}/files",
                headers=self._headers(),
                json=meta,
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

        Returns:
            {
                'client': <folder_id>,
                'PDF':    <folder_id>,
                'HTML':   <folder_id>,
                'LOC':    <folder_id>,
            }
        """
        if not self.root_folder_id:
            raise ValueError("root_folder_id is required to create client folders")

        # Sanitise client name for Drive (strip weird chars)
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
        """
        Upload a single file using the Drive multipart upload API.
        Builds the multipart body manually to avoid requests_toolbelt issues.
        """
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
            logger.error(f"Upload API error {upload_resp.status_code}: {upload_resp.text}")
        upload_resp.raise_for_status()
        return upload_resp.json()

    def _set_public_readable(self, file_id: str):
        """Make a file publicly readable (anyone with link)."""
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
        file_type: str,          # 'PDF', 'HTML', or 'LOC'
        mime_type: str = 'application/octet-stream'
    ) -> dict:
        """
        Upload a file into the correct client subfolder.

        Args:
            file_bytes:   Raw file content
            filename:     Filename to use in Drive
            client_name:  Client's name (used as folder name)
            file_type:    'PDF', 'HTML', or 'LOC'
            mime_type:    MIME type for the file

        Returns:
            {
                success: bool,
                file_id: str,
                web_view_link: str,
                web_content_link: str,
                filename: str,
                folder_path: str,   e.g. "JOHN DOE/PDF"
                error: str          only if success=False
            }
        """
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
        """
        Legacy single-file upload for backwards compatibility with
        /batch-process-csv and any external API callers that POST directly.

        If folder_id is supplied it uploads there; otherwise uses root folder.
        Returns same shape as before so existing callers aren't broken.
        """
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

    async def upload_client_files(self, files: list[dict]) -> list[dict]:
        """
        Upload a batch of files, each into the correct client subfolder.

        Each item in `files` should have:
            {
                file_bytes:  bytes,
                filename:    str,
                client_name: str,
                file_type:   'PDF' | 'HTML' | 'LOC',
                mime_type:   str  (optional)
            }

        Returns list of upload result dicts.
        """
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