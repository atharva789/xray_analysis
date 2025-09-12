from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSlider, QPushButton, QFileDialog, QMessageBox, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from utils.dicom_loader import load_dicom_slices
from utils.image_utils import get_qimage

class FullStackViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Full Stack Viewer")
        self.dicom_slices = []
        self.current_index = 0
        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.next_slice)
        self.scroll_accumulator = 0

        self.label = QLabel()
        self.label.setMouseTracking(True)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.update_image)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)

        self.switch_button = QPushButton("Switch Folder")
        self.switch_button.clicked.connect(self.load_folder)

        buttons = QHBoxLayout()
        buttons.addWidget(self.slider)
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.switch_button)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.label.mouseMoveEvent = self.mouse_moved
        self.label.wheelEvent = self.handle_scroll

        self.load_folder()
        self.resize(700, 700)
        self.show()

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DICOM Folder")
        if not folder:
            return
        slices = load_dicom_slices(folder)
        if not slices:
            QMessageBox.critical(self, "Error", "No valid DICOM files found.")
            return
        self.dicom_slices = slices
        self.slider.setMaximum(len(slices) - 1)
        self.slider.setValue(0)
        self.update_image(0)

    def update_image(self, index):
        self.current_index = index
        dcm = self.dicom_slices[index]
        self.img_array = dcm.pixel_array
        self.pixel_spacing = getattr(dcm, "PixelSpacing", [1.0, 1.0])
        self.slope = float(getattr(dcm, "RescaleSlope", 1))
        self.intercept = float(getattr(dcm, "RescaleIntercept", 0))

        qimg = get_qimage(dcm)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label.width(), self.label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(pixmap)

    def handle_scroll(self, event):
        self.scroll_accumulator += event.angleDelta().y()
        threshold = 120
        if self.scroll_accumulator >= threshold:
            if self.current_index > 0:
                self.slider.setValue(self.current_index - 1)
            self.scroll_accumulator = 0
        elif self.scroll_accumulator <= -threshold:
            if self.current_index < len(self.dicom_slices) - 1:
                self.slider.setValue(self.current_index + 1)
            self.scroll_accumulator = 0

    def mouse_moved(self, event):
        if not hasattr(self, "img_array"):
            return
        x = event.pos().x()
        y = event.pos().y()
        if self.label.pixmap():
            label_pix = self.label.pixmap()
            img_w = self.img_array.shape[1]
            img_h = self.img_array.shape[0]
            scale_w = label_pix.width() / img_w
            scale_h = label_pix.height() / img_h

            true_x = int(x / scale_w)
            true_y = int(y / scale_h)

            if 0 <= true_x < img_w and 0 <= true_y < img_h:
                px = self.img_array[true_y, true_x]
                hu = self.slope * px + self.intercept
                mm_x = true_x * float(self.pixel_spacing[1])
                mm_y = true_y * float(self.pixel_spacing[0])
                self.setWindowTitle(
                    f"Slice {self.current_index + 1} | x={true_x}, y={true_y} "
                    f"(mm: {mm_x:.2f}, {mm_y:.2f}) | HU={int(hu)}"
                )

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