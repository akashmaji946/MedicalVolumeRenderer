import os
import numpy as np
import matplotlib.pyplot as plt
import volumerenderer

BASE_DIR = "../"
NIFTI_DIR = BASE_DIR + "data/nifti-test-data-3.0.2/nifti_regress_data"

def recursively_show(NIFTI_DIR):
    volume_folder = NIFTI_DIR
    volume_files = [os.path.join(volume_folder, f) for f in os.listdir(volume_folder)
                if f.endswith(".nii") or f.endswith(".nii.gz")]  # filter NIfTI files

    # Create renderer instance
    r = volumerenderer.Renderer()
    for volume_file in volume_files:
        # Choose a file
        file_to_load = volume_file
        # Load it
        loaded = r.load_volume(file_to_load)
        if loaded:
            volume_array = r.get_volume_as_numpy()

            # Check shape and type
            print(f"Loaded {file_to_load}")
            print(f"Shape: {volume_array.shape}, dtype: {volume_array.dtype}")

            # Display the middle slice along depth
            middle_slice = volume_array.shape[0] // 2
            plt.imshow(volume_array[middle_slice, :, :], cmap="viridis")
            plt.title(f"{os.path.basename(file_to_load)} - Slice {middle_slice}")
            plt.show()
        else:
            print(f"Failed to load {file_to_load}")
    print("Done")

if __name__ == "__main__":
    recursively_show(NIFTI_DIR)
