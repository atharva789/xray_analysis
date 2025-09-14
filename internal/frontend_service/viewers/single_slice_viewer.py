from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap
from utils.image_utils import get_qimage
import pydicom
from PyQt5.QtCore import Qt

class SingleSliceViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Single Slice Viewer")
        layout = QVBoxLayout()
        self.label = QLabel("No image loaded")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.show_slice()

    def show_slice(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select DICOM File", "", "All Files (*)")
        if not file:
            return
        try:
            dcm = pydicom.dcmread(file, force=True)
            img = get_qimage(dcm)
            pixmap = QPixmap.fromImage(img).scaled(700, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(pixmap)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
