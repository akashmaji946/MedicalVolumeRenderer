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
    void set_camera_angles(float azimuthDeg, float elevationDeg);


    void setupBoundingBox();
    void setupVolumeTexture();
    void setupProxyCube();
    void setupFullscreenQuad();
    void setupColormapLUT();

    // Controls
    void setShowBoundingBox(bool show);
    void setColormapPreset(int presetIndex);
    // Transfer function (custom colormap)
    void setColormapModeCustom(bool useCustom);
    struct TFPoint { float position; float r; float g; float b; float a; };
    void setTransferFunctionPoints(const std::vector<TFPoint>& points);
    void setBackgroundColor(float r, float g, float b);
    void setBoundingBoxScale(float scale);
    void frameCameraToBox();
    // Slicer controls
    void setSliceMode(bool enabled);
    void setSliceAxis(int axis);     // 0=Z,1=Y,2=X
    void setSliceIndex(int index);

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
    unsigned int m_fullscreenQuadVAO = 0;
    unsigned int m_fullscreenQuadVBO = 0;
    unsigned int m_volumeShader = 0;
    unsigned int m_lutTex1D = 0;
    // Slicer resources
    unsigned int m_sliceShader = 0;
    unsigned int m_sliceVAO = 0;
    unsigned int m_sliceVBO = 0;

    // Defer GL setup until a valid GL context is current (e.g., inside paintGL/render)
    bool m_needsGLSetup = false;

    bool m_showBoundingBox = true;
    int  m_colormapPreset = 0; // 0..9
    bool m_useCustomTF = false;
    std::vector<TFPoint> m_tfPoints; // positions in [0,1], colors RGBA in [0,1]
    glm::vec3 m_bgColor = glm::vec3(0.1f, 0.1f, 0.2f);
    float m_bboxScale = 1.0f;
    bool  m_shouldFrameCameraNext = true;

    // Slicer state
    bool  m_sliceMode = false;
    int   m_sliceAxis = 0; // 0=Z,1=Y,2=X
    int   m_sliceIndex = 0;
};

#endif // RENDERER_H