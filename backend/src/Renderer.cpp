// backend/src/Renderer.cpp

#include "../include/Renderer.h"
#include "../include/DataLoader.h"
#include <filesystem>
#include <iostream>

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/type_ptr.hpp>

namespace fs = std::filesystem;

Renderer::Renderer() {
    m_volumeData = std::make_unique<VolumeData>();
}

bool Renderer::loadVolume(const std::string& path) {
    //... (this function remains the same)
    std::cout << "      MVR INFO: Attempting to load volume from path: " << path << std::endl;

    if (!fs::exists(path)) {
        std::cerr << "      MVR ERROR: Path does not exist: " << path << std::endl;
        return false;
    }

    m_volumeData->clear();

    bool success = false;
    if (fs::is_directory(path)) {
        std::cout << "      MVR INFO: Path is a directory, attempting to load as DICOM series." << std::endl;
        success = DataLoader::loadDICOM(path, *m_volumeData);
    } else if (fs::is_regular_file(path)) {
        std::cout << "      MVR INFO: Path is a file, attempting to load." << std::endl;
        std::string extension = fs::path(path).extension().string();
        if (extension == ".nii" || extension == ".gz") {
            success = DataLoader::loadNIFTI(path, *m_volumeData);
        } else {
            std::cerr << "      MVR ERROR: Unsupported file type: " << extension << std::endl;
        }
    } else {
        std::cerr << "      MVR ERROR: Path is not a regular file or directory." << std::endl;
    }

    if (success) {
        std::cout << "      MVR INFO: Volume loaded successfully." << std::endl;
    } else {
        std::cerr << "      MVR ERROR: Failed to load volume." << std::endl;
    }

    return success;
}

// --- New Lightweight Getter Implementations ---

bool Renderer::isVolumeLoaded() const {
    return m_volumeData && m_volumeData->width > 0;
}

unsigned int Renderer::getVolumeWidth() const {
    return isVolumeLoaded()? m_volumeData->width : 0;
}

unsigned int Renderer::getVolumeHeight() const {
    return isVolumeLoaded()? m_volumeData->height : 0;
}

unsigned int Renderer::getVolumeDepth() const {
    return isVolumeLoaded()? m_volumeData->depth : 0;
}

double Renderer::getVolumeSpacingX() const {
    return isVolumeLoaded()? m_volumeData->spacing_x : 0.0;
}

double Renderer::getVolumeSpacingY() const {
    return isVolumeLoaded()? m_volumeData->spacing_y : 0.0;
}

double Renderer::getVolumeSpacingZ() const {
    return isVolumeLoaded()? m_volumeData->spacing_z : 0.0;
}

VolumeData* Renderer::getVolume() {
    return m_volumeData.get();
}
