// backend/include/VTKVolumeData.h
#pragma once

#include <string>
#include <vector>

struct VTKVec3i { int x{0}, y{0}, z{0}; };
struct VTKVec3f { float x{1.f}, y{1.f}, z{1.f}; };

// VTK volume that can contain multiple scalar fields (each a 3D dataset)
struct VTKVolumeData {
    VTKVec3i dimensions{};   // voxels
    VTKVec3f spacing{1.f,1.f,1.f};
    VTKVec3f origin{0.f,0.f,0.f};

    struct Field {
        std::string name;           // field name
        std::vector<float> data;    // size = dims.x * dims.y * dims.z (normalized to [0,1])
        float minVal{0.f};          // original min
        float maxVal{1.f};          // original max
    };

    std::vector<Field> fields;      // one or more scalar fields

    bool empty() const {
        return fields.empty() || dimensions.x == 0 || dimensions.y == 0 || dimensions.z == 0;
    }

    size_t voxelCount() const {
        return static_cast<size_t>(dimensions.x) * dimensions.y * dimensions.z;
    }
};
