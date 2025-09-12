# viewers/mask_overlay_viewer.py

import os
import cv2
import numpy as np
import pydicom
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage

from utils.dicom_loader import load_dicom_slices
from utils.image_utils import get_qimage

class MaskOverlayViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Overlay Mask Viewer")
        self.dicom_slices = []
        self.mask_images = []
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

        self.load_folders()
        self.resize(800, 800)
        self.show()

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

        self.slider.setMaximum(len(self.dicom_slices) - 1)
        self.slider.setValue(0)
        self.update_image(0)

    def load_mask_images(self, folder_path):
        dicom_map = {
            int(getattr(ds, "InstanceNumber", i)): i
            for i, ds in enumerate(self.dicom_slices)
        }

        mask_images = [None] * len(self.dicom_slices)

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
            except:
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

        # Overlay red where mask is 1
        overlay = base_rgb.copy()
        overlay[mask > 0] = [255, 0, 0]  # Red overlay

        blended = cv2.addWeighted(base_rgb, 0.7, overlay, 0.3, 0)

        h, w, _ = blended.shape
        qimg = QImage(blended.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            self.timer.start()
            self.play_button.setText("Pause")

    def next_slice(self):
        idx = self.current_index + 1
        if idx >= len(self.dicom_slices):
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            self.slider.setValue(idx)