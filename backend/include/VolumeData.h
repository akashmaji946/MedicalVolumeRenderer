//
// Created by akashmaji on 10/4/25.
//

// backend/include/VolumeData.h

#ifndef VOLUMEDATA_H
#define VOLUMEDATA_H

#include <vector>
#include <cstdint> // For standard integer types like uint16_t

// A simple container for 3D volumetric data.
// This class stores the dimensions, voxel spacing, and the raw voxel data
// in a contiguous block of memory.
class VolumeData {
public:
    // Dimensions of the volume in number of voxels.
    unsigned int width = 0;
    unsigned int height = 0;
    unsigned int depth = 0;

    // Physical spacing of the voxels in millimeters.
    double spacing_x = 1.0;
    double spacing_y = 1.0;
    double spacing_z = 1.0;

    // Raw voxel data. We use unsigned short (uint16_t) as it's a common
    // format for medical imaging data (e.g., 12-bit CT data is often
    // stored in 16-bit integers).
    std::vector<uint16_t> data;

    // Default constructor
    VolumeData() = default;

    // Clears all data, resetting the object to its initial state.
    void clear() {
        width = 0;
        height = 0;
        depth = 0;
        spacing_x = 1.0;
        spacing_y = 1.0;
        spacing_z = 1.0;
        data.clear();
    }
};

#endif // VOLUMEDATA_H