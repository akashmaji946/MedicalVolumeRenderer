//
// Created by akashmaji on 10/4/25.
//

// backend/src/NIFTILoader.cpp

#include "../include/DataLoader.h"
#include "../include/VolumeData.h"
#include <iostream>
#include <vector>

// nifti_clib includes
extern "C" {
    #include "../extern/nifti_clib/niftilib/nifti1_io.h"
    // #include "nifti1_io.h"
}

namespace DataLoader {

bool loadNIFTI(const std::string& filePath, VolumeData& volumeData) {
    volumeData.clear();

    // Read the NIfTI image. The second argument '1' means to read the data blob.
    nifti_image* nim = nifti_image_read(filePath.c_str(), 1);
    if (!nim) {
        std::cerr << "      MVR Error: Failed to read NIfTI file: " << filePath << std::endl;
        return false;
    }

    // Check if the image is 3D
    if (nim->dim[0] < 3) {
        std::cerr << "      MVR Error: NIfTI file is not a 3D volume." << std::endl;
        nifti_image_free(nim);
        return false;
    }

    // 1. Extract dimensions and spacing from the header.
    volumeData.width = nim->nx;
    volumeData.height = nim->ny;
    volumeData.depth = nim->nz;

    volumeData.spacing_x = nim->dx;
    volumeData.spacing_y = nim->dy;
    volumeData.spacing_z = nim->dz;

    // 2. Check data type and copy pixel data.
    // This example assumes the data is 16-bit unsigned integers.
    // A more robust implementation would handle different data types.
    if (nim->datatype!= NIFTI_TYPE_UINT16) {
        std::cerr << "      MVR Warning: NIfTI data type is not UINT16. Attempting to cast." << std::endl;
        // In a real application, you would handle different types properly.
    }

    const uint16_t* nifti_data = static_cast<uint16_t*>(nim->data);
    if (!nifti_data) {
        std::cerr << "      MVR Error: NIfTI file contains no pixel data." << std::endl;
        nifti_image_free(nim);
        return false;
    }

    size_t num_voxels = nim->nvox;
    volumeData.data.resize(num_voxels);
    std::copy(nifti_data, nifti_data + num_voxels, volumeData.data.begin());

    // 3. Clean up by freeing the nifti_image struct.
    nifti_image_free(nim);

    std::cout << "      MVR Info: Loaded NIfTI volume: " << volumeData.width << "x" << volumeData.height << "x" << volumeData.depth << std::endl;
    return true;
}

} // namespace DataLoader