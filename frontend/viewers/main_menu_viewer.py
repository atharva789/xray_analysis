from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from viewers.single_slice_viewer import SingleSliceViewer
from viewers.full_stack_viewer import FullStackViewer
from viewers.mask_side_by_side_viewer import MaskSideBySideViewer
from viewers.mask_overlay_viewer import MaskOverlayViewer

class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CT DICOM Viewer - Main Menu")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # Basic Viewers
        single_btn = QPushButton("Single Slice Viewer")
        single_btn.clicked.connect(self.launch_single)

        full_btn = QPushButton("Full Stack Viewer")
        full_btn.clicked.connect(self.launch_full)

        layout.addWidget(single_btn)
        layout.addWidget(full_btn)

        # Merged Side-by-Side Viewer
        side_by_side_btn = QPushButton("Side-by-Side Viewer")
        side_by_side_btn.clicked.connect(self.launch_side_by_side)

        layout.addWidget(side_by_side_btn)

        # Overlay Viewer
        overlay_btn = QPushButton("Overlay Viewer")
        overlay_btn.clicked.connect(self.launch_overlay)

        layout.addWidget(overlay_btn)

        self.setLayout(layout)

    def launch_single(self):
        self.single = SingleSliceViewer()
        self.single.show()

    def launch_full(self):
        self.full = FullStackViewer()
        self.full.show()

    def launch_side_by_side(self):
        self.side_by_side = MaskSideBySideViewer(mode="rgb")  # or "grayscale" if preferred
        self.side_by_side.show()

    def launch_overlay(self):
        self.overlay = MaskOverlayViewer()
        self.overlay.show()