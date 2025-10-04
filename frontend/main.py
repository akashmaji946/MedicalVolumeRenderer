import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QCheckBox,
                             QComboBox, QLabel, QSizePolicy, QSpacerItem, QColorDialog,
                             QSlider, QSpinBox, QInputDialog)
from PyQt6.QtGui import QSurfaceFormat, QShortcut
from PyQt6.QtCore import Qt, QTimer
import json
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

        # History (last 10 files) — placed right under Load
        hist_row = QHBoxLayout()
        hist_row.addWidget(QLabel("History"))
        self.history_combo = QComboBox()
        self.history_paths = []  # maintain full paths in parallel
        self.history_combo.setMinimumWidth(220)
        hist_row.addWidget(self.history_combo)
        self.history_load_btn = QPushButton("Load")
        self.history_load_btn.setToolTip("Load the selected file from history")
        self.history_load_btn.clicked.connect(self.load_from_history)
        hist_row.addWidget(self.history_load_btn)
        controls_layout.addLayout(hist_row)
        # Load persisted history
        self.load_history()

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

        # Auto sweep controls
        auto_row = QHBoxLayout()
        self.slicer_auto = QCheckBox("Auto Sweep")
        self.slicer_auto.setChecked(False)
        self.slicer_auto.stateChanged.connect(self.toggle_auto_sweep)
        auto_row.addWidget(self.slicer_auto)
        auto_row.addWidget(QLabel("Speed"))
        self.slicer_speed = QSlider(Qt.Orientation.Horizontal)
        self.slicer_speed.setMinimum(1)   # 1 step/sec
        self.slicer_speed.setMaximum(20)  # 20 steps/sec
        self.slicer_speed.setValue(5)
        self.slicer_speed.setFixedWidth(120)
        self.slicer_speed.valueChanged.connect(self.on_slicer_speed_changed)
        auto_row.addWidget(self.slicer_speed)
        self.slicer_panel_layout.addLayout(auto_row)

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

        # Timer for auto sweep
        self.slicer_timer = QTimer(self)
        self.slicer_timer.timeout.connect(self.step_slicer)

        # Spacer to push items up
        controls_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Save buttons (bottom) ---
        save_bottom = QHBoxLayout()
        self.btn_save_image = QPushButton("Save Image")
        self.btn_save_image.setToolTip("Save the volume/slice image including bounding box (overlay hidden)")
        self.btn_save_image.clicked.connect(self.save_volume_only_image)
        save_bottom.addWidget(self.btn_save_image)

        self.btn_save_screen = QPushButton("Save Screen")
        self.btn_save_screen.setToolTip("Save a screenshot of the entire application window")
        self.btn_save_screen.clicked.connect(self.save_full_screenshot)
        save_bottom.addWidget(self.btn_save_screen)
        controls_layout.addLayout(save_bottom)

        # View alignment row: Reset View + Z/Y/X normals in one line
        view_row = QHBoxLayout()
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.setToolTip("Reset camera to initial framing without changing any other settings")
        self.reset_view_btn.clicked.connect(self.reset_view)
        view_row.addWidget(self.reset_view_btn)

        self.btn_view_z = QPushButton("Z-normal")
        self.btn_view_z.setToolTip("View along +Z (depth)")
        self.btn_view_z.clicked.connect(lambda: self.view_align('Z'))
        view_row.addWidget(self.btn_view_z)

        self.btn_view_y = QPushButton("Y-normal")
        self.btn_view_y.setToolTip("View along +Y (row)")
        self.btn_view_y.clicked.connect(lambda: self.view_align('Y'))
        view_row.addWidget(self.btn_view_y)

        self.btn_view_x = QPushButton("X-normal")
        self.btn_view_x.setToolTip("View along +X (col)")
        self.btn_view_x.clicked.connect(lambda: self.view_align('X'))
        view_row.addWidget(self.btn_view_x)

        controls_layout.addLayout(view_row)

        # Reset button at the very bottom
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
                    self.gl_widget.set_dataset_path(path)
                except Exception:
                    self.gl_widget.set_dataset_name("")
                # Add to history (unique, max 10)
                self.push_history(path)
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
        default_slicer_auto = False
        default_slicer_speed = 5

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
        self.slicer_auto.setChecked(default_slicer_auto)
        self.slicer_speed.setValue(default_slicer_speed)

        # Apply to renderer explicitly for background color
        r, g, b = default_bg
        self.renderer.set_background_color(r, g, b)

        # Ensure dependent updates
        self.on_bbox_scale_changed(default_bbox_scale)
        # Reset camera to frame the (unscaled) volume bounding box
        try:
            self.renderer.frame_camera_to_box()
        except Exception:
            pass
        self.gl_widget.set_overlay_visible(default_show_overlay)
        self.gl_widget.update()

    # --- History helpers ---
    def push_history(self, path: str):
        # Keep unique entries; newest first; max 10
        if path in self.history_paths:
            self.history_paths.remove(path)
        self.history_paths.insert(0, path)
        self.history_paths = self.history_paths[:10]
        # Update combo
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItems([os.path.basename(p) for p in self.history_paths])
        self.history_combo.blockSignals(False)
        # Persist
        self.save_history()

    def load_from_history(self):
        idx = self.history_combo.currentIndex()
        if idx < 0 or idx >= len(self.history_paths):
            return
        path = self.history_paths[idx]
        if not path:
            return
        print(f"Python: Loading {path} from history")
        if self.renderer.load_volume(path):
            print("Python: Load successful.")
            try:
                name = os.path.basename(path)
                self.gl_widget.set_dataset_name(name)
                self.gl_widget.set_dataset_path(path)
            except Exception:
                self.gl_widget.set_dataset_name("")
            # Re-apply current UI state
            self.renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
            self.renderer.set_colormap_preset(self.cmap_combo.currentIndex())
            self.on_bbox_scale_changed(self.bbox_slider.value())
            self.init_slicer_limits()
            self.gl_widget.update()
        else:
            print("Python: Load failed.")

    # --- Persistence for history (.mvr/history.json) ---
    def _history_dir(self) -> str:
        # Project root is one directory up from this file's directory (frontend/)
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        d = os.path.join(root, ".mvr")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _history_file(self) -> str:
        return os.path.join(self._history_dir(), "history.json")

    def load_history(self):
        try:
            with open(self._history_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
                paths = data.get("recent", [])
                # Filter to existing files only
                self.history_paths = [p for p in paths if isinstance(p, str) and os.path.exists(p)]
        except Exception:
            self.history_paths = []
        # Populate combo
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItems([os.path.basename(p) for p in self.history_paths])
        self.history_combo.blockSignals(False)

    def save_history(self):
        try:
            with open(self._history_file(), "w", encoding="utf-8") as f:
                json.dump({"recent": self.history_paths}, f, indent=2)
        except Exception:
            pass

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
        # If auto sweeping, ensure timer interval updated
        if self.slicer_auto.isChecked():
            self.toggle_auto_sweep(True)

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

    # --- Save handlers ---
    def _pick_save_path(self, caption: str, default_name: str = "image.png") -> str:
        path, _ = QFileDialog.getSaveFileName(self, caption, default_name, "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)")
        return path

    def _pick_export_resolution(self):
        """Ask user for export resolution preset or custom size.
        Returns (width, height) or None if cancelled.
        """
        presets = [
            "Window size",
            "1920 x 1080",
            "2560 x 1440",
            "3840 x 2160",
            "Custom...",
        ]
        choice, ok = QInputDialog.getItem(self, "Select Export Resolution", "Resolution", presets, 0, False)
        if not ok:
            return None
        if choice == "Window size":
            return (self.gl_widget.width(), self.gl_widget.height())
        if choice == "1920 x 1080":
            return (1920, 1080)
        if choice == "2560 x 1440":
            return (2560, 1440)
        if choice == "3840 x 2160":
            return (3840, 2160)
        # Custom
        w, ok1 = QInputDialog.getInt(self, "Custom Width", "Width (px)", 1920, 16, 16384, 1)
        if not ok1:
            return None
        h, ok2 = QInputDialog.getInt(self, "Custom Height", "Height (px)", 1080, 16, 16384, 1)
        if not ok2:
            return None
        return (int(w), int(h))

    def save_render_image(self):
        path = self._pick_save_path("Save Render Image", "render.png")
        if not path:
            return
        img = self.gl_widget.grab_render_image()  # QImage
        img.save(path)

    def save_full_screenshot(self):
        path = self._pick_save_path("Save Full Screenshot", "screenshot.png")
        if not path:
            return
        shot = self.gl_widget.grab_window_image()  # QPixmap
        if shot is not None:
            shot.save(path)

    def save_volume_only_image(self):
        """Save the render image (including bounding box, overlay hidden) with custom resolution export."""
        path = self._pick_save_path("Save Volume/Slice Only", "volume.png")
        if not path:
            return
        res = self._pick_export_resolution()
        if not res:
            return
        exp_w, exp_h = res
        # Temporarily hide overlay only (keep bbox)
        prev_overlay = self.overlay_checkbox.isChecked()
        try:
            if prev_overlay:
                self.overlay_checkbox.setChecked(False)
                self.gl_widget.set_overlay_visible(False)
            self.gl_widget.update()
            # Render offscreen at requested resolution
            img = self.gl_widget.render_offscreen(exp_w, exp_h)
            img.save(path)
        finally:
            # Restore
            self.overlay_checkbox.setChecked(prev_overlay)
            self.gl_widget.set_overlay_visible(prev_overlay)
            self.gl_widget.update()

    def reset_view(self):
        """Reset only the camera/view to the initial framing of the current volume."""
        try:
            self.renderer.frame_camera_to_box()
        except Exception:
            pass
        self.gl_widget.update()

    def view_align(self, axis: str):
        """Align camera to look along +axis (Z/Y/X)."""
        # Map axis to (azimuth, elevation) in degrees for our spherical camera.
        # Position equations:
        #   x = r*cos(elev)*sin(azim); y = r*sin(elev); z = r*cos(elev)*cos(azim)
        if axis == 'Z':
            azim, elev = 0.0, 0.0        # +Z
        elif axis == 'Y':
            azim, elev = 0.0, 89.0       # near +Y (avoid exact pole)
        elif axis == 'X':
            azim, elev = 90.0, 0.0       # +X
        else:
            return
        try:
            # Reframe to a consistent radius, then set angles
            self.renderer.frame_camera_to_box()
            self.renderer.set_camera_angles(azim, elev)
        except Exception as e:
            print(f"Python: view_align error: {e}")
        self.gl_widget.update()

    def get_slicer_max_index(self) -> int:
        w = self.renderer.get_volume_width()
        h = self.renderer.get_volume_height()
        d = self.renderer.get_volume_depth()
        axis = self.slicer_axis.currentIndex()
        return {0: max(0, d-1), 1: max(0, h-1), 2: max(0, w-1)}[axis]

    def on_slicer_speed_changed(self, value: int):
        # Adjust timer interval if running; interval in ms ~ 1000/steps_per_sec
        if self.slicer_timer.isActive():
            interval = max(10, int(1000 / max(1, value)))
            self.slicer_timer.start(interval)

    def toggle_auto_sweep(self, checked: bool):
        if checked and self.slicer_enable.isChecked():
            interval = max(10, int(1000 / max(1, self.slicer_speed.value())))
            self.slicer_timer.start(interval)
        else:
            self.slicer_timer.stop()

    def step_slicer(self):
        # Move slice by +1 and wrap around
        current = self.slicer_slider.value()
        max_idx = self.get_slicer_max_index()
        next_idx = 0 if max_idx <= 0 else (current + 1) % (max_idx + 1)
        # Update via spin to keep both in sync through handlers
        self.slicer_spin.setValue(next_idx)

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

    