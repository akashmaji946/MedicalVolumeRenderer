import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QCheckBox,
                             QComboBox, QLabel, QSizePolicy, QSpacerItem, QColorDialog,
                             QSlider, QSpinBox, QInputDialog, QTableWidget, QTableWidgetItem,
                             QDoubleSpinBox, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QHeaderView, QScrollArea, QGraphicsOpacityEffect, QFrame)
from PyQt6.QtGui import QSurfaceFormat, QShortcut, QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer
import json
from PyQt6.QtGui import QSurfaceFormat  # <-- Import QSurfaceFormat

import volumerenderer
import pyqtgraph as pg
from opengl_widget import OpenGLWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medical Volume Renderer")

        ## print ascii logo
        # ____________________________
        # __  __  __      __  _____  
        # |  \/  | \ \    / / |  __ \ 
        # | |\/| |  \ \  / /  | |__) |
        # | |  | |   \ \/ /   |  _  / 
        # |_|  |_|    \__/    |_| \_\ 
        # MVR - Medical Volume Renderer
        # ____________________________

        print(r"""
            ____________________________
             __  __  __      __  _____  
            |  \/  | \ \    / / |  __ \ 
            | |\/| |  \ \  / /  | |__) |
            | |  | |   \ \/ /   |  _  / 
            |_|  |_|    \__/    |_| \_\ 
            MVR - Medical Volume Renderer
            ____________________________
            """)

        # Start with a reasonable size; user can maximize/minimize
        self.resize(1600, 900)

        # Keep separate instances for default and VTK renderers; switch as needed
        self.renderer_default = volumerenderer.Renderer()
        self.renderer = self.renderer_default
        self.vtk_renderer = None
        self.is_vtk_mode = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root = QHBoxLayout(central_widget)

        # --- Very light background image overlay (entire window) ---
        try:
            self._bg_image_label = QLabel(central_widget)
            self._bg_image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._bg_image_label.setScaledContents(True)
            # Resolve image path: ../images/ascii-art-text.png
            app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            bg_path = os.path.join(app_root, 'images', 'ascii-art-text.png')
            self._bg_pix = QPixmap(bg_path) if os.path.exists(bg_path) else QPixmap()
            # Apply faint opacity
            self._bg_opacity = QGraphicsOpacityEffect(self._bg_image_label)
            self._bg_opacity.setOpacity(0.3)  # very light overlay
            self._bg_image_label.setGraphicsEffect(self._bg_opacity)
            # Place above content but click-through so it won't block interaction
            self._bg_image_label.raise_()
            # Initial geometry and pixmap
            self._resize_background_label()
        except Exception:
            self._bg_image_label = None

        # Left: OpenGL view (resizes with window)
        self.gl_widget = OpenGLWidget(self.renderer)
        self.gl_widget.setMinimumSize(800, 600)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.gl_widget, 1)

        # Right: controls panel (wrapped in a scroll area to avoid overflow)
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        # Make the controls panel more compact
        controls_layout.setSpacing(6)
        controls_layout.setContentsMargins(6, 6, 6, 6)
        # Reduce font size for the entire controls panel (does not affect GL view)
        small_font = QFont()
        # Slightly larger than before, still compact
        small_font.setPointSize(max(9, self.font().pointSize() - 1))
        controls.setFont(small_font)
        # Tighten default widget paddings via stylesheet
        controls.setStyleSheet(
        """
        QWidget {
            font-size: 13px;
            color: #0a0a0a;
            background-color: #f7f9fc;
        }

        /* Buttons - very light elegant blue with soft gradients */
        QPushButton {
            padding: 6px 10px;
            min-height: 28px;
            color: #0a0a0a;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #e9f3ff, stop:1 #cfe3ff);
            border: 1px solid #a8cfff;
            border-radius: 6px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #d8e9ff, stop:1 #bcd8ff);
            border: 1px solid #7fb8ff;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #b8d3ff, stop:1 #9ec5ff);
        }

        /* ComboBoxes - matching aesthetic */
        QComboBox {
            padding: 4px 8px;
            min-height: 26px;
            color: #0a0a0a;
            background: #e9f3ff;
            border: 1px solid #a8cfff;
            border-radius: 5px;
        }
        QComboBox:hover {
            background: #d8e9ff;
            border-color: #7fb8ff;
        }

        QSpinBox, QDoubleSpinBox {
            padding: 2px 6px;
            min-height: 24px;
            border: 1px solid #a8cfff;
            border-radius: 5px;
            background: #ffffff;
        }

        QLabel {
            font-size: 13px;
        }

        QCheckBox {
            font-size: 13px;
            spacing: 4px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }

        /* Table and headers */
        QHeaderView::section {
            padding: 4px 6px;
            font-size: 12px;
            background: #e2f0ff;
            color: #0a0a0a;
            border: 0px;
            border-bottom: 1px solid #000000;
        }

        QTableWidget {
            gridline-color: #000000;
            background: #ffffff;
        }

        /* Sliders */
        QSlider::groove:horizontal {
            height: 8px;
            background: rgba(120,180,255,0.35);
            margin: 4px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #77a9e6;
            width: 14px;
            margin: -6px 0;
            border-radius: 7px;
        }
        QSlider::groove:vertical {
            width: 8px;
            background: rgba(120,180,255,0.35);
            margin: 0 4px;
            border-radius: 4px;
        }
        QSlider::handle:vertical {
            background: #77a9e6;
            height: 14px;
            margin: 0 -6px;
            border-radius: 7px;
        }

        /* Black separators for clarity */
        QFrame#SectionSeparator {
            background: #000000;
            height: 1px;
            margin-top: 4px;
            margin-bottom: 4px;
        }
        """
        )


        # Load button
        self.load_button = QPushButton("Load NIfTI/DICOM File")
        self.load_button.clicked.connect(self.load_file)
        controls_layout.addWidget(self.load_button)

        # Quick VTK load button directly below
        self.vtk_quick_load_btn = QPushButton("Load VTK File")
        self.vtk_quick_load_btn.setToolTip("Load a .vtk structured points/grid volume")
        self.vtk_quick_load_btn.clicked.connect(self.load_vtk_file)
        controls_layout.addWidget(self.vtk_quick_load_btn)
        controls_layout.addWidget(self._make_separator())

        # VTK Field selector (top, visible always)
        vtk_field_row_top = QHBoxLayout()
        vtk_field_row_top.addWidget(QLabel("Field"))
        self.vtk_field_combo = QComboBox()
        self.vtk_field_combo.currentIndexChanged.connect(self.on_vtk_field_changed)
        vtk_field_row_top.addWidget(self.vtk_field_combo)
        controls_layout.addLayout(vtk_field_row_top)

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

        # Background color controls (will be shown on the same row as Fullscreen)
        self.bg_label = QLabel("Background Color")
        self.bg_pick_btn = QPushButton("Pick Color")
        self.bg_pick_btn.clicked.connect(self.pick_background_color)

        # Window controls (Fullscreen + Background color on the same row)
        win_controls_row = QHBoxLayout()
        self.full_btn = QPushButton("Fullscreen")
        self.full_btn.clicked.connect(self.toggle_fullscreen)
        win_controls_row.addWidget(self.full_btn)
        # Spacer
        win_controls_row.addStretch(1)
        # Background color label + button
        win_controls_row.addWidget(self.bg_label)
        win_controls_row.addWidget(self.bg_pick_btn)
        controls_layout.addLayout(win_controls_row)

        # Toggles row: Bounding box + Overlay on the same row
        toggles_row = QHBoxLayout()
        self.bbox_checkbox = QCheckBox("Show Bounding Box")
        self.bbox_checkbox.setChecked(True)
        self.bbox_checkbox.stateChanged.connect(self.on_bbox_toggled)
        toggles_row.addWidget(self.bbox_checkbox)
        self.overlay_checkbox = QCheckBox("Show Overlay (FPS & Name)")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.stateChanged.connect(lambda s: self.set_overlay_all_visible(bool(s)))
        toggles_row.addWidget(self.overlay_checkbox)
        toggles_row.addStretch(1)
        controls_layout.addLayout(toggles_row)
        controls_layout.addWidget(self._make_separator())

        # Colormap selector (label removed per request)
        self.cmap_combo = QComboBox()
        # Backend tinycolormap presets (order matters; must match Renderer.cpp mapping)
        self.cmap_presets = [
            "Gray",               # 0
            "Gray (Inverted)",   # 1
            "Parula",            # 2
            "Heat",              # 3
            "Jet",               # 4
            "Turbo",             # 5
            "Hot",               # 6
            "Magma",             # 7
            "Inferno",           # 8
            "Plasma",            # 9
            "Viridis",           # 10
            "Cividis",           # 11
            "Github",            # 12
            "Cubehelix",         # 13
            "HSV",               # 14
        ]
        self.cmap_combo.addItems(self.cmap_presets)
        self.cmap_combo.currentIndexChanged.connect(self.on_cmap_changed)
        controls_layout.addWidget(self.cmap_combo)
        # Map our backend preset indices to pyqtgraph preset names for gradient preview
        # Use best-available approximations when an exact preset does not exist in pyqtgraph
        self._pg_preset_map = {
            0: 'grey',        # Gray
            1: 'grey',        # Gray (Inverted) -> will reverse in _apply_preset_to_gradient
            2: 'viridis',     # Parula (approx)
            3: 'thermal',     # Heat (approx)
            4: 'spectrum',    # Jet via HSV spectrum
            5: 'turbo',       # Turbo
            6: 'hot',         # Hot
            7: 'magma',       # Magma
            8: 'inferno',     # Inferno
            9: 'plasma',      # Plasma
            10: 'viridis',    # Viridis
            11: 'viridis',   # Cividis approx
            12: 'grey',       # Github (no direct; placeholder)
            13: 'grey',       # Cubehelix (no direct; placeholder)
            14: 'spectrum',   # HSV
        }

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
        self.slicer_panel_layout.setSpacing(4)
        self.slicer_panel_layout.setContentsMargins(0,0,0,0)
        self.slicer_panel.setVisible(False)
        controls_layout.addWidget(self.slicer_panel)
        controls_layout.addWidget(self._make_separator())

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

        # --- Colormap / Transfer Function (collapsible) ---
        self.tf_toggle_btn = QPushButton("Colormap / Transfer Function ▸")
        self.tf_toggle_btn.setCheckable(True)
        self.tf_toggle_btn.setChecked(False)
        self.tf_toggle_btn.toggled.connect(self.toggle_tf_panel)
        controls_layout.addWidget(self.tf_toggle_btn)

        self.tf_panel = QWidget()
        self.tf_panel_layout = QVBoxLayout(self.tf_panel)
        self.tf_panel_layout.setSpacing(4)
        self.tf_panel_layout.setContentsMargins(0,0,0,0)
        self.tf_panel.setVisible(False)

        # Preset vs Custom
        tf_mode_row = QHBoxLayout()
        tf_mode_row.addWidget(QLabel("Mode"))
        self.tf_mode_combo = QComboBox()
        self.tf_mode_combo.addItems(["Preset", "Custom"])
        self.tf_mode_combo.currentIndexChanged.connect(self.on_tf_mode_changed)
        tf_mode_row.addWidget(self.tf_mode_combo)
        self.tf_panel_layout.addLayout(tf_mode_row)

        # Preset helper (reuse existing cmap combo) — wrap in a QWidget to control visibility
        self.preset_row = QWidget()
        preset_row = QHBoxLayout(self.preset_row)
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.addWidget(QLabel("Preset"))
        self.tf_preset_combo = self.cmap_combo  # reuse
        preset_row.addWidget(self.tf_preset_combo)
        self.tf_panel_layout.addWidget(self.preset_row)

        # Custom Preset selector (only used in Custom mode)
        self.custom_preset_row = QWidget()
        custom_row_layout = QHBoxLayout(self.custom_preset_row)
        custom_row_layout.setContentsMargins(0, 0, 0, 0)
        custom_row_layout.addWidget(QLabel("Custom Preset"))
        self.custom_cmap_combo = QComboBox()
        # Provide a comprehensive list of pyqtgraph presets
        self._custom_presets = [
            ("Grey", "grey"),
            ("Grey Clip", "greyclip"),
            ("Thermal", "thermal"),
            ("Flame", "flame"),
            ("Yellowy", "yellowy"),
            ("Bipolar", "bipolar"),
            ("Spectrum (HSV)", "spectrum"),
            ("Cyclic (HSV)", "cyclic"),
            ("Viridis", "viridis"),
            ("Inferno", "inferno"),
            ("Plasma", "plasma"),
            ("Magma", "magma"),
            ("Turbo", "turbo"),
        ]
        self.custom_cmap_combo.addItems([name for name, _ in self._custom_presets])
        self.custom_cmap_combo.currentIndexChanged.connect(self.on_custom_cmap_changed)
        custom_row_layout.addWidget(self.custom_cmap_combo)
        self.tf_panel_layout.addWidget(self.custom_preset_row)

        # Custom TF table
        self.tf_table = QTableWidget(0, 5)
        self.tf_table.setHorizontalHeaderLabels(["Pos", "R", "G", "B", "A"])
        # Fit columns to available width
        header = self.tf_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tf_table.horizontalHeader().setStretchLastSection(True)
        # Hide vertical header to save space
        self.tf_table.verticalHeader().setVisible(False)
        # Disable scrollbars and let us control height
        self.tf_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tf_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tf_table.setShowGrid(False)
        # Compact row height for TF table
        self.tf_table.verticalHeader().setDefaultSectionSize(20)
        self.tf_panel_layout.addWidget(self.tf_table)

        # PyQtGraph Gradient Editor (for interactive control points)
        # Place inside a GraphicsLayoutWidget and below the table
        self._updating_from_gradient = False
        self._updating_from_table = False
        self.tf_graphics = pg.GraphicsLayoutWidget()
        self.gradient_editor = pg.GradientEditorItem()
        # Nice default preset for visibility
        try:
            self.gradient_editor.loadPreset('inferno')
        except Exception:
            pass
        self.gradient_editor.sigGradientChanged.connect(self.on_gradient_changed)
        self.tf_graphics.addItem(self.gradient_editor)
        self.tf_panel_layout.addWidget(self.tf_graphics)

        # Buttons for TF editing
        tf_btn_row = QHBoxLayout()
        self.tf_add_btn = QPushButton("Add")
        # Use lambda to avoid passing the 'checked' bool argument from clicked(bool)
        self.tf_add_btn.clicked.connect(lambda: self.tf_add_point())
        tf_btn_row.addWidget(self.tf_add_btn)
        self.tf_remove_btn = QPushButton("Remove")
        self.tf_remove_btn.clicked.connect(self.tf_remove_selected)
        tf_btn_row.addWidget(self.tf_remove_btn)
        self.tf_apply_btn = QPushButton("Apply")
        self.tf_apply_btn.clicked.connect(self.tf_apply_custom)
        tf_btn_row.addWidget(self.tf_apply_btn)
        self.tf_reset_btn = QPushButton("Reset")
        self.tf_reset_btn.clicked.connect(self.tf_reset_to_preset)
        tf_btn_row.addWidget(self.tf_reset_btn)
        self.tf_panel_layout.addLayout(tf_btn_row)

        controls_layout.addWidget(self.tf_panel)
        controls_layout.addWidget(self._make_separator())

        # Seed with a small useful default TF
        self.tf_seed_default()
        # Ensure table height matches its content
        self._resize_tf_table_to_contents()
        # Set initial visibility based on current TF mode (default Preset hides editor/table)
        self._update_tf_mode_visibility()


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
        controls_layout.addWidget(self._make_separator())

        # Reset button at the very bottom
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.clicked.connect(self.reset_defaults)
        controls_layout.addWidget(self.reset_btn)

        # Wrap controls in a scroll area so expanded panels are still accessible
        scroll = QScrollArea()
        scroll.setWidget(controls)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Fix a comfortable, more compact width for the controls area
        scroll.setMinimumWidth(260)
        scroll.setMaximumWidth(360)
        root.addWidget(scroll)

        # Keyboard shortcuts: F11 to toggle fullscreen, Esc to exit fullscreen
        QShortcut(Qt.Key.Key_F11, self, activated=self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_Escape, self, activated=self.exit_fullscreen)

        # Apply compact sizing to child widgets in the controls panel
        self._apply_compact_sizing(controls)
        # Ensure the overlay sits above after all widgets are laid out
        try:
            if self._bg_image_label:
                self._bg_image_label.raise_()
        except Exception:
            pass

    # --- Renderer switching helpers ---
    def switch_to_renderer(self, renderer, vtk_mode: bool):
        # Swap our active renderer and update the GL widget
        self.renderer = renderer
        try:
            self.gl_widget.set_renderer(renderer)
        except Exception:
            pass
        # Update mode flag and controls
        self.is_vtk_mode = vtk_mode
        self.update_controls_for_mode()
        # Re-apply some common settings if supported
        try:
            if hasattr(self.renderer, 'resize'):
                self.renderer.resize(self.gl_widget.width(), self.gl_widget.height())
            # Apply current bbox visibility and colormap to the new renderer if supported
            if hasattr(self.renderer, 'set_show_bounding_box'):
                self.renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
            if hasattr(self.renderer, 'set_colormap_preset'):
                self.renderer.set_colormap_preset(int(self.cmap_combo.currentIndex()))
            if hasattr(self.renderer, 'set_bounding_box_scale'):
                self.renderer.set_bounding_box_scale(self.bbox_slider.value() / 100.0)
        except Exception:
            pass

    # --- Notification helpers ---
    def _safe_alert(self, message: str, duration_ms: int):
        try:
            self.gl_widget.show_alert(message, duration_ms)
        except Exception:
            pass

    def _notify_loaded(self, path: str):
        name = os.path.basename(path) if path else ""
        # fire after 1s, visible for 3s
        try:
            QTimer.singleShot(1000, lambda: self._safe_alert(f"File: {name} loaded", 3000))
        except Exception:
            # Fallback: show immediately if timer fails
            self._safe_alert(f"File: {name} loaded", 3000)

    def update_controls_for_mode(self):
        # Keep all primary controls enabled in both modes as requested
        self.bbox_checkbox.setEnabled(True)
        self.cmap_combo.setEnabled(True)
        self.bbox_slider.setEnabled(True)
        # Slicer stays enabled in both modes
        # Background color is handled safely in code even if not supported by VTK
        # TF panel stays enabled in both modes

    # --- Event/handler refactors to be renderer-agnostic ---
    def on_bbox_toggled(self, state: int):
        try:
            if hasattr(self.renderer, 'set_show_bounding_box'):
                self.renderer.set_show_bounding_box(bool(state))
        except Exception:
            pass

    def _make_separator(self) -> QFrame:
        """Create a thin, light horizontal separator for the controls panel."""
        line = QFrame()
        line.setObjectName("SectionSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setFixedHeight(1)
        # Inline style in case global stylesheet is overridden later
        line.setStyleSheet("QFrame#SectionSeparator{background: rgba(255,255,255,0.12); margin: 6px 0;}")
        return line

    def _apply_compact_sizing(self, parent_widget: QWidget):
        """Reduce heights/paddings of buttons, sliders, and inputs to keep the UI compact."""
        try:
            from PyQt6.QtWidgets import QPushButton, QComboBox, QSlider, QSpinBox, QDoubleSpinBox
            # Buttons
            for btn in parent_widget.findChildren(QPushButton):
                btn.setMinimumHeight(24)
                btn.setMaximumHeight(28)
            # Combos
            for cb in parent_widget.findChildren(QComboBox):
                cb.setMinimumHeight(24)
                cb.setMaximumHeight(28)
            # Sliders
            for sl in parent_widget.findChildren(QSlider):
                if sl.orientation() == Qt.Orientation.Horizontal:
                    sl.setFixedHeight(16)
                else:
                    sl.setFixedWidth(16)
            # Spin boxes
            for sb in parent_widget.findChildren((QSpinBox, QDoubleSpinBox)):
                sb.setMinimumHeight(22)
                sb.setMaximumHeight(26)
            # Table row height (already set, enforce again to be safe)
            if hasattr(self, 'tf_table') and self.tf_table is not None:
                try:
                    self.tf_table.verticalHeader().setDefaultSectionSize(20)
                except Exception:
                    pass
        except Exception:
            pass

    def on_cmap_changed(self, idx: int):
        # Always reflect preset selection to backend when in Preset mode,
        # because Apply/Reset are hidden in this mode.
        is_preset_mode = (self.tf_mode_combo.currentIndex() == 0)
        try:
            if is_preset_mode and hasattr(self.renderer, 'set_colormap_mode_custom'):
                self.renderer.set_colormap_mode_custom(False)
            if hasattr(self.renderer, 'set_colormap_preset'):
                self.renderer.set_colormap_preset(int(idx))
        except Exception:
            pass
        if is_preset_mode:
            # Keep UI gradient/table in sync with the selected preset
            try:
                self._apply_preset_to_gradient(int(idx))
            except Exception:
                pass

    # --- VTK helpers ---
    def toggle_vtk_panel(self, checked: bool):
        self.vtk_panel.setVisible(checked)
        self.vtk_toggle_btn.setText("VTK Data ▾" if checked else "VTK Data ▸")

    def refresh_vtk_fields(self):
        self.vtk_field_combo.blockSignals(True)
        self.vtk_field_combo.clear()
        try:
            if self.vtk_renderer and hasattr(self.vtk_renderer, 'get_num_fields'):
                n = int(self.vtk_renderer.get_num_fields())
                names = []
                for i in range(n):
                    try:
                        nm = self.vtk_renderer.get_vtk_volume().field_name(i) if hasattr(self.vtk_renderer, 'get_vtk_volume') else f"Field {i}"
                    except Exception:
                        nm = f"Field {i}"
                    names.append(nm if nm else f"Field {i}")
                if names:
                    self.vtk_field_combo.addItems(names)
        except Exception:
            pass
        self.vtk_field_combo.blockSignals(False)

    # --- Transfer Function UI helpers ---
    def toggle_tf_panel(self, checked: bool):
        self.tf_panel.setVisible(checked)
        self.tf_toggle_btn.setText("Colormap / Transfer Function ▾" if checked else "Colormap / Transfer Function ▸")

    def on_tf_mode_changed(self, idx: int):
        # 0 = Preset, 1 = Custom
        use_custom = (idx == 1)
        try:
            if hasattr(self.renderer, 'set_colormap_mode_custom'):
                self.renderer.set_colormap_mode_custom(bool(use_custom))
            # If switching to Preset, immediately apply the current preset selection
            if not use_custom and hasattr(self.renderer, 'set_colormap_preset'):
                self.renderer.set_colormap_preset(int(self.cmap_combo.currentIndex()))
        except Exception:
            pass
        # In Preset mode, immediately sync gradient/table since Apply is hidden
        if not use_custom:
            try:
                self._apply_preset_to_gradient(int(self.cmap_combo.currentIndex()))
            except Exception:
                pass
        # Update visibility of editor/table/buttons based on mode
        self._update_tf_mode_visibility()
        self.gl_widget.update()

    def tf_seed_default(self):
        # A small default set of points similar to your ImGui example
        defaults = [
            (0.00, 0.0, 0.0, 0.0, 0.0),
            (0.30, 0.2, 0.2, 1.0, 0.0),
            (0.50, 1.0, 1.0, 0.2, 0.8),
            (1.00, 1.0, 0.2, 0.2, 1.0),
        ]
        self.tf_table.setRowCount(0)
        for p in defaults:
            self.tf_add_point(values=p)
        self._resize_tf_table_to_contents()
        # Initialize the gradient editor to match the default table
        self._update_gradient_from_table()

    def tf_add_point(self, values=None):
        # QPushButton.clicked(bool) may pass a boolean; treat it as no values provided
        if isinstance(values, bool):
            values = None
        from PyQt6.QtWidgets import QDoubleSpinBox
        row = self.tf_table.rowCount()
        self.tf_table.insertRow(row)
        cols = ["Pos", "R", "G", "B", "A"]
        defaults = (0.5, 1, 1, 1, 1) if values is None else values
        for c, val in enumerate(defaults):
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.01)
            spin.setValue(float(val))
            # Compact spin boxes to avoid horizontal overflow
            spin.setMinimumWidth(50)
            spin.setMaximumWidth(80)
            # When a value changes in the table, update the gradient editor (unless we are already syncing)
            spin.valueChanged.connect(self.on_tf_table_changed)
            self.tf_table.setCellWidget(row, c, spin)
        self._resize_tf_table_to_contents()

    def tf_remove_selected(self):
        rows = sorted({idx.row() for idx in self.tf_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.tf_table.removeRow(r)
        self._resize_tf_table_to_contents()

    def _collect_tf_points(self):
        pts = []
        for r in range(self.tf_table.rowCount()):
            row_vals = []
            for c in range(5):
                w = self.tf_table.cellWidget(r, c)
                if w is None:
                    row_vals.append(0.0)
                else:
                    try:
                        row_vals.append(float(w.value()))
                    except Exception:
                        row_vals.append(0.0)
            pts.append(tuple(row_vals))
        # Sort by position
        pts.sort(key=lambda t: t[0])
        return pts

    def _resize_tf_table_to_contents(self):
        # Compute a fixed height that fits the current rows + header, no scroll
        try:
            # Resize rows to their contents (spin boxes)
            self.tf_table.resizeRowsToContents()
            header_h = self.tf_table.horizontalHeader().height()
            total_rows_h = 0
            for r in range(self.tf_table.rowCount()):
                total_rows_h += self.tf_table.rowHeight(r)
            # Add frame and a small margin to avoid clipping under the buttons
            frame = self.tf_table.frameWidth() * 2
            margin = 8
            total = header_h + total_rows_h + frame + margin
            self.tf_table.setFixedHeight(total)
        except Exception:
            pass

    def tf_apply_custom(self):
        """Apply button handler.
        - If Mode is Preset: apply current preset to renderer and mirror into gradient/table.
        - If Mode is Custom: apply table points to renderer and mirror into gradient (as before).
        """
        mode_is_custom = (self.tf_mode_combo.currentIndex() == 1)
        if not mode_is_custom:
            # Preset mode: apply selected preset and update gradient/table from it
            idx = int(self.cmap_combo.currentIndex())
            try:
                if hasattr(self.renderer, 'set_colormap_mode_custom'):
                    self.renderer.set_colormap_mode_custom(False)
                if hasattr(self.renderer, 'set_colormap_preset'):
                    self.renderer.set_colormap_preset(idx)
            except Exception as e:
                print(f"Python: Preset apply error: {e}")
            # Reflect preset in UI gradient/table
            try:
                self._apply_preset_to_gradient(idx)
            except Exception:
                pass
            self.gl_widget.update()
            return

        # Custom mode: apply TF points to renderer
        pts = self._collect_tf_points()
        if not pts:
            return
        try:
            if hasattr(self.renderer, 'set_colormap_mode_custom'):
                self.renderer.set_colormap_mode_custom(True)
            if hasattr(self.renderer, 'set_transfer_function_points'):
                self.renderer.set_transfer_function_points(pts)
        except Exception as e:
            print(f"Python: TF apply error: {e}")
        # Keep gradient synced from the applied table points
        self._update_gradient_from_table()
        self.gl_widget.update()

    def tf_reset_to_preset(self):
        """Reset colormap to default (Grayscale) and switch to Preset mode.
        Applies to renderer and syncs gradient/table. Hides editor as per Preset mode.
        """
        # Force Mode = Preset
        try:
            if self.tf_mode_combo.currentIndex() != 0:
                self.tf_mode_combo.blockSignals(True)
                self.tf_mode_combo.setCurrentIndex(0)
                self.tf_mode_combo.blockSignals(False)
        except Exception:
            pass
        # Set Preset dropdown to Grayscale (index 0)
        try:
            if self.cmap_combo.currentIndex() != 0:
                self.cmap_combo.blockSignals(True)
                self.cmap_combo.setCurrentIndex(0)
                self.cmap_combo.blockSignals(False)
        except Exception:
            pass
        # Apply to renderer
        try:
            if hasattr(self.renderer, 'set_colormap_mode_custom'):
                self.renderer.set_colormap_mode_custom(False)
            if hasattr(self.renderer, 'set_colormap_preset'):
                self.renderer.set_colormap_preset(0)
        except Exception:
            pass
        # Sync gradient/table to grayscale preset and update visibility
        try:
            self._apply_preset_to_gradient(0)
        except Exception:
            pass
        self._update_tf_mode_visibility()
        self.gl_widget.update()

    def _apply_preset_to_gradient(self, idx: int):
        """Apply the selected preset to the gradient editor and mirror into the table.
        Handles inverted grayscale by reversing tick positions."""
        # Avoid feedback loops: we will drive updates from gradient to table
        # Load pyqtgraph preset
        name = self._pg_preset_map.get(int(idx), 'viridis')
        try:
            self.gradient_editor.loadPreset(name)
        except Exception:
            # fallback: keep existing gradient
            pass
        # If inverted grayscale, reverse the ticks
        if int(idx) == 1:
            try:
                state = self.gradient_editor.saveState()
                ticks = state.get('ticks', [])
                inv_ticks = []
                for pos, rgba in ticks:
                    inv_ticks.append((1.0 - float(pos), rgba))
                inv_ticks.sort(key=lambda t: t[0])
                self.gradient_editor.restoreState({'mode': state.get('mode', 'rgb'), 'ticks': inv_ticks})
            except Exception:
                pass
        # Sync the table from the gradient
        self.on_gradient_changed()

    def _update_tf_mode_visibility(self):
        """Show/hide TF editor and numeric table depending on Mode.
        - Preset: hide gradient editor, hide numeric table, hide Add/Remove.
        - Custom: show gradient editor and table, show Add/Remove, show Custom Preset selector.
        Apply/Reset are visible only in Custom mode.
        """
        try:
            use_custom = (self.tf_mode_combo.currentIndex() == 1)
            if hasattr(self, 'tf_table'):
                self.tf_table.setVisible(use_custom)
            if hasattr(self, 'tf_graphics'):
                self.tf_graphics.setVisible(use_custom)
            if hasattr(self, 'tf_add_btn'):
                self.tf_add_btn.setVisible(use_custom)
            if hasattr(self, 'tf_remove_btn'):
                self.tf_remove_btn.setVisible(use_custom)
            if hasattr(self, 'custom_preset_row'):
                self.custom_preset_row.setVisible(use_custom)
            if hasattr(self, 'preset_row'):
                self.preset_row.setVisible(not use_custom)
            # Apply/Reset: visible only in Custom mode per request
            if hasattr(self, 'tf_apply_btn'):
                self.tf_apply_btn.setVisible(use_custom)
            if hasattr(self, 'tf_reset_btn'):
                self.tf_reset_btn.setVisible(use_custom)
        except Exception:
            pass

    def on_custom_cmap_changed(self, idx: int):
        """When in Custom mode, selecting a custom preset should load its control points
        into the gradient editor and mirror to the table. Does not apply to renderer
        until the user presses Apply."""
        try:
            if self.tf_mode_combo.currentIndex() != 1:
                return  # Only active in Custom mode
            # Look up the pyqtgraph preset key and load it
            if 0 <= idx < len(self._custom_presets):
                _, key = self._custom_presets[idx]
                self.gradient_editor.loadPreset(key)
                # Mirror gradient ticks into table
                self.on_gradient_changed()
        except Exception:
            pass

    # --- Gradient/TF synchronization helpers ---
    def on_gradient_changed(self):
        """When the user edits the gradient editor, update the TF table points."""
        if self._updating_from_table:
            return
        self._updating_from_gradient = True
        try:
            state = self.gradient_editor.saveState()
            ticks = state.get('ticks', [])
            # ticks are (pos, (r,g,b,a)) with 0-255 ints; convert to 0-1 floats
            pts = []
            for pos, rgba in ticks:
                try:
                    r, g, b, a = rgba
                except Exception:
                    # Some versions might give QColor; try to extract
                    try:
                        r = rgba.red()
                        g = rgba.green()
                        b = rgba.blue()
                        a = rgba.alpha()
                    except Exception:
                        r = g = b = a = 255
                pts.append((float(pos), r/255.0, g/255.0, b/255.0, a/255.0))
            # Sort and update the table
            pts.sort(key=lambda t: t[0])
            self.tf_table.setRowCount(0)
            for p in pts:
                self.tf_add_point(values=p)
            self._resize_tf_table_to_contents()
        finally:
            self._updating_from_gradient = False
        # Do not auto-apply to renderer here; user can press Apply or switch to Custom mode

    def _update_gradient_from_table(self):
        """Rebuild gradient ticks from the TF table values and apply to the editor."""
        if self._updating_from_gradient:
            return
        self._updating_from_table = True
        try:
            pts = self._collect_tf_points()
            # Build restoreState-compatible dict
            ticks = []
            for pos, r, g, b, a in pts:
                rr = int(max(0, min(255, round(r * 255))))
                gg = int(max(0, min(255, round(g * 255))))
                bb = int(max(0, min(255, round(b * 255))))
                aa = int(max(0, min(255, round(a * 255))))
                ticks.append((float(pos), (rr, gg, bb, aa)))
            state = {'mode': 'rgb', 'ticks': ticks}
            self.gradient_editor.restoreState(state)
        except Exception:
            pass
        finally:
            self._updating_from_table = False

    def on_tf_table_changed(self, _val=None):
        """When any spin box in the TF table changes, mirror it into the gradient editor."""
        if self._updating_from_gradient:
            return
        self._update_gradient_from_table()

    def on_vtk_field_changed(self, idx: int):
        try:
            if self.vtk_renderer and hasattr(self.vtk_renderer, 'set_current_field_index'):
                self.vtk_renderer.set_current_field_index(int(idx))
                self.gl_widget.update()
        except Exception:
            pass

    def load_vtk_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open VTK File",
            "",
            "VTK Files (*.vtk);;All Files (*)",
        )
        if not path:
            return
        # Show loading status
        try:
            self.gl_widget.show_alert("Loading VTK...", 10000)
        except Exception:
            pass
        if self.vtk_renderer is None:
            try:
                self.vtk_renderer = volumerenderer.VTKRenderer()
            except Exception as e:
                try:
                    self.gl_widget.show_alert(f"Cannot create VTK renderer: {e}", 5000)
                except Exception:
                    pass
                return
        ok = False
        try:
            ok = bool(self.vtk_renderer.load_vtk(path))
        except Exception as e:
            ok = False
        if ok:
            # Switch to VTK mode
            self.switch_to_renderer(self.vtk_renderer, vtk_mode=True)
            # Apply current colormap preset to VTK
            try:
                if hasattr(self.vtk_renderer, 'set_colormap_preset'):
                    self.vtk_renderer.set_colormap_preset(int(self.cmap_combo.currentIndex()))
            except Exception:
                pass
            # Apply bbox state and frame camera to box so it's centered and sized
            try:
                if hasattr(self.vtk_renderer, 'set_show_bounding_box'):
                    self.vtk_renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
                if hasattr(self.vtk_renderer, 'frame_camera_to_box'):
                    self.vtk_renderer.frame_camera_to_box()
                if hasattr(self.vtk_renderer, 'set_bounding_box_scale'):
                    self.vtk_renderer.set_bounding_box_scale(self.bbox_slider.value() / 100.0)
            except Exception:
                pass
            try:
                name = os.path.basename(path)
                self.gl_widget.set_dataset_name(name)
                self.gl_widget.set_dataset_path(path)
            except Exception:
                pass
            # Initialize slicer limits
            self.init_slicer_limits()
            # Populate field names
            self.refresh_vtk_fields()
            # Update view
            self.gl_widget.update()
            # Replace loading alert with success
            try:
                self.gl_widget.show_alert("VTK loaded", 1500)
            except Exception:
                pass
            # Add to history (unique, max 10)
            self.push_history(path)
            # Delayed popup: after 1s, for 3s
            self._notify_loaded(path)
        else:
            try:
                self.gl_widget.show_alert("VTK loading failed", 5000)
            except Exception:
                pass

    def load_file(self):
        # Ask the user whether to load a NIfTI file or a DICOM folder
        choice, ok = QInputDialog.getItem(
            self,
            "Load Data",
            "Select input type",
            ["NIfTI file (.nii/.nii.gz)", "DICOM folder (recursively)"],
            0,
            False,
        )
        if not ok:
            return

        path = ""
        if choice.startswith("NIfTI"):
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Open NIfTI File",
                "",
                "NIfTI Files (*.nii *.nii.gz);;All Files (*)",
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self,
                "Select DICOM Folder",
                "",
                QFileDialog.Option.ShowDirsOnly,
            )

        if not path:
            return

        # Ensure we are in default renderer mode before loading volume
        if self.is_vtk_mode:
            self.switch_to_renderer(self.renderer_default, vtk_mode=False)
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
            try:
                if hasattr(self.renderer, 'set_show_bounding_box'):
                    self.renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
                if hasattr(self.renderer, 'set_colormap_preset'):
                    self.renderer.set_colormap_preset(self.cmap_combo.currentIndex())
            except Exception:
                pass
            # Apply current bbox scale
            self.on_bbox_scale_changed(self.bbox_slider.value())
            # Initialize slicer limits using volume dims
            self.init_slicer_limits()
            self.gl_widget.update()  # Trigger repaint to show bounding box
            # Delayed popup: after 1s, for 3s
            self._notify_loaded(path)
        else:
            print("Python: Load failed.")
            # Show alert banner
            try:
                self.gl_widget.show_alert("Data loading failed", 5000)
            except Exception:
                pass

    def on_bbox_scale_changed(self, slider_value: int):
        scale = max(0.1, min(5.0, slider_value / 100.0))
        # Only supported in default renderer
        try:
            if hasattr(self.renderer, 'set_bounding_box_scale'):
                self.renderer.set_bounding_box_scale(scale)
        except Exception:
            pass
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

        # Apply to renderer explicitly for background color (if supported)
        r, g, b = default_bg
        try:
            if hasattr(self.renderer, 'set_background_color'):
                self.renderer.set_background_color(r, g, b)
        except Exception:
            pass

        # Ensure dependent updates
        self.on_bbox_scale_changed(default_bbox_scale)
        # Reset camera to frame the (unscaled) volume bounding box if supported
        try:
            if hasattr(self.renderer, 'frame_camera_to_box'):
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
        ext = os.path.splitext(path)[1].lower()
        is_vtk = (ext == '.vtk')

        if is_vtk:
            # Ensure VTK renderer exists
            if self.vtk_renderer is None:
                try:
                    self.vtk_renderer = volumerenderer.VTKRenderer()
                except Exception as e:
                    try:
                        self.gl_widget.show_alert(f"Cannot create VTK renderer: {e}", 5000)
                    except Exception:
                        pass
                    return
            # Load VTK
            ok = False
            try:
                ok = bool(self.vtk_renderer.load_vtk(path))
            except Exception:
                ok = False
            if ok:
                # Switch to VTK mode and apply current UI settings
                self.switch_to_renderer(self.vtk_renderer, vtk_mode=True)
                try:
                    if hasattr(self.vtk_renderer, 'set_show_bounding_box'):
                        self.vtk_renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
                    if hasattr(self.vtk_renderer, 'set_colormap_preset'):
                        self.vtk_renderer.set_colormap_preset(int(self.cmap_combo.currentIndex()))
                    if hasattr(self.vtk_renderer, 'set_bounding_box_scale'):
                        self.vtk_renderer.set_bounding_box_scale(self.bbox_slider.value() / 100.0)
                    if hasattr(self.vtk_renderer, 'frame_camera_to_box'):
                        self.vtk_renderer.frame_camera_to_box()
                except Exception:
                    pass
                try:
                    name = os.path.basename(path)
                    self.gl_widget.set_dataset_name(name)
                    self.gl_widget.set_dataset_path(path)
                except Exception:
                    pass
                self.refresh_vtk_fields()
                self.init_slicer_limits()
                self.gl_widget.update()
                # Delayed popup
                self._notify_loaded(path)
            else:
                print("Python: VTK load failed.")
                try:
                    self.gl_widget.show_alert("VTK loading failed", 5000)
                except Exception:
                    pass
        else:
            # Treat as NIfTI (.nii/.nii.gz) or DICOM folder
            # Ensure default renderer is active (supports load_volume)
            if self.is_vtk_mode or not hasattr(self.renderer, 'load_volume'):
                self.switch_to_renderer(self.renderer_default, vtk_mode=False)
            if self.renderer.load_volume(path):
                print("Python: Load successful.")
                try:
                    name = os.path.basename(path)
                    self.gl_widget.set_dataset_name(name)
                    self.gl_widget.set_dataset_path(path)
                except Exception:
                    self.gl_widget.set_dataset_name("")
                # Re-apply current UI state
                try:
                    if hasattr(self.renderer, 'set_show_bounding_box'):
                        self.renderer.set_show_bounding_box(self.bbox_checkbox.isChecked())
                    if hasattr(self.renderer, 'set_colormap_preset'):
                        self.renderer.set_colormap_preset(self.cmap_combo.currentIndex())
                except Exception:
                    pass
                self.on_bbox_scale_changed(self.bbox_slider.value())
                self.init_slicer_limits()
                self.gl_widget.update()
                # Delayed popup
                self._notify_loaded(path)
            else:
                print("Python: Load failed.")
                try:
                    self.gl_widget.show_alert("Data loading failed", 5000)
                except Exception:
                    pass

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
            try:
                if hasattr(self.renderer, 'set_background_color'):
                    self.renderer.set_background_color(r, g, b)
            except Exception:
                pass
            self.gl_widget.update()

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

    def set_overlay_all_visible(self, visible: bool):
        """Toggle visibility of both the GL overlay (FPS/name) and the corner image overlay."""
        try:
            # GL overlay label inside OpenGLWidget
            if hasattr(self.gl_widget, 'set_overlay_visible'):
                self.gl_widget.set_overlay_visible(bool(visible))
        except Exception:
            pass
        try:
            # Corner image overlay label
            if self._bg_image_label is not None:
                self._bg_image_label.setVisible(bool(visible))
        except Exception:
            pass

    def _resize_background_label(self):
        """Place a small faint image at the bottom-left. Scales with window size but stays small."""
        try:
            if not self._bg_image_label:
                return
            cw = self.centralWidget()
            if cw is None:
                return
            rect = cw.rect()
            # Target a small area: ~22% of window width, capped, with 10px margin
            margin = 10
            tgt_w = max(160, int(rect.width() * 0.22))
            tgt_w = min(tgt_w, 320)
            if not self._bg_pix.isNull():
                aspect = self._bg_pix.width() / self._bg_pix.height() if self._bg_pix.height() else 1.0
                tgt_h = int(tgt_w / max(0.1, aspect))
                scaled = self._bg_pix.scaled(tgt_w, tgt_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._bg_image_label.setPixmap(scaled)
                self._bg_image_label.resize(scaled.size())
                # Position at bottom-left with margin
                x = margin
                y = rect.height() - scaled.height() - margin
                self._bg_image_label.move(x, y)
                self._bg_image_label.raise_()
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_background_label()

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

    