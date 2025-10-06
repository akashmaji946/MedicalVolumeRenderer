import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

class GradientTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQtGraph Gradient Editor Test")
        self.setGeometry(200, 200, 800, 150)

        # --- Main Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- Create the Gradient Editor ---
        # The GradientEditorItem must be placed inside a GraphicsLayoutWidget or similar view
        graphics_widget = pg.GraphicsLayoutWidget()
        
        # Instantiate the GradientEditorItem
        self.gradient_editor = pg.GradientEditorItem()
        
        # Load a predefined gradient to start with for a nice visual
        self.gradient_editor.loadPreset('viridis') # [1]

        # Add the editor to the graphics widget
        graphics_widget.addItem(self.gradient_editor)
        
        # Add the graphics widget to our main layout
        layout.addWidget(graphics_widget)

        # --- Connect the Signal ---
        # The sigGradientChanged signal is emitted every time the gradient is modified.[1]
        # We connect this signal to our custom 'gradient_changed' method.
        self.gradient_editor.sigGradientChanged.connect(self.gradient_changed)
        
        # --- Initial Print ---
        # Print the initial state of the gradient when the app starts
        print("--- Initial Gradient State ---")
        self.gradient_changed()

    def gradient_changed(self):
        """
        This method is called every time the gradient is modified by the user.
        It retrieves and prints the gradient's state in different formats.
        """
        print("\n--- Gradient Updated ---")

        # 1. Get the Lookup Table (LUT)
        # This is the most useful format for volume rendering. It samples the gradient
        # at N points and returns a NumPy array of shape (N, 4) for RGBA.
        # Each value is a uint8 from 0-255. [1]
        lookup_table = self.gradient_editor.getLookupTable(10, alpha=True)
        print(f"1. Lookup Table (10 samples):\n{lookup_table}\n")

        # 2. Get the Raw State
        # This returns a dictionary containing the exact positions and colors of the ticks.
        # This is useful for saving/loading the exact state of the editor. [1]
        state = self.gradient_editor.saveState()
        print("2. Raw State Dictionary:")
        # The 'ticks' key holds a list of tuples: (position, (R, G, B, A))
        for pos, color in state['ticks']:
            print(f"   - Position: {pos:.2f}, Color (RGBA): {color}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GradientTestWindow()
    window.show()
    sys.exit(app.exec())