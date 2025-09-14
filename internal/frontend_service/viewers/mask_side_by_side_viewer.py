# viewers/mask_side_by_side_viewer.py

import os
import cv2
import pydicom
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage

from utils.dicom_loader import load_dicom_slices
from utils.image_utils import get_qimage


class MaskSideBySideViewer(QWidget):
    def __init__(self, mode="grayscale"):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(f"Side-by-Side Mask Viewer ({mode.upper()})")
        self.dicom_slices = []
        self.mask_images = []
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

        self.load_folders()
        self.resize(1400, 700)
        self.show()

    def load_folders(self):
        # fetch dicoms, masks from db on app startup (async)
        
        ct_folder = QFileDialog.getExistingDirectory(self, "Select DICOM Slice Folder")
        if not ct_folder:
            return
        mask_folder = QFileDialog.getExistingDirectory(self, "Select Mask Folder")
        if not mask_folder:
            return

        self.dicom_slices = load_dicom_slices(ct_folder)
        self.mask_images = self.load_mask_images(mask_folder)

        print(f"DICOM slices loaded: {len(self.dicom_slices)}")
        print(f"Mask images loaded: {len(self.mask_images)}")

        if len(self.dicom_slices) != len(self.mask_images):
            QMessageBox.critical(self, "Mismatch", "DICOM and mask counts do not match.")
            return
        
        # send to DB
        self.slider.setMaximum(len(self.dicom_slices) - 1)
        self.slider.setValue(0)
        self.update_images(0)


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
                    print(f"Skipping {fname}: not int or hex")
                    continue

            idx = dicom_map.get(instance)
            if idx is None:
                print(f"No matching slice for mask {fname} (Instance: {instance})")
                continue

            file_path = os.path.join(folder_path, fname)
            try:
                dcm = pydicom.dcmread(file_path)
                img = dcm.pixel_array.astype(np.uint8)
                mask_images[idx] = img
                print(f"Loaded DICOM mask {fname} → slice {idx}")
            except Exception as e:
                print(f"Error reading {fname}: {e}")

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