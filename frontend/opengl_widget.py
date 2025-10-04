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
                background-color: rgba(0, 0, 0, 140);
                color: white;
                padding: 6px 8px;
                border-radius: 6px;
                font-family: monospace;
            }
            """
        )
        self.info_label.move(10, 10)
        self.info_label.setText("File: -\nFPS: 0.0\nGPU: N/A")
        self.info_label.adjustSize()
        self.info_label.setVisible(True)

    def initializeGL(self):
        """Called once to initialize OpenGL."""
        self.renderer.init()

    def resizeGL(self, w, h):
        """Called whenever the widget is resized."""
        self.renderer.resize(w, h)
        # Keep overlay at top-left
        self.info_label.move(10, 10)

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
                    self._base_title = win.windowTitle() or "Medical Volume Renderer"
                win.setWindowTitle(f"{self._base_title} - {fps:.1f} FPS")
            # Update overlay text: File, FPS, GPU
            file_line = self.dataset_path if self.dataset_path else (self.dataset_name if self.dataset_name else "-")
            gpu_line = self._gpu_usage_text()
            self.info_label.setText(f"File: {file_line}\nFPS: {fps:.1f}\nGPU: {gpu_line}")
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
        file_line = self.dataset_name if self.dataset_name else "-"
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
        """Return GPU memory used in MB (best-effort)."""
        # Try pynvml first
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used_mb = int(mem.used / (1024 * 1024))
            pynvml.nvmlShutdown()
            return f"{used_mb} MB"
        except Exception:
            pass
        # Fallback: nvidia-smi if available
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.check_output([
                    "nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"
                ], stderr=subprocess.DEVNULL, text=True, timeout=0.2)
                first = out.strip().splitlines()[0].strip()
                used_mb = int(first)
                return f"{used_mb} MB"
            except Exception:
                return "N/A"
        return "N/A"