"""Google Drive v3 client with OAuth Desktop + resumable upload + appProperties."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

from .config import DRIVE_APPDATA_FOLDER, DRIVE_TOKEN, UPLOAD_CHUNK
from .logging_config import get_logger

_log = get_logger("teledrive.drive")

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    _GDRIVE_AVAILABLE = True
except Exception:  # pragma: no cover
    _GDRIVE_AVAILABLE = False
    Credentials = None  # type: ignore

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveService:
    def __init__(self, client_secret_path: str, token_path: str = str(DRIVE_TOKEN)):
        if not _GDRIVE_AVAILABLE:
            raise RuntimeError("google client libraries are not installed")
        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.creds: Optional[Credentials] = None
        self.service = None

    # ---------- Auth ----------

    def _load_creds(self) -> Optional[Credentials]:
        if os.path.exists(self.token_path):
            try:
                return Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception:
                return None
        return None

    def _save_creds(self, creds: Credentials) -> None:
        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            f.write(creds.to_json())
        try:
            os.chmod(self.token_path, 0o600)
        except Exception:
            pass

    def start_auth_flow(self) -> str:
        """Return an auth URL for the user to open. Uses out-of-band flow for Colab."""
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        self._pending_flow = flow
        return auth_url

    def complete_auth_flow(self, code: str) -> bool:
        flow = getattr(self, "_pending_flow", None)
        if flow is None:
            return False
        flow.fetch_token(code=code)
        self.creds = flow.credentials
        self._save_creds(self.creds)
        self._build_service()
        return True

    def try_authenticate_from_token(self) -> bool:
        creds = self._load_creds()
        if creds and creds.valid:
            self.creds = creds
            self._build_service()
            return True
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.creds = creds
                self._save_creds(creds)
                self._build_service()
                return True
            except Exception as e:
                _log.warning("token refresh failed: %s", e)
        return False

    def _build_service(self) -> None:
        self.service = build("drive", "v3", credentials=self.creds, cache_discovery=False)

    def revoke(self) -> None:
        try:
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
        except Exception:
            pass
        self.creds = None
        self.service = None

    # ---------- Metadata ----------

    def about(self) -> dict[str, Any]:
        assert self.service
        return self.service.about().get(fields="storageQuota,user").execute()

    def storage_quota(self) -> dict[str, int]:
        info = self.about().get("storageQuota", {}) or {}
        return {
            "limit": int(info.get("limit", 0) or 0),
            "usage": int(info.get("usage", 0) or 0),
        }

    # ---------- Folders ----------

    def find_folder(self, name: str, parent: str | None = None) -> str | None:
        assert self.service
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent:
            q += f" and '{parent}' in parents"
        r = self.service.files().list(q=q, fields="files(id,name)", pageSize=1).execute()
        files = r.get("files", [])
        return files[0]["id"] if files else None

    def create_folder(self, name: str, parent: str | None = None) -> str:
        assert self.service
        body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent:
            body["parents"] = [parent]
        r = self.service.files().create(body=body, fields="id").execute()
        return r["id"]

    def ensure_folder(self, name: str, parent: str | None = None) -> str:
        return self.find_folder(name, parent) or self.create_folder(name, parent)

    def list_folders(self, parent: str | None = None) -> list[dict[str, Any]]:
        assert self.service
        q = "mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent:
            q += f" and '{parent}' in parents"
        r = self.service.files().list(q=q, fields="files(id,name)", pageSize=200).execute()
        return r.get("files", [])

    # ---------- Duplicate lookup ----------

    def find_by_source_key(self, source_key: str) -> dict[str, Any] | None:
        assert self.service
        q = f"appProperties has {{ key='source_key' and value='{source_key}' }} and trashed=false"
        r = self.service.files().list(
            q=q, fields="files(id,name,size,appProperties)", pageSize=1
        ).execute()
        files = r.get("files", [])
        return files[0] if files else None

    # ---------- Upload ----------

    def upload_resumable(
        self,
        file_path: str,
        drive_name: str,
        parent_id: str,
        source_key: str,
        progress_cb: Callable[[int, int], None] | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        assert self.service
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type or "application/octet-stream",
            chunksize=UPLOAD_CHUNK,
            resumable=True,
        )
        body = {
            "name": drive_name,
            "parents": [parent_id],
            "appProperties": {"source_key": source_key},
        }
        request = self.service.files().create(
            body=body, media_body=media, fields="id,name,size,appProperties"
        )
        response = None
        total = os.path.getsize(file_path) or 1
        while response is None:
            status, response = request.next_chunk()
            if status and progress_cb:
                try:
                    progress_cb(int(status.resumable_progress), total)
                except Exception:
                    pass
        if progress_cb:
            try:
                progress_cb(total, total)
            except Exception:
                pass
        return response

    # ---------- Download small files (checkpoint retrieval) ----------

    def download_bytes(self, file_id: str) -> bytes:
        assert self.service
        req = self.service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()

    def upload_bytes(self, name: str, data: bytes, parent_id: str) -> str:
        assert self.service
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(data, mimetype="application/json", resumable=False)
        body = {"name": name, "parents": [parent_id]}
        r = self.service.files().create(body=body, media_body=media, fields="id").execute()
        return r["id"]

    def list_children(self, parent_id: str) -> list[dict[str, Any]]:
        assert self.service
        r = self.service.files().list(
            q=f"'{parent_id}' in parents and trashed=false",
            fields="files(id,name,size,modifiedTime,appProperties)",
            pageSize=1000,
        ).execute()
        return r.get("files", [])
