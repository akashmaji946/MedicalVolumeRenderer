import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from PySide6.QtWidgets import QApplication, QFileDialog
import volumerenderer

def browse_volume_file():
    """Open a file dialog to pick a volume file."""
    app = QApplication([])
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select a NIfTI volume data file",
        "",
        "NIfTI files (*.nii *.nii.gz)"
    )
    return file_path

def normalize_slice(slice_2d):
    """Normalize slice data to 0-1 for display."""
    if np.max(slice_2d) > 0:
        return slice_2d / np.max(slice_2d)
    return slice_2d

def view_volume(volume_array):
    """Display interactive slice viewer for a 3D volume."""
    # Start with the first axis (depth)
    axis = 0
    max_index = volume_array.shape[axis] - 1
    current_index = max_index // 2

    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.25)

    slice_img = ax.imshow(normalize_slice(volume_array[current_index, :, :]), cmap='gray')
    ax.set_title(f"Slice {current_index} / {max_index}")

    # Slider to scroll through slices
    axslice = plt.axes([0.25, 0.1, 0.65, 0.03])
    slider = Slider(axslice, 'Slice', 0, max_index, valinit=current_index, valstep=1)

    def update(val):
        idx = int(slider.val)
        slice_img.set_data(normalize_slice(volume_array[idx, :, :]))
        ax.set_title(f"Slice {idx} / {max_index}")
        fig.canvas.draw_idle()

    slider.on_changed(update)
    plt.show()

if __name__ == "__main__":
    # 1. Browse for a file
    nifti_file = browse_volume_file()
    if not nifti_file:
        print("No file selected. Exiting.")
        exit(0)

    # 2. Load volume using Renderer
    r = volumerenderer.Renderer()
    if not r.load_volume(nifti_file):
        print(f"Failed to load {nifti_file}")
        exit(1)

    volume_array = r.get_volume_as_numpy()
    print(f"Loaded {nifti_file} with shape {volume_array.shape} and dtype {volume_array.dtype}")

    # 3. Open interactive viewer
    view_volume(volume_array)
