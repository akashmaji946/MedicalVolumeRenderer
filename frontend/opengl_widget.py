# frontend/opengl_widget.py

from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtWidgets import QLabel
import shutil
import subprocess
import time

class OpenGLWidget(QOpenGLWidget):
    def __init__(self, renderer, parent=None):
        super().__init__(parent)
        self.renderer = renderer
        self.last_pos = QPoint()
        # FPS tracking
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._base_title = None
        # Drive continuous rendering for FPS updates
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(16)  # ~60 FPS target

        # Small overlay label (dataset name + FPS)
        self.dataset_name = ""
        self.dataset_path = ""
        self.info_label = QLabel(self)
        self.info_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.info_label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(0, 0, 0, 80);   /* very light black */
                color: #7CFC00;                        /* lawn green */
                padding: 4px 6px;                      /* smaller padding */
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;                       /* smaller font */
                font-weight: 200;
            }
            """
        )
        self.info_label.move(10, 10)
        self.info_label.setText("File: -\nFPS: 0.0\nGPU: N/A")
        self.info_label.adjustSize()
        self.info_label.setVisible(True)

        # Alert banner (hidden by default)
        self.alert_label = QLabel(self)
        self.alert_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.alert_label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(200, 20, 20, 200);
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-family: sans-serif;
                font-weight: 400;
            }
            """
        )
        self.alert_label.move(10, 50)
        self.alert_label.setVisible(False)
        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(lambda: self.alert_label.setVisible(False))

    def initializeGL(self):
        """Called once to initialize OpenGL."""
        self.renderer.init()

    def resizeGL(self, w, h):
        """Called whenever the widget is resized."""
        self.renderer.resize(w, h)
        # Keep overlay at top-left
        self.info_label.move(10, 10)
        # If alert is visible, keep it centered on resize
        if hasattr(self, 'alert_label') and self.alert_label.isVisible():
            self._center_alert()

    def paintGL(self):
        """Called whenever the widget needs to be repainted."""
        self.renderer.render()
        # Update FPS once per second in window title
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            fps = self._frame_count / elapsed if elapsed > 0 else 0.0
            self._frame_count = 0
            self._last_fps_time = now
            win = self.window()
            if win is not None:
                if self._base_title is None:
                    self._base_title = win.windowTitle() or "Medical Volume Renderer - v0"
                win.setWindowTitle(f"{self._base_title} - {fps:.1f} FPS.")
            # Update overlay text: File (full path), FPS, GPU
            file_line = self.dataset_path if self.dataset_path else (self.dataset_name if self.dataset_name else "-")
            gpu_line = self._gpu_usage_text()
            self.info_label.setText(f"FILE: {file_line}\nFPS: {fps:.1f}\nGPU: {gpu_line}")
            self.info_label.adjustSize()

    # --- Mouse Event Handlers ---

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()

        if event.buttons() & Qt.MouseButton.LeftButton:
            # Sensitivity factor for rotation
            sensitivity = 0.25
            self.renderer.camera_rotate(dx * sensitivity, dy * sensitivity)
            self.update()  # Trigger a repaint

        self.last_pos = event.pos()

    def wheelEvent(self, event):
        # wheelDelta() is deprecated, use angleDelta()
        delta = event.angleDelta().y() / 120.0  # Usually in steps of 120
        # Sensitivity factor for zoom (faster)
        sensitivity = 1.5
        # Hold Shift to zoom even faster
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            sensitivity *= 2.0
        self.renderer.camera_zoom(delta * sensitivity)
        self.update() # Trigger a repaint

    # --- Helpers ---
    def set_dataset_name(self, name: str):
        self.dataset_name = name or ""
        # Update immediately
        file_line = self.dataset_path if self.dataset_path else (self.dataset_name if self.dataset_name else "-")
        self.info_label.setText(f"File: {file_line}\nFPS: 0.0\nGPU: {self._gpu_usage_text()}")
        self.info_label.adjustSize()

    def set_overlay_visible(self, visible: bool):
        self.info_label.setVisible(bool(visible))

    # --- Captures ---
    def grab_render_image(self):
        """Grab only the OpenGL framebuffer as a QImage (no Qt overlays)."""
        return self.grabFramebuffer()

    def grab_window_image(self):
        """Grab the application window as a QPixmap (includes UI)."""
        win = self.window()
        if win is None:
            return None
        return win.grab()

    def set_dataset_path(self, path: str):
        """Set full dataset path for overlay."""
        self.dataset_path = path or ""
        # Also set name for fallback
        try:
            import os
            self.dataset_name = os.path.basename(path) if path else ""
        except Exception:
            pass
        self.info_label.setText(f"File: {self.dataset_path if self.dataset_path else (self.dataset_name or '-') }\nFPS: 0.0\nGPU: {self._gpu_usage_text()}")
        self.info_label.adjustSize()

    def render_offscreen(self, width: int, height: int):
        """Render the scene offscreen at the requested size and return a QImage.
        This captures ONLY the OpenGL render (no Qt overlays).
        """
        # Ensure GL context is current
        self.makeCurrent()
        # Create FBO
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setAttachment(QOpenGLFramebufferObject.Attachment.Depth)
        fbo = QOpenGLFramebufferObject(width, height, fmt)
        if not fbo.isValid():
            # Fallback to onscreen buffer
            return self.grabFramebuffer()
        # Bind FBO and render
        fbo.bind()
        try:
            # Save current size
            old_w = self.width()
            old_h = self.height()
            # Tell renderer to render at the requested size
            self.renderer.resize(width, height)
            self.renderer.render()
            img = fbo.toImage()
            # Restore renderer size
            self.renderer.resize(old_w, old_h)
        finally:
            fbo.release()
            self.doneCurrent()
        return img

    # --- GPU usage helper ---
    def _gpu_usage_text(self) -> str:
        """Return GPU text as 'X MB [Name YGB]' or 'N/A' if unavailable."""
        info = self._gpu_info()
        if info is None:
            return "N/A"
        used_mb, total_mb, name = info
        total_gb = total_mb / 1024.0 if total_mb else 0.0
        name_str = name if name else "GPU"
        if total_mb:
            return f"{used_mb} MB [{name_str} {total_gb:.0f}GB]"
        return f"{used_mb} MB [{name_str}]"

    def _gpu_info(self):
        """Return (used_mb, total_mb, name) or None."""
        # Try pynvml first (NVIDIA)
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle).decode('utf-8') if hasattr(pynvml, 'nvmlDeviceGetName') else ""
            used_mb = int(mem.used / (1024 * 1024))
            total_mb = int(mem.total / (1024 * 1024))
            pynvml.nvmlShutdown()
            return (used_mb, total_mb, name)
        except Exception:
            pass
        # Fallback: nvidia-smi if available
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.check_output([
                    "nvidia-smi", "--query-gpu=memory.used,memory.total,name", "--format=csv,noheader,nounits"
                ], stderr=subprocess.DEVNULL, text=True, timeout=0.4)
                first = out.strip().splitlines()[0].strip()
                parts = [p.strip() for p in first.split(',')]
                if len(parts) >= 3:
                    used_mb = int(parts[0])
                    total_mb = int(parts[1])
                    name = parts[2]
                    return (used_mb, total_mb, name)
                elif len(parts) >= 2:
                    used_mb = int(parts[0])
                    total_mb = int(parts[1])
                    return (used_mb, total_mb, "")
            except Exception:
                return None
        return None

    # --- Alert banner helpers ---
    def _center_alert(self):
        """Position the alert at the visual center of this widget."""
        # Use contentsRect to account for any frame/borders
        rect = self.contentsRect()
        x = max(0, rect.x() + int((rect.width() - self.alert_label.width()) / 2))
        y = max(0, rect.y() + int((rect.height() - self.alert_label.height()) / 2))
        self.alert_label.move(x, y)

    def show_alert(self, message: str, duration_ms: int = 5000):
        """Show a temporary alert banner over the GL view (centered)."""
        self.alert_label.setText(message)
        self.alert_label.adjustSize()
        self._center_alert()
        # Also recenter on the next event loop cycle to account for any pending layout/resize
        QTimer.singleShot(0, self._center_alert)
        self.alert_label.raise_()
        self.alert_label.setVisible(True)
        self._alert_timer.start(max(0, int(duration_ms)))