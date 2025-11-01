import os
from typing import List, Optional

import cv2
import numpy as np
import pydicom
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from utils.dicom_loader import load_dicom_slices


class MaskOverlayViewer(QWidget):
    def __init__(
        self,
        dicom_slices: Optional[List[pydicom.dataset.Dataset]] = None,
        mask_images: Optional[List[np.ndarray]] = None,
    ):
        super().__init__()
        self.setWindowTitle("Overlay Mask Viewer")
        self.dicom_slices = dicom_slices or []
        self.mask_images = mask_images or []
        self.current_index = 0

        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.next_slice)

        # UI
        self.image_label = QLabel("Overlay")
        self.image_label.setAlignment(Qt.AlignCenter)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.update_image)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)

        self.switch_button = QPushButton("Switch Folder")
        self.switch_button.clicked.connect(self.load_folders)

        # Layouts
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.switch_button)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addLayout(control_layout)
        self.setLayout(layout)

        if self.dicom_slices and self.mask_images:
            self._configure_slider()
            self.update_image(0)
        else:
            self.load_folders()

        self.resize(800, 800)
        self.show()

    def _configure_slider(self) -> None:
        if not self.dicom_slices or not self.mask_images:
            return
        length = min(len(self.dicom_slices), len(self.mask_images))
        self.slider.setMaximum(length - 1)
        self.slider.setValue(0)

    def load_folders(self):
        ct_folder = QFileDialog.getExistingDirectory(self, "Select DICOM Slice Folder")
        if not ct_folder:
            return
        mask_folder = QFileDialog.getExistingDirectory(self, "Select Mask Folder")
        if not mask_folder:
            return

        self.dicom_slices = load_dicom_slices(ct_folder)
        self.mask_images = self.load_mask_images(mask_folder)

        if len(self.dicom_slices) != len(self.mask_images):
            QMessageBox.critical(self, "Mismatch", "DICOM and mask counts do not match.")
            return

        self._configure_slider()
        self.update_image(0)

    def load_mask_images(self, folder_path: str) -> List[np.ndarray]:
        dicom_map = {
            int(getattr(ds, "InstanceNumber", i)): i
            for i, ds in enumerate(self.dicom_slices)
        }

        mask_images: List[np.ndarray] = [None] * len(self.dicom_slices)  # type: ignore

        for fname in os.listdir(folder_path):
            if fname.startswith('.'):
                continue

            base = os.path.basename(fname)
            try:
                instance = int(base)
            except ValueError:
                try:
                    instance = int(base, 16)
                except ValueError:
                    continue

            idx = dicom_map.get(instance)
            if idx is None:
                continue

            file_path = os.path.join(folder_path, fname)
            try:
                dcm = pydicom.dcmread(file_path)
                img = dcm.pixel_array.astype(np.uint8)
                mask_images[idx] = img
            except Exception:
                try:
                    raw = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
                    if raw is not None:
                        mask_images[idx] = raw
                except Exception:
                    continue

        return [img for img in mask_images if img is not None]

    def update_image(self, index):
        if index >= len(self.dicom_slices) or index >= len(self.mask_images):
            return

        self.current_index = index
        dcm = self.dicom_slices[index]
        mask = self.mask_images[index]

        base_img = dcm.pixel_array
        base_img_norm = cv2.normalize(base_img, None, 0, 255, cv2.NORM_MINMAX)
        base_rgb = cv2.cvtColor(base_img_norm.astype(np.uint8), cv2.COLOR_GRAY2RGB)

        overlay = base_rgb.copy()
        overlay[mask > 0] = [255, 0, 0]  # Red overlay

        blended = cv2.addWeighted(base_rgb, 0.7, overlay, 0.3, 0)

        h, w, _ = blended.shape
        qimg = QImage(blended.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)

    def toggle_play(self):
        if not self.dicom_slices or not self.mask_images:
            return
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            self.timer.start()
            self.play_button.setText("Pause")

    def next_slice(self):
        if not self.dicom_slices or not self.mask_images:
            return
        idx = self.current_index + 1
        if idx >= len(self.dicom_slices):
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            self.slider.setValue(idx)
