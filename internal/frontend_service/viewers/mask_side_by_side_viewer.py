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
from utils.image_utils import get_qimage


class MaskSideBySideViewer(QWidget):
    def __init__(
        self,
        mode: str = "grayscale",
        dicom_slices: Optional[List[pydicom.dataset.Dataset]] = None,
        mask_images: Optional[List[np.ndarray]] = None,
    ):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(f"Side-by-Side Mask Viewer ({mode.upper()})")
        self.dicom_slices = dicom_slices or []
        self.mask_images = mask_images or []
        self.current_index = 0

        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.next_slice)

        # Widgets
        self.slice_label = QLabel("Slice")
        self.slice_label.setAlignment(Qt.AlignCenter)

        self.mask_label = QLabel("Mask")
        self.mask_label.setAlignment(Qt.AlignCenter)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.update_images)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)

        self.switch_button = QPushButton("Switch Folder")
        self.switch_button.clicked.connect(self.load_folders)

        # Layouts
        img_layout = QHBoxLayout()
        img_layout.addWidget(self.slice_label)
        img_layout.addWidget(self.mask_label)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.slider)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.switch_button)

        layout = QVBoxLayout()
        layout.addLayout(img_layout)
        layout.addLayout(control_layout)
        self.setLayout(layout)

        if self.dicom_slices and self.mask_images:
            self._configure_slider()
            self.update_images(0)
        else:
            self.load_folders()

        self.resize(1400, 700)
        self.show()

    def _configure_slider(self):
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
        self.update_images(0)

    def load_mask_images(self, folder_path):
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

    def update_images(self, index):
        if index >= len(self.dicom_slices) or index >= len(self.mask_images):
            return

        self.current_index = index
        dcm = self.dicom_slices[index]
        mask_img = self.mask_images[index]

        # CT Slice to QPixmap
        qimg = get_qimage(dcm)
        pixmap = QPixmap.fromImage(qimg).scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.slice_label.setPixmap(pixmap)

        # Mask to QPixmap based on mode
        height, width = mask_img.shape[:2]

        if self.mode == "grayscale":
            if len(mask_img.shape) == 3:  # Convert RGB to grayscale if needed
                mask_img = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
            mask_qimg = QImage(mask_img.data, width, height, width, QImage.Format_Grayscale8)
        else:  # RGB
            if len(mask_img.shape) == 2:  # Convert grayscale to RGB
                mask_img = cv2.cvtColor(mask_img, cv2.COLOR_GRAY2RGB)
            mask_qimg = QImage(mask_img.data, width, height, width * 3, QImage.Format_RGB888)

        mask_pixmap = QPixmap.fromImage(mask_qimg).scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.mask_label.setPixmap(mask_pixmap)

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
