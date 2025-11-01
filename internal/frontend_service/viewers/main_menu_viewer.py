from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pydicom
import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.api_client import ApiClient, ApiClientError
from viewers.full_stack_viewer import FullStackViewer
from viewers.mask_overlay_viewer import MaskOverlayViewer
from viewers.mask_side_by_side_viewer import MaskSideBySideViewer
from viewers.single_slice_viewer import SingleSliceViewer


class MainMenu(QWidget):
    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api_client = api_client
        self.sessions: Dict[int, Dict[str, Any]] = {}

        self.setWindowTitle("CT DICOM Viewer - Main Menu")
        self.setMinimumSize(520, 480)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Available sessions"))

        self.session_list = QListWidget()
        self.session_list.itemSelectionChanged.connect(self._update_button_states)
        layout.addWidget(self.session_list)

        viewer_buttons = QHBoxLayout()
        self.single_btn = QPushButton("Single Slice Viewer")
        self.single_btn.clicked.connect(self.launch_single)
        viewer_buttons.addWidget(self.single_btn)

        self.full_btn = QPushButton("Full Stack Viewer")
        self.full_btn.clicked.connect(self.launch_full)
        viewer_buttons.addWidget(self.full_btn)
        layout.addLayout(viewer_buttons)

        mask_buttons = QHBoxLayout()
        self.side_btn = QPushButton("Side-by-Side Viewer")
        self.side_btn.clicked.connect(self.launch_side_by_side)
        mask_buttons.addWidget(self.side_btn)

        self.overlay_btn = QPushButton("Overlay Viewer")
        self.overlay_btn.clicked.connect(self.launch_overlay)
        mask_buttons.addWidget(self.overlay_btn)
        layout.addLayout(mask_buttons)

        action_buttons = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_sessions)
        action_buttons.addWidget(refresh_btn)

        download_btn = QPushButton("Download Session")
        download_btn.clicked.connect(self.download_session)
        action_buttons.addWidget(download_btn)

        upload_btn = QPushButton("Upload New Accession")
        upload_btn.clicked.connect(self.upload_accession)
        action_buttons.addWidget(upload_btn)
        layout.addLayout(action_buttons)

        self.setLayout(layout)
        self._update_button_states()
        self.load_sessions()

    # ------------------------------------------------------------------
    def _update_button_states(self) -> None:
        has_selection = bool(self.session_list.selectedItems())
        for button in (self.single_btn, self.full_btn, self.side_btn, self.overlay_btn):
            button.setEnabled(has_selection)

    def load_sessions(self) -> None:
        try:
            sessions = self.api_client.get_sessions()
        except (requests.RequestException, ApiClientError) as exc:
            QMessageBox.critical(self, "Error", f"Failed to load sessions: {exc}")
            return

        self.session_list.clear()
        self.sessions.clear()
        for session in sessions:
            dicom_id = session.get("dicom_id")
            if dicom_id is None:
                continue
            created_at = session.get("created_at", "")
            dicom_name = session.get("dicom_name", "Unnamed Study")
            label = f"{dicom_name} (ID: {dicom_id})"
            if created_at:
                label = f"{label}\n{created_at}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, dicom_id)
            self.session_list.addItem(item)
            self.sessions[dicom_id] = session

        self._update_button_states()

    def _selected_session_id(self) -> Optional[int]:
        items = self.session_list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    def _fetch_accession(self) -> Optional[Dict[str, Any]]:
        session_id = self._selected_session_id()
        if session_id is None:
            QMessageBox.information(self, "No selection", "Please select a session first.")
            return None
        try:
            accession = self.api_client.get_session_with_files(session_id)
        except requests.HTTPError as exc:
            QMessageBox.critical(self, "Error", f"API error: {exc.response.text}")
            return None
        except (requests.RequestException, ApiClientError) as exc:
            QMessageBox.critical(self, "Error", f"Failed to fetch session: {exc}")
            return None
        return accession

    def _partition_files(self, accession: Dict[str, Any]) -> Tuple[List[pydicom.dataset.Dataset], List[np.ndarray]]:
        dicom_slices: List[pydicom.dataset.Dataset] = []
        mask_images: List[np.ndarray] = []

        for file_info in accession.get("files", []):
            content = file_info.get("content")
            if not content:
                continue
            file_type = file_info.get("type", "slice")
            buffer = BytesIO(content)
            try:
                dataset = pydicom.dcmread(buffer, force=True)
                if file_type == "mask":
                    mask_images.append(dataset.pixel_array.astype(np.uint8))
                else:
                    dicom_slices.append(dataset)
                continue
            except Exception:
                buffer.seek(0)

            if file_type == "mask":
                array = cv2.imdecode(np.frombuffer(buffer.read(), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if array is not None:
                    mask_images.append(array)

        if dicom_slices:
            dicom_slices.sort(key=lambda ds: int(getattr(ds, "InstanceNumber", 0)))
        return dicom_slices, mask_images

    # ------------------------------------------------------------------
    def launch_single(self) -> None:
        accession = self._fetch_accession()
        if not accession:
            return
        dicom_slices, _ = self._partition_files(accession)
        if not dicom_slices:
            QMessageBox.information(self, "No slices", "The selected session has no slice images to display.")
            return
        viewer = SingleSliceViewer(accession=accession, dicom_slices=dicom_slices)
        viewer.show()

    def launch_full(self) -> None:
        accession = self._fetch_accession()
        if not accession:
            return
        dicom_slices, _ = self._partition_files(accession)
        if not dicom_slices:
            QMessageBox.information(self, "No slices", "The selected session has no slice images to display.")
            return
        viewer = FullStackViewer(dicom_slices=dicom_slices)
        viewer.show()

    def launch_side_by_side(self) -> None:
        accession = self._fetch_accession()
        if not accession:
            return
        dicom_slices, masks = self._partition_files(accession)
        if not dicom_slices or not masks:
            QMessageBox.information(self, "Incomplete data", "Side-by-side view requires both slices and masks.")
            return
        viewer = MaskSideBySideViewer(dicom_slices=dicom_slices, mask_images=masks, mode="rgb")
        viewer.show()

    def launch_overlay(self) -> None:
        accession = self._fetch_accession()
        if not accession:
            return
        dicom_slices, masks = self._partition_files(accession)
        if not dicom_slices or not masks:
            QMessageBox.information(self, "Incomplete data", "Overlay view requires both slices and masks.")
            return
        viewer = MaskOverlayViewer(dicom_slices=dicom_slices, mask_images=masks)
        viewer.show()

    # ------------------------------------------------------------------
    def download_session(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            QMessageBox.information(self, "No selection", "Please select a session to download.")
            return
        destination = QFileDialog.getExistingDirectory(self, "Select download directory")
        if not destination:
            return
        try:
            saved_files = self.api_client.download_session_to_directory(session_id, destination)
        except (requests.RequestException, ApiClientError) as exc:
            QMessageBox.critical(self, "Download failed", f"Unable to download session: {exc}")
            return
        QMessageBox.information(
            self,
            "Download complete",
            f"Saved {len(saved_files)} files to {destination}",
        )

    def upload_accession(self) -> None:
        aid = self.api_client.user_aid
        if aid is None:
            aid, ok = QInputDialog.getInt(self, "Patient ID", "Enter the patient AID:")
            if not ok:
                return
        dicom_name, ok = QInputDialog.getText(self, "Accession Name", "Enter a name for the study:")
        if not ok or not dicom_name:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select DICOM files", filter="DICOM Files (*.dcm);;All Files (*)")
        if not files:
            return
        try:
            self.api_client.upload_accession(aid, dicom_name, files)
        except requests.HTTPError as exc:
            QMessageBox.critical(self, "Upload failed", f"API error: {exc.response.text}")
            return
        except (requests.RequestException, ApiClientError) as exc:
            QMessageBox.critical(self, "Upload failed", f"Unable to upload accession: {exc}")
            return
        QMessageBox.information(self, "Upload complete", "Accession uploaded successfully.")
        self.load_sessions()
