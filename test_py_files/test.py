import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Make sure Python can find your compiled module
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "build"))
if module_path not in sys.path:
    sys.path.insert(0, module_path)

import volumerenderer  # your compiled Python binding

BASE_DIR = "../"
nifti_file = BASE_DIR + "data/nifti-test-data-3.0.2/nifti_regress_data/anat0.nii"

# -----------------------------
# 1. Load a NIfTI file
# -----------------------------

# volume_data = None
# try:
#     r = volumerenderer.Renderer()
#     loaded = r.load_volume(nifti_file)
#     if loaded:
#         volume_data = r.get_volume_as_numpy()
#
# except Exception as e:
#     print(f"Error loading NIfTI: {e}")
#     sys.exit(1)
#
# print(f"Loaded volume with shape: {volume_data.shape}")
#
# # -----------------------------
# # 2. Select a middle slice (axial)
# # -----------------------------
# z_mid = volume_data.shape[2] // 2
# slice_data = volume_data[:, :, z_mid]
#
# # -----------------------------
# # 3. Display using matplotlib
# # -----------------------------
# plt.figure(figsize=(6,6))
# plt.imshow(slice_data.T, cmap="gray", origin="lower")
# plt.title(f"Middle Axial Slice (Z={z_mid})")
# plt.axis("off")
# plt.show()




# 1. Create the renderer and load the volume data
r = volumerenderer.Renderer()
was_loaded = r.load_volume(nifti_file)

if was_loaded:
    # 2. Get the data as a NumPy array
    # This call returns a standard numpy.ndarray
    volume_array = r.get_volume_as_numpy()

    # 3. Access the data just like any other NumPy array
    print(f"Data type received in Python: {volume_array.dtype}")
    print(f"Shape of the volume: {volume_array.shape}")

    # You can perform any NumPy operation, for example, finding the max intensity
    max_intensity = np.max(volume_array)
    print(f"Maximum voxel intensity: {max_intensity}")

    # 4. Slice the array to get a single 2D image
    # For example, get the middle slice along the first axis (depth)
    middle_slice_index = volume_array.shape[0] // 2
    slice_2d = volume_array[middle_slice_index, :, :]

    print(f"Shape of the extracted 2D slice: {slice_2d.shape}")

    # 5. Use the data with any other Python library that accepts NumPy arrays
    plt.imshow(slice_2d, cmap='gray')
    plt.title(f"Displaying Slice #{middle_slice_index}")
    plt.show()
