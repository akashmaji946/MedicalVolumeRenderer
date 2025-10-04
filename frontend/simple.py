import os
import numpy as np
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QApplication, QFileDialog
import volumerenderer

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

def simple_volume_render(volume_array, axis=0, method='mip'):
    """
    Simple volume renderer using numpy.

    Parameters:
        volume_array: 3D numpy array (depth, height, width)
        axis: axis along which to project (0=depth, 1=height, 2=width)
        method: 'mip' (max intensity projection) or 'sum' (average)
    """
    volume_array = normalize_volume(volume_array)

    if method == 'mip':
        # Max intensity projection along the selected axis
        rendered_image = np.max(volume_array, axis=axis)
    elif method == 'sum':
        # Sum along axis and normalize
        rendered_image = np.sum(volume_array, axis=axis)
        rendered_image = rendered_image / np.max(rendered_image)
    else:
        raise ValueError("method must be 'mip' or 'sum'")

    plt.imshow(rendered_image, cmap='gray')
    plt.title(f"Volume Rendering ({method.upper()}), axis={axis}")
    plt.axis('off')
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

    # 3. Simple volume rendering
    # Try axis=0 (depth), method='mip'
    simple_volume_render(volume_array, axis=0, method='sum')
