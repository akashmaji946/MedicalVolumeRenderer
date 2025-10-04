//
// Created by akashmaji on 10/4/25.
//

// backend/include/Renderer.h

#ifndef RENDERER_H
#define RENDERER_H

#include "VolumeData.h"
#include <string>
#include <memory> // For std::unique_ptr

/**
 * @class Renderer
 * @brief Manages the core state and operations of the volume rendering engine.
 *
 * This class acts as the main interface for the C++ backend. It holds the
 * volume data, camera, and other rendering parameters. Its methods will be
 * exposed to Python via pybind11.
 */
class Renderer {
public:
    // Constructor
    Renderer();

    /**
     * @brief Loads a medical volume from a given path.
     *
     * This method intelligently determines whether the path is a directory
     * (for DICOM series) or a file (for NIfTI) and calls the appropriate loader.
     *
     * @param path The file path to the NIfTI file or the directory path for a DICOM series.
     * @return true if loading was successful, false otherwise.
     */
    bool loadVolume(const std::string& path);

public:
    VolumeData* getVolumeData() const { return m_volumeData.get(); }

private:
    // Using a smart pointer to manage the VolumeData object's lifetime.
    std::unique_ptr<VolumeData> m_volumeData;

    // In the future, other state variables will go here:
    // Camera m_camera;
    // TransferFunction m_transferFunction;
};

#endif // RENDERER_H