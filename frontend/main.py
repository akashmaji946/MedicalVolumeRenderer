# frontend/main.py

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QCheckBox,
                             QComboBox, QLabel, QSizePolicy, QSpacerItem, QColorDialog, QSlider)
from PyQt6.QtGui import QSurfaceFormat, QShortcut
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSurfaceFormat  # <-- Import QSurfaceFormat

import volumerenderer
from opengl_widget import OpenGLWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medical Volume Renderer")
        # Start with a reasonable size; user can maximize/minimize
        self.resize(1600, 900)

        self.renderer = volumerenderer.Renderer()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root = QHBoxLayout(central_widget)

        # Left: OpenGL view (resizes with window)
        self.gl_widget = OpenGLWidget(self.renderer)
        self.gl_widget.setMinimumSize(800, 600)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.gl_widget, 1)

        # Right: controls panel
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setSpacing(8)

        # Load button
        self.load_button = QPushButton("Load NIfTI/DICOM File")
        self.load_button.clicked.connect(self.load_file)
        controls_layout.addWidget(self.load_button)

        # Background color selector
        bg_row = QHBoxLayout()
        self.bg_label = QLabel("Background Color")
        bg_row.addWidget(self.bg_label)
        self.bg_pick_btn = QPushButton("Pick Color")
        self.bg_pick_btn.clicked.connect(self.pick_background_color)
        bg_row.addWidget(self.bg_pick_btn)
        controls_layout.addLayout(bg_row)

        # Window controls
        win_controls_row = QHBoxLayout()
        self.min_btn = QPushButton("Minimize")
        self.min_btn.clicked.connect(self.showMinimized)
        win_controls_row.addWidget(self.min_btn)

        self.max_btn = QPushButton("Maximize/Restore")
        self.max_btn.clicked.connect(self.toggle_maximize)
        win_controls_row.addWidget(self.max_btn)

        self.full_btn = QPushButton("Fullscreen")
        self.full_btn.clicked.connect(self.toggle_fullscreen)
        win_controls_row.addWidget(self.full_btn)

        controls_layout.addLayout(win_controls_row)

        # Bounding box toggle
        self.bbox_checkbox = QCheckBox("Show Bounding Box")
        self.bbox_checkbox.setChecked(True)
        self.bbox_checkbox.stateChanged.connect(lambda s: self.renderer.set_show_bounding_box(bool(s)))
        controls_layout.addWidget(self.bbox_checkbox)

        # Overlay (FPS/filename) toggle
        self.overlay_checkbox = QCheckBox("Show Overlay (FPS & Name)")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.stateChanged.connect(lambda s: self.gl_widget.set_overlay_visible(bool(s)))
        controls_layout.addWidget(self.overlay_checkbox)

        # Colormap selector
        controls_layout.addWidget(QLabel("Pick Colormap"))
        self.cmap_combo = QComboBox()
        self.cmap_presets = [
            "Grayscale",            # 0
            "Grayscale (Inverted)", # 1
            "Hot",                  # 2
            "Cool",                 # 3
            "Spring",               # 4
            "Summer",               # 5
            "Autumn",               # 6
            "Winter",               # 7
            "Jet-like",             # 8
            "Viridis-like"          # 9
        ]
        self.cmap_combo.addItems(self.cmap_presets)
        self.cmap_combo.currentIndexChanged.connect(lambda idx: self.renderer.set_colormap_preset(int(idx)))
        controls_layout.addWidget(self.cmap_combo)

        # Bounding box scale slider (0.1x .. 5.0x)
        bbox_row = QHBoxLayout()
        self.bbox_label = QLabel("Bounding Box Scale: 1.0x")
        bbox_row.addWidget(self.bbox_label)
        self.bbox_slider = QSlider(Qt.Orientation.Horizontal)
        self.bbox_slider.setMinimum(10)   # 0.1x
        self.bbox_slider.setMaximum(500)  # 5.0x
        self.bbox_slider.setValue(100)    # 1.0x default
        self.bbox_slider.setSingleStep(5)
        self.bbox_slider.setPageStep(10)
        self.bbox_slider.valueChanged.connect(self.on_bbox_scale_changed)
        bbox_row.addWidget(self.bbox_slider)
        controls_layout.addLayout(bbox_row)

        # Spacer to push items up
        controls_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Fix a comfortable width for the controls panel
        controls.setMinimumWidth(320)
        controls.setMaximumWidth(420)
        root.addWidget(controls)

        # Keyboard shortcuts: F11 to toggle fullscreen, Esc to exit fullscreen
        QShortcut(Qt.Key.Key_F11, self, activated=self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_Escape, self, activated=self.exit_fullscreen)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "NIfTI Files (*.nii *.nii.gz);;All Files (*)")
        if path:
            print(f"Python: Loading {path}")
            if self.renderer.load_volume(path):
                print("Python: Load successful.")
                # Update overlay with dataset name
                try:
                    name = os.path.basename(path)
                    self.gl_widget.set_dataset_name(name)
                except Exception:
                    self.gl_widget.set_dataset_name("")
                # Ensure current UI state is applied post-load
                self.renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
                self.renderer.set_colormap_preset(self.cmap_combo.currentIndex())
                # Apply current bbox scale
                self.on_bbox_scale_changed(self.bbox_slider.value())
                self.gl_widget.update() # Trigger repaint to show bounding box
            else:
                print("Python: Load failed.")

    def on_bbox_scale_changed(self, slider_value: int):
        scale = max(0.1, min(5.0, slider_value / 100.0))
        self.renderer.set_bounding_box_scale(scale)
        self.bbox_label.setText(f"Bounding Box Scale: {scale:.2f}x")
        self.gl_widget.update()

    def pick_background_color(self):
        # Get the current window background color as starting point (fallback to dark blue)
        initial = QColorDialog.getColor()
        if initial.isValid():
            r = initial.redF()
            g = initial.greenF()
            b = initial.blueF()
            # Apply to renderer
            self.renderer.set_background_color(r, g, b)
            self.gl_widget.update()

    # --- Window control helpers ---
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.full_btn.setText("Fullscreen")
        else:
            self.showFullScreen()
            self.full_btn.setText("Exit Fullscreen")

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.full_btn.setText("Fullscreen")

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # --- CRITICAL: Set the Default OpenGL Surface Format ---
    # This must be done BEFORE the first window is created.
    format = QSurfaceFormat()
    format.setDepthBufferSize(24)  # Request a 24-bit depth buffer
    format.setVersion(3, 3)        # Request OpenGL 3.3
    # PyQt6: use OpenGLContextProfile enum
    format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(format)
    # ----------------------------------------------------

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

    