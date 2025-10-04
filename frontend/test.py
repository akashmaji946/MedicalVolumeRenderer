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

# -----------------------------
# 1. Load a NIfTI file
# -----------------------------
nifti_file = BASE_DIR + "data/nifti-test-data-3.0.2/nifti_regress_data/anat0.nii"

try:
    r = volumerenderer.Renderer()
    volume_data = r.load_volume(nifti_file)

except Exception as e:
    print(f"Error loading NIfTI: {e}")
    sys.exit(1)

print(f"Loaded volume with shape: {volume_data.shape}")

# -----------------------------
# 2. Select a middle slice (axial)
# -----------------------------
z_mid = volume_data.shape[2] // 2
slice_data = volume_data[:, :, z_mid]

# -----------------------------
# 3. Display using matplotlib
# -----------------------------
plt.figure(figsize=(6,6))
plt.imshow(slice_data.T, cmap="gray", origin="lower")
plt.title(f"Middle Axial Slice (Z={z_mid})")
plt.axis("off")
plt.show()
