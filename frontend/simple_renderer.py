import numpy as np
import pyvista as pv
import volumerenderer
from PySide6.QtWidgets import QApplication, QFileDialog

def browse_volume_file():
    """Open a file dialog to pick a volume file."""
    app = QApplication([])
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select a NIfTI volume",
        "",
        "NIfTI files (*.nii *.nii.gz)"
    )
    return file_path

def normalize_volume(volume):
    """Normalize volume data to 0-1."""
    max_val = np.max(volume)
    if max_val > 0:
        return volume / max_val
    return volume

if __name__ == "__main__":
    # 1. Pick a NIfTI file
    nifti_file = browse_volume_file()
    if not nifti_file:
        print("No file selected. Exiting.")
        exit(0)

    # 2. Load volume via Renderer
    r = volumerenderer.Renderer()
    if not r.load_volume(nifti_file):
        print(f"Failed to load {nifti_file}")
        exit(1)

    volume_array = r.get_volume_as_numpy()
    print(f"Volume shape: {volume_array.shape}, dtype: {volume_array.dtype}")

    # 3. Normalize for rendering
    volume_array = normalize_volume(volume_array)

    # 4. Create PyVista ImageData for 3D volume rendering
    depth, height, width = volume_array.shape
    grid = pv.ImageData()
    grid.dimensions = np.array(volume_array.shape) + 1
    grid.spacing = (1, 1, 1)
    grid.origin = (0, 0, 0)
    grid.cell_data["values"] = volume_array.flatten(order="F")

    # 5. Initialize PyVista plotter
    p = pv.Plotter()

    # Add volume with a colormap
    p.add_volume(
        grid,
        scalars="values",
        opacity="sigmoid",  # Sigmoid for depth perception
        cmap="viridis",     # You can change to "plasma", "magma", "gray", etc.
        shade=True
    )

    # Add XYZ axes (like camera reference)
    p.show_axes()  # Shows small XYZ axes in the corner

    # Set background color (optional)
    p.set_background("white")

    # 6. Enable interactive rotation/zoom
    p.show()
