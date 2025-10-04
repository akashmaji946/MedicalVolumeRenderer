//
// Created by akashmaji on 10/4/25.
//

// backend/src/NIFTILoader.cpp

#include "../include/DataLoader.h"
#include "../include/VolumeData.h"
#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdint>

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

    // 2. Read and convert data into uint16_t buffer with normalization.
    if (!nim->data) {
        std::cerr << "      MVR Error: NIfTI file contains no pixel data." << std::endl;
        nifti_image_free(nim);
        return false;
    }

    const size_t num_voxels = static_cast<size_t>(nim->nvox);
    volumeData.data.resize(num_voxels);

    // Helper lambdas
    auto apply_slope_inter = [&](double v) -> double {
        double slope = (nim->scl_slope == 0.0) ? 1.0 : nim->scl_slope;
        double inter = nim->scl_inter;
        return v * slope + inter;
    };

    auto normalize_to_u16 = [&](const std::vector<double>& src){
        if (src.empty()) return;
        auto [minIt, maxIt] = std::minmax_element(src.begin(), src.end());
        double mn = *minIt, mx = *maxIt;
        if (mx <= mn) {
            std::fill(volumeData.data.begin(), volumeData.data.end(), 0);
            return;
        }
        const double scale = 65535.0 / (mx - mn);
        for (size_t i = 0; i < num_voxels; ++i) {
            double v = (src[i] - mn) * scale;
            if (v < 0.0) v = 0.0; else if (v > 65535.0) v = 65535.0;
            volumeData.data[i] = static_cast<uint16_t>(v + 0.5);
        }
    };

    switch (nim->datatype) {
        case NIFTI_TYPE_UINT16: {
            const uint16_t* ptr = static_cast<uint16_t*>(nim->data);
            std::copy(ptr, ptr + num_voxels, volumeData.data.begin());
            break;
        }
        case NIFTI_TYPE_INT16: {
            const int16_t* ptr = static_cast<int16_t*>(nim->data);
            std::vector<double> tmp(num_voxels);
            for (size_t i = 0; i < num_voxels; ++i) tmp[i] = apply_slope_inter(static_cast<double>(ptr[i]));
            normalize_to_u16(tmp);
            break;
        }
        case NIFTI_TYPE_UINT8: {
            const uint8_t* ptr = static_cast<uint8_t*>(nim->data);
            // Expand 8-bit to 16-bit
            for (size_t i = 0; i < num_voxels; ++i) volumeData.data[i] = static_cast<uint16_t>(ptr[i]) * 257u;
            break;
        }
        case NIFTI_TYPE_FLOAT32: {
            const float* ptr = static_cast<float*>(nim->data);
            std::vector<double> tmp(num_voxels);
            for (size_t i = 0; i < num_voxels; ++i) tmp[i] = apply_slope_inter(static_cast<double>(ptr[i]));
            normalize_to_u16(tmp);
            break;
        }
        case NIFTI_TYPE_FLOAT64: {
            const double* ptr = static_cast<double*>(nim->data);
            std::vector<double> tmp(num_voxels);
            for (size_t i = 0; i < num_voxels; ++i) tmp[i] = apply_slope_inter(ptr[i]);
            normalize_to_u16(tmp);
            break;
        }
        default: {
            std::cerr << "      MVR Warning: Unsupported NIfTI datatype (code " << nim->datatype << "), normalizing as bytes." << std::endl;
            const uint8_t* ptr = static_cast<uint8_t*>(nim->data);
            for (size_t i = 0; i < num_voxels; ++i) volumeData.data[i] = static_cast<uint16_t>(ptr[i]) * 257u;
            break;
        }
    }

    // 3. Clean up by freeing the nifti_image struct.
    nifti_image_free(nim);

    std::cout << "      MVR Info: Loaded NIfTI volume: " << volumeData.width << "x" << volumeData.height << "x" << volumeData.depth << std::endl;
    return true;
}

} // namespace DataLoader