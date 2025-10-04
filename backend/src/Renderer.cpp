//
// Created by akashmaji on 10/4/25.
//

// backend/src/Renderer.cpp

#include "../include/Renderer.h"
#include "../include/DataLoader.h"
#include <filesystem> // For checking if a path is a directory
#include <iostream>

// C++17 standard library for filesystem operations
namespace fs = std::filesystem;

Renderer::Renderer() {
    // Initialize the VolumeData object
    m_volumeData = std::make_unique<VolumeData>();
}

bool Renderer::loadVolume(const std::string& path) {
    std::cout << "C++: Attempting to load volume from path: " << path << std::endl;

    if (!fs::exists(path)) {
        std::cerr << "Error: Path does not exist: " << path << std::endl;
        return false;
    }

    // Clear any previously loaded data
    m_volumeData->clear();

    bool success = false;
    if (fs::is_directory(path)) {
        std::cout << "Path is a directory, attempting to load as DICOM series." << std::endl;
        success = DataLoader::loadDICOM(path, *m_volumeData);
    } else if (fs::is_regular_file(path)) {
        std::cout << "Path is a file, attempting to load as NIfTI." << std::endl;
        std::string extension = fs::path(path).extension().string();
        // Simple check for NIfTI extensions
        if (extension == ".nii" || extension == ".gz") {
            success = DataLoader::loadNIFTI(path, *m_volumeData);
} else {
    std::cerr << "Error: Unsupported file type: " << extension << std::endl;
}
    } else {
        std::cerr << "Error: Path is not a regular file or directory." << std::endl;
    }

    if (success) {
        std::cout << "C++: Volume loaded successfully." << std::endl;
    } else {
        std::cerr << "C++: Failed to load volume." << std::endl;
    }

    return success;
}

