# frontend/main.py

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QCheckBox,
                             QComboBox, QLabel, QSizePolicy, QSpacerItem, QColorDialog,
                             QSlider, QSpinBox)
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

        # --- Slicer (collapsible) ---
        self.slicer_toggle_btn = QPushButton("Slicer ▸")
        self.slicer_toggle_btn.setCheckable(True)
        self.slicer_toggle_btn.setChecked(False)
        self.slicer_toggle_btn.toggled.connect(self.toggle_slicer_panel)
        controls_layout.addWidget(self.slicer_toggle_btn)

        self.slicer_panel = QWidget()
        self.slicer_panel_layout = QVBoxLayout(self.slicer_panel)
        self.slicer_panel.setVisible(False)

        # Enable checkbox
        self.slicer_enable = QCheckBox("Enable Slicer View")
        self.slicer_enable.setChecked(False)
        self.slicer_enable.stateChanged.connect(lambda s: self.renderer.set_slice_mode(bool(s)))
        self.slicer_panel_layout.addWidget(self.slicer_enable)

        # Axis selector
        axis_row = QHBoxLayout()
        axis_row.addWidget(QLabel("Axis"))
        self.slicer_axis = QComboBox()
        self.slicer_axis.addItems(["Z (depth)", "Y (row)", "X (col)"])
        self.slicer_axis.currentIndexChanged.connect(self.on_slicer_axis_changed)
        axis_row.addWidget(self.slicer_axis)
        self.slicer_panel_layout.addLayout(axis_row)

        # Slice slider + spin
        slice_row = QHBoxLayout()
        self.slice_label = QLabel("Slice: 0")
        slice_row.addWidget(self.slice_label)
        self.slicer_slider = QSlider(Qt.Orientation.Horizontal)
        self.slicer_slider.setMinimum(0)
        self.slicer_slider.setMaximum(0)
        self.slicer_slider.setValue(0)
        self.slicer_slider.valueChanged.connect(self.on_slicer_index_changed)
        slice_row.addWidget(self.slicer_slider)
        self.slicer_spin = QSpinBox()
        self.slicer_spin.setMinimum(0)
        self.slicer_spin.setMaximum(0)
        self.slicer_spin.valueChanged.connect(self.on_slicer_index_changed)
        slice_row.addWidget(self.slicer_spin)
        self.slicer_panel_layout.addLayout(slice_row)

        controls_layout.addWidget(self.slicer_panel)

        # Spacer to push items up
        controls_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Reset button at the bottom
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.clicked.connect(self.reset_defaults)
        controls_layout.addWidget(self.reset_btn)

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
                # Initialize slicer limits using volume dims
                self.init_slicer_limits()
                self.gl_widget.update() # Trigger repaint to show bounding box
            else:
                print("Python: Load failed.")

    def on_bbox_scale_changed(self, slider_value: int):
        scale = max(0.1, min(5.0, slider_value / 100.0))
        self.renderer.set_bounding_box_scale(scale)
        self.bbox_label.setText(f"Bounding Box Scale: {scale:.2f}x")
        self.gl_widget.update()

    def reset_defaults(self):
        # Defaults
        default_bg = (0.1, 0.1, 0.2)
        default_cmap_idx = 0  # Gray
        default_bbox_scale = 100  # 1.00x
        default_show_bbox = True
        default_show_overlay = True
        default_slicer_enabled = False
        default_slicer_axis = 0
        default_slicer_index = 0

        # Apply to UI controls (signals will update renderer for some)
        self.cmap_combo.setCurrentIndex(default_cmap_idx)
        self.bbox_slider.setValue(default_bbox_scale)
        self.bbox_checkbox.setChecked(default_show_bbox)
        self.overlay_checkbox.setChecked(default_show_overlay)
        self.slicer_toggle_btn.setChecked(False)
        self.slicer_enable.setChecked(default_slicer_enabled)
        self.slicer_axis.setCurrentIndex(default_slicer_axis)
        self.slicer_slider.setValue(default_slicer_index)
        self.slicer_spin.setValue(default_slicer_index)

        # Apply to renderer explicitly for background color
        r, g, b = default_bg
        self.renderer.set_background_color(r, g, b)

        # Ensure dependent updates
        self.on_bbox_scale_changed(default_bbox_scale)
        self.gl_widget.set_overlay_visible(default_show_overlay)
        self.gl_widget.update()

    # --- Slicer helpers ---
    def toggle_slicer_panel(self, checked: bool):
        self.slicer_panel.setVisible(checked)
        self.slicer_toggle_btn.setText("Slicer ▾" if checked else "Slicer ▸")

    def init_slicer_limits(self):
        # Get volume dims from backend
        w = self.renderer.get_volume_width()
        h = self.renderer.get_volume_height()
        d = self.renderer.get_volume_depth()
        # Set limits based on current axis
        axis = self.slicer_axis.currentIndex()
        max_idx = {0: max(0, d-1), 1: max(0, h-1), 2: max(0, w-1)}[axis]
        self.slicer_slider.setMaximum(max_idx)
        self.slicer_spin.setMaximum(max_idx)
        mid = max_idx // 2
        self.slicer_slider.setValue(mid)
        self.slicer_spin.setValue(mid)
        self.slice_label.setText(f"Slice: {mid}")
        # Send to backend
        self.renderer.set_slice_axis(axis)
        self.renderer.set_slice_index(mid)

    def on_slicer_axis_changed(self, idx: int):
        self.renderer.set_slice_axis(int(idx))
        self.init_slicer_limits()
        self.gl_widget.update()

    def on_slicer_index_changed(self, value: int):
        # Keep slider and spin synchronized
        sender = self.sender()
        if sender is self.slicer_slider and self.slicer_spin.value() != value:
            self.slicer_spin.setValue(value)
        elif sender is self.slicer_spin and self.slicer_slider.value() != value:
            self.slicer_slider.setValue(value)
        self.slice_label.setText(f"Slice: {value}")
        self.renderer.set_slice_index(int(value))
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

    