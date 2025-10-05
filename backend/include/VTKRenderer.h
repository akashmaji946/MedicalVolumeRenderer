// backend/include/VTKRenderer.h
#pragma once

#include <string>
#include <memory>
#include <vector>

#include "VTKVolumeData.h"
#include "Camera.h"
#include "../glad/glad.hpp"
#include <glm/glm.hpp>

class VTKRenderer {
public:
    VTKRenderer();

    // Load an ASCII VTK structured points/structured grid scalar volume
    bool loadVTK(const std::string& filename);

    // GL lifecycle
    void init();
    void render();
    void resize(int width, int height);

    // Camera
    void camera_rotate(float dx, float dy);
    void camera_zoom(float delta);
    void set_camera_angles(float azimuthDeg, float elevationDeg);

    // Slicer controls (same semantics as Renderer: 0=Z,1=Y,2=X)
    void setSliceMode(bool enabled);
    void setSliceAxis(int axis);
    void setSliceIndex(int index);

    // Field selection
    int  getNumFields() const;
    int  getCurrentFieldIndex() const;
    void setCurrentFieldIndex(int idx);

    // Accessors
    bool isVolumeLoaded() const;
    VTKVolumeData* getVTKVolume();

    // Lightweight getters
    unsigned int getVolumeWidth() const;
    unsigned int getVolumeHeight() const;
    unsigned int getVolumeDepth() const;
    float getSpacingX() const; 
    float getSpacingY() const; 
    float getSpacingZ() const; 

    // Colormap preset (0..9) same mapping as default Renderer
    void setColormapPreset(int presetIndex);
    // Transfer function (custom colormap)
    struct TFPoint { float position; float r; float g; float b; float a; };
    void setColormapModeCustom(bool useCustom);
    void setTransferFunctionPoints(const std::vector<TFPoint>& points);

    // Match default Renderer API bits for UI parity
    void setShowBoundingBox(bool show);
    void frameCameraToBox();
    void setBoundingBoxScale(float scale);

private:
    void setupVolumeTexture();
    void setupFullscreenQuad();
    void setupBoundingBox();
    void setupColormapLUT();

    std::unique_ptr<VTKVolumeData> m_volume;
    int m_currentField{0};

    // GL handles (reuse same names to share shader logic)
    unsigned int m_volumeTex3D = 0;
    unsigned int m_fullscreenQuadVAO = 0;
    unsigned int m_fullscreenQuadVBO = 0;
    unsigned int m_volumeShader = 0;
    unsigned int m_sliceShader = 0;
    unsigned int m_sliceVAO = 0;
    unsigned int m_sliceVBO = 0;
    unsigned int m_lutTex1D = 0;
    unsigned int m_boundingBoxVAO = 0;
    unsigned int m_boundingBoxVBO = 0;
    unsigned int m_bboxProgram = 0;

    // State
    Camera m_camera;
    bool m_needsGLSetup = false;
    bool m_sliceMode = false;
    int  m_sliceAxis = 0; // 0=Z,1=Y,2=X
    int  m_sliceIndex = 0;
    glm::vec3 m_bgColor{0.1f, 0.1f, 0.2f};
    int m_colormapPreset{0};
    bool m_showBoundingBox{true};
    float m_bboxScale{1.0f};
    bool m_useCustomTF{false};
    std::vector<TFPoint> m_tfPoints;
};
