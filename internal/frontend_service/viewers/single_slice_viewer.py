from typing import List, Optional

import pydicom
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.image_utils import get_qimage


class SingleSliceViewer(QWidget):
    def __init__(
        self,
        accession: Optional[dict] = None,
        dicom_slices: Optional[List[pydicom.dataset.Dataset]] = None,
    ):
        super().__init__()
        self.setWindowTitle("Single Slice Viewer")

        self.accession = accession or {}
        self.dicom_slices: List[pydicom.dataset.Dataset] = dicom_slices or []
        self.current_index = 0

        layout = QVBoxLayout()

        self.label = QLabel("No image loaded")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        controls = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(lambda: self._change_slice(-1))
        controls.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(lambda: self._change_slice(1))
        controls.addWidget(self.next_button)

        self.load_button = QPushButton("Load Local File")
        self.load_button.clicked.connect(self.load_local_slice)
        controls.addWidget(self.load_button)

        layout.addLayout(controls)

        self.setLayout(layout)

        if self.dicom_slices:
            self._display_slice(0)
        else:
            self._update_controls()

    # ------------------------------------------------------------------
    def _change_slice(self, delta: int) -> None:
        if not self.dicom_slices:
            return
        new_index = self.current_index + delta
        if 0 <= new_index < len(self.dicom_slices):
            self._display_slice(new_index)

    def _display_slice(self, index: int) -> None:
        self.current_index = index
        dataset = self.dicom_slices[index]
        qimg = get_qimage(dataset)
        pixmap = QPixmap.fromImage(qimg).scaled(
            700,
            700,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.label.setPixmap(pixmap)
        description = dataset.SeriesDescription if hasattr(dataset, "SeriesDescription") else ""
        title_suffix = f" - {description}" if description else ""
        if self.accession:
            dicom_name = self.accession.get("dicom_name")
            if dicom_name:
                title_suffix = f" - {dicom_name}{title_suffix}"
        self.setWindowTitle(f"Single Slice Viewer (Slice {index + 1}/{len(self.dicom_slices)}){title_suffix}")
        self._update_controls()

    def _update_controls(self) -> None:
        has_slices = bool(self.dicom_slices)
        self.prev_button.setEnabled(has_slices and self.current_index > 0)
        self.next_button.setEnabled(has_slices and self.current_index < len(self.dicom_slices) - 1)

    # ------------------------------------------------------------------
    def load_local_slice(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select DICOM File", "", "DICOM Files (*.dcm);;All Files (*)")
        if not file_path:
            return
        try:
            dataset = pydicom.dcmread(file_path, force=True)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{exc}")
            return
        self.dicom_slices = [dataset]
        self._display_slice(0)
