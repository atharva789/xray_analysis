import json
import os
from typing import Any, Dict, Iterable, List, Optional

import requests


class ApiClientError(RuntimeError):
    """Raised when the API client encounters an unexpected response."""


class ApiClient:
    """Simple API client used by the PyQt frontend to talk to FastAPI."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
        self._token: Optional[str] = None
        self.user_aid: Optional[int] = None

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate the user and cache the returned JWT token."""

        response = requests.post(
            f"{self.base_url}/api/auth/token",
            data={"username": username, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        token = payload.get("access_token")
        if not token:
            raise ApiClientError("Missing access token in authentication response")
        self._token = token
        return payload

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    def _auth_headers(self) -> Dict[str, str]:
        if not self._token:
            raise ApiClientError("Attempted to call an authenticated endpoint without logging in")
        return {"Authorization": f"Bearer {self._token}"}

    def get_sessions(self) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/user/sessions",
            headers=self._auth_headers(),
            timeout=30,
        )
        response.raise_for_status()
        sessions: List[Dict[str, Any]] = response.json()
        if sessions and not self.user_aid:
            self.user_aid = sessions[0].get("aid")
        return sessions

    def get_session(self, session_id: int, aid: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        resolved_aid = aid or self.user_aid
        if resolved_aid is not None:
            params["aid"] = resolved_aid
        response = requests.get(
            f"{self.base_url}/user/get-session/{session_id}",
            headers=self._auth_headers(),
            params=params or None,
            timeout=60,
        )
        response.raise_for_status()
        accession: Dict[str, Any] = response.json()
        if accession and not self.user_aid:
            self.user_aid = accession.get("aid")
        return accession

    def get_session_with_files(self, session_id: int, aid: Optional[int] = None) -> Dict[str, Any]:
        accession = self.get_session(session_id, aid=aid)
        files: List[Dict[str, Any]] = []
        for file_info in accession.get("files", []):
            url = file_info.get("s3_url")
            if not url:
                files.append(file_info)
                continue
            content = self.download_file(url)
            files.append({**file_info, "content": content})
        accession["files"] = files
        return accession

    def download_file(self, url: str) -> bytes:
        response = requests.get(url, headers=self._auth_headers(), timeout=120)
        response.raise_for_status()
        return response.content

    def download_session_to_directory(self, session_id: int, destination: str, aid: Optional[int] = None) -> List[str]:
        accession = self.get_session_with_files(session_id, aid=aid)
        saved_files: List[str] = []
        for file_info in accession.get("files", []):
            content: Optional[bytes] = file_info.get("content")
            if not content:
                continue
            object_key = file_info.get("object_key") or f"file_{len(saved_files)}"
            filename = os.path.basename(object_key.strip("/")) or f"file_{len(saved_files)}"
            path = os.path.join(destination, filename)
            with open(path, "wb") as handle:
                handle.write(content)
            saved_files.append(path)
        return saved_files

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------
    def upload_accession(
        self,
        aid: int,
        dicom_name: str,
        file_paths: Iterable[str],
        agaston_score: int | None = None,
    ) -> Dict[str, Any]:
        file_paths = list(file_paths)

        accession_payload: Dict[str, Any] = {
            "aid": aid,
            "dicom_name": dicom_name,
            "agaston_score": agaston_score or 0,
            "files": [{"type": "slice"} for _ in file_paths],
        }

        files_data = []
        for path in file_paths:
            filename = os.path.basename(path)
            files_data.append((
                "files",
                (filename, open(path, "rb"), "application/octet-stream"),
            ))

        try:
            response = requests.post(
                f"{self.base_url}/user/new_accession",
                headers=self._auth_headers(),
                data={"accession": json.dumps(accession_payload)},
                files=files_data,
                timeout=120,
            )
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
            return payload
        finally:
            for _, file_tuple in files_data:
                file_tuple[1].close()

    # Convenience ----------------------------------------------------------------
    def ensure_user_aid(self) -> int:
        if self.user_aid is not None:
            return self.user_aid
        sessions = self.get_sessions()
        if sessions:
            self.user_aid = sessions[0].get("aid")
            if self.user_aid is not None:
                return self.user_aid
        raise ApiClientError("Unable to determine the current user's AID")
