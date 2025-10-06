import os
import pydicom
import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
from scipy.ndimage import zoom

def load_dicom_folder_recursive(folder_path):
    # Recursively find all .dcm files
    dicom_files = []
    for root_dir, _, files in os.walk(folder_path):
        for f in files:
            if f.endswith('.dcm'):
                dicom_files.append(os.path.join(root_dir, f))
    
    if not dicom_files:
        raise ValueError("No DICOM files found in folder or subfolders!")

    # Read slices and sort by InstanceNumber (slice order)
    slices = [pydicom.dcmread(f) for f in dicom_files]
    slices.sort(key=lambda s: int(s.InstanceNumber))

    # Print dimensions of each slice
    print("Slice dimensions:")
    for i, s in enumerate(slices):
        print(f"Slice {i} ({s.SOPInstanceUID}): {s.pixel_array.shape}")

    # Find max shape
    max_shape = np.max([s.pixel_array.shape for s in slices], axis=0)

    # Resize all slices to max shape
    resized_slices = []
    for s in slices:
        arr = s.pixel_array
        zoom_factors = (max_shape[0] / arr.shape[0], max_shape[1] / arr.shape[1])
        resized = zoom(arr, zoom_factors, order=1)  # linear interpolation
        resized_slices.append(resized)

    # Stack into 3D array
    volume = np.stack(resized_slices, axis=0)
    return volume

def show_middle_slice(volume):
    z_middle = volume.shape[0] // 2
    plt.imshow(volume[z_middle], cmap='gray')
    plt.title(f'Middle slice (slice {z_middle})')
    plt.axis('off')
    plt.show()

if __name__ == "__main__":
    # Hide main Tk window
    root = Tk()
    root.withdraw()

    # Open folder picker
    folder = filedialog.askdirectory(title="Select DICOM folder")
    if not folder:
        print("No folder selected, exiting.")
        exit()

    volume = load_dicom_folder_recursive(folder)
    print(f"Volume shape: {volume.shape}")
    show_middle_slice(volume)
