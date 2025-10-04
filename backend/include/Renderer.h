// backend/include/Renderer.h

#ifndef RENDERER_H
#define RENDERER_H

#include "VolumeData.h"
#include "Camera.h"
#include <string>
#include <memory>

class Renderer {
public:
    Renderer();

    // load and get volume data
    bool loadVolume(const std::string& path);
    VolumeData* getVolume();

    // lightweight getters for metadata
    bool isVolumeLoaded() const;
    unsigned int getVolumeWidth() const;
    unsigned int getVolumeHeight() const;
    unsigned int getVolumeDepth() const;
    double getVolumeSpacingX() const;
    double getVolumeSpacingY() const;
    double getVolumeSpacingZ() const;

    // --- Core OpenGL Methods ---
    void init();
    void render();
    void resize(int width, int height);

    // --- Camera Control ---
    void camera_rotate(float dx, float dy);
    void camera_zoom(float delta);


    void setupBoundingBox();

private:
    std::unique_ptr<VolumeData> m_volumeData;
    // Orbital Camera
    Camera m_camera;
    // OpenGL handles
    unsigned int m_boundingBoxVBO = 0;
    unsigned int m_boundingBoxVAO = 0;
    unsigned int m_shaderProgram = 0;
};

#endif // RENDERER_H