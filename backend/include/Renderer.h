// backend/include/Renderer.h

#ifndef RENDERER_H
#define RENDERER_H

#include <glm/glm.hpp>

#include "VolumeData.h"
#include "Camera.h"
#include <string>
#include <memory>
#include "../glad/glad.hpp"

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
    void setupVolumeTexture();
    void setupProxyCube();
    void setupColormapLUT();

    // Controls
    void setShowBoundingBox(bool show);
    void setColormapPreset(int presetIndex);
    void setBackgroundColor(float r, float g, float b);
    void setBoundingBoxScale(float scale);

private:
    std::unique_ptr<VolumeData> m_volumeData;
    // Orbital Camera
    Camera m_camera;
    // OpenGL handles
    unsigned int m_boundingBoxVBO = 0;
    unsigned int m_boundingBoxVAO = 0;
    unsigned int m_shaderProgram = 0;

    // Volume rendering resources
    unsigned int m_volumeTex3D = 0;
    unsigned int m_proxyCubeVAO = 0;
    unsigned int m_proxyCubeVBO = 0;
    unsigned int m_volumeShader = 0;
    unsigned int m_lutTex1D = 0;

    // Defer GL setup until a valid GL context is current (e.g., inside paintGL/render)
    bool m_needsGLSetup = false;

    bool m_showBoundingBox = true;
    int  m_colormapPreset = 0; // 0..9
    glm::vec3 m_bgColor = glm::vec3(0.1f, 0.1f, 0.2f);
    float m_bboxScale = 1.0f;
    bool  m_shouldFrameCameraNext = true;
};

#endif // RENDERER_H