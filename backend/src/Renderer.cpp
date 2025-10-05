// backend/src/Renderer.cpp

#include "../include/Renderer.h"
#include "../include/DataLoader.h"
#include <filesystem>
#include <iostream>
#include <fstream>
#include <sstream>

#include "../glad/glad.hpp"
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/type_ptr.hpp>

#include "../include/tinycolormap.h"

namespace fs = std::filesystem;

// Fallback for SHADERS_DIR if not provided by the build system
#ifndef SHADERS_DIR
    #define SHADERS_DIR "../shaders"
#endif

// Helper to load shader source from file under SHADERS_DIR
static std::string loadShaderFile(const char* filename) {
    std::string fullPath = std::string(SHADERS_DIR) + "/" + filename;
    std::ifstream file(fullPath);
    if (!file.is_open()) {
        std::cerr << "[Renderer::loadShaderFile] ERROR: Cannot open shader file: " << fullPath << std::endl;
        return std::string();
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// --- Slicer setters (keep outside of loadShaderFile) ---
void Renderer::setSliceMode(bool enabled) { 
    m_sliceMode = enabled; 
}
void Renderer::setSliceAxis(int axis)  { 
    m_sliceAxis = (axis<0 ? 0 : (axis>2 ? 2 : axis)); 
}
void Renderer::setSliceIndex(int index){ 
    m_sliceIndex = index; 
}

Renderer::Renderer() {
    m_volumeData = std::make_unique<VolumeData>();
}


void Renderer::init() {
    // Initialize GL loader (GLAD).
    // In Qt, the context is current when this is called, so glad can query via system loader.
    // If this fails, nothing will render.
    if (!gladLoadGL()) {
        std::cerr << "  [Renderer::init ] ERROR: Failed to initialize GLAD. OpenGL functions unavailable." << std::endl;
        return;
    }

    #include <iostream>

    // std::cout << R"(
    // ____________________________
    // __  __  __      __  _____  
    // |  \/  | \ \    / / |  __ \ 
    // | |\/| |  \ \  / /  | |__) |
    // | |  | |   \ \/ /   |  _  / 
    // |_|  |_|    \__/    |_| \_\ 
    // MVR - Medical Volume Renderer
    // ____________________________
    // )" << std::endl;

    std::cout << "  [Renderer::init ] OpenGL version: " << glGetString(GL_VERSION) << std::endl;
    std::cout << "  [Renderer::init ] GLSL version: " << glGetString(GL_SHADING_LANGUAGE_VERSION) << std::endl;
    std::cout << "  [Renderer::init ] Vendor: " << glGetString(GL_VENDOR) << std::endl;
    std::cout << "  [Renderer::init ] Renderer: " << glGetString(GL_RENDERER) << std::endl;
    std::cout << std::endl;
    // --- Compile Shaders --- (bounding box)
    std::string bboxVSsrc = loadShaderFile("bbox.vert");
    std::string bboxFSsrc = loadShaderFile("bbox.frag");
    const char* bboxVS = bboxVSsrc.c_str();
    const char* bboxFS = bboxFSsrc.c_str();

    unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &bboxVS, NULL);
    glCompileShader(vertexShader);
    {
        int success = 0; char log[1024] = {0};
        glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);
        if (!success) {
            glGetShaderInfoLog(vertexShader, sizeof(log), nullptr, log);
            std::cerr << "[Renderer::init] ERROR: Vertex shader compile failed: " << log << std::endl;
        }
    }

    unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &bboxFS, NULL);
    glCompileShader(fragmentShader);
    {
        int success = 0; char log[1024] = {0};
        glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, &success);
        if (!success) {
            glGetShaderInfoLog(fragmentShader, sizeof(log), nullptr, log);
            std::cerr << "[Renderer::init] ERROR: Fragment shader compile failed: " << log << std::endl;
        }
    }

    m_shaderProgram = glCreateProgram();
    glAttachShader(m_shaderProgram, vertexShader);
    glAttachShader(m_shaderProgram, fragmentShader);
    glLinkProgram(m_shaderProgram);
    {
        int success = 0; char log[1024] = {0};
        glGetProgramiv(m_shaderProgram, GL_LINK_STATUS, &success);
        if (!success) {
            glGetProgramInfoLog(m_shaderProgram, sizeof(log), nullptr, log);
            std::cerr << "[Renderer::init] ERROR: Shader program link failed: " << log << std::endl;
        }
    }
    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    // --- OpenGL State ---
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glLineWidth(2.0f);
    glClearColor(m_bgColor.r, m_bgColor.g, m_bgColor.b, 1.0f);
}

void Renderer::resize(int width, int height) {
    glViewport(0, 0, width, height);
    m_camera.setAspectRatio((float)width / (float)height);
}

void Renderer::render() {
    // Apply current background color each frame so user changes take effect
    glClearColor(m_bgColor.r, m_bgColor.g, m_bgColor.b, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    if (!isVolumeLoaded()) return;

    // If a new volume was loaded, set up GL resources now (context is current in paintGL)
    if (m_needsGLSetup) {
        // Build or rebuild GL resources tied to the current context
        setupVolumeTexture();
        setupProxyCube();
        setupFullscreenQuad();
        setupBoundingBox();
        setupColormapLUT();
        m_needsGLSetup = false;
        std::cout << "  [Renderer::render] Deferred GL setup completed." << std::endl;
    }

    // --- Draw volume or slicer ---
    if (!m_sliceMode && m_volumeTex3D != 0 && m_volumeShader != 0 && m_fullscreenQuadVAO != 0){
        glUseProgram(m_volumeShader);

        glm::mat4 view = m_camera.getViewMatrix();
        glm::mat4 projection = m_camera.getProjectionMatrix();
        glm::mat4 viewProj = projection * view;
        glm::mat4 invViewProj = glm::inverse(viewProj);

        // Camera position from inverse view
        glm::mat4 invView = glm::inverse(view);
        glm::vec3 camPos = glm::vec3(invView[3]);

        // Compute volume box in world space (unscaled). Box is centered at origin.
        float sx = (m_volumeData->spacing_x > 0.0 ? (float)m_volumeData->spacing_x : 1.0f);
        float sy = (m_volumeData->spacing_y > 0.0 ? (float)m_volumeData->spacing_y : 1.0f);
        float sz = (m_volumeData->spacing_z > 0.0 ? (float)m_volumeData->spacing_z : 1.0f);
        glm::vec3 boxSize = glm::vec3(m_volumeData->width * sx, m_volumeData->height * sy, m_volumeData->depth * sz);
        glm::vec3 boxMin = -0.5f * boxSize;
        glm::vec3 boxMax =  0.5f * boxSize;

        glUniformMatrix4fv(glGetUniformLocation(m_volumeShader, "uInvViewProj"), 1, GL_FALSE, glm::value_ptr(invViewProj));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uCamPos"), 1, glm::value_ptr(camPos));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uBoxMin"), 1, glm::value_ptr(boxMin));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uBoxMax"), 1, glm::value_ptr(boxMax));

        // Choose step based on box diagonal to target ~256 samples across the volume
        float diag = glm::length(boxSize);
        float step = diag / 256.0f; // tune for quality/perf
        step = std::max(step, 0.001f);
        glUniform1f(glGetUniformLocation(m_volumeShader, "uStep"), step);

        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_3D, m_volumeTex3D);
        glUniform1i(glGetUniformLocation(m_volumeShader, "uVolume"), 0);

        // Bind LUT on texture unit 1
        if (m_lutTex1D != 0) {
            glActiveTexture(GL_TEXTURE1);
            glBindTexture(GL_TEXTURE_1D, m_lutTex1D);
            glUniform1i(glGetUniformLocation(m_volumeShader, "uLUT"), 1);
        }

        // Disable depth test for fullscreen quad to avoid occlusion
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_CULL_FACE);

        glBindVertexArray(m_fullscreenQuadVAO);
        glDrawArrays(GL_TRIANGLES, 0, 6);
        glBindVertexArray(0);

        // Restore state
        glEnable(GL_DEPTH_TEST);
    }

    // --- Slicer mode: draw a single textured slice quad inside the bbox ---
    if (m_sliceMode && m_volumeTex3D != 0){
        // Lazy compile slice shader if needed
        if (m_sliceShader == 0){
            std::string sVSsrc = loadShaderFile("slice.vert");
            std::string sFSsrc = loadShaderFile("slice.frag");
            const char* svs = sVSsrc.c_str();
            const char* sfs = sFSsrc.c_str();
            unsigned int svsId = glCreateShader(GL_VERTEX_SHADER);
            glShaderSource(svsId, 1, &svs, nullptr);
            glCompileShader(svsId);
            unsigned int sfsId = glCreateShader(GL_FRAGMENT_SHADER);
            glShaderSource(sfsId, 1, &sfs, nullptr);
            glCompileShader(sfsId);
            m_sliceShader = glCreateProgram();
            glAttachShader(m_sliceShader, svsId);
            glAttachShader(m_sliceShader, sfsId);
            glLinkProgram(m_sliceShader);
            glDeleteShader(svsId);
            glDeleteShader(sfsId);
        }

        // Compute box min/max from volume spacing/dims (unscaled)
        float sx = (m_volumeData->spacing_x > 0.0 ? (float)m_volumeData->spacing_x : 1.0f);
        float sy = (m_volumeData->spacing_y > 0.0 ? (float)m_volumeData->spacing_y : 1.0f);
        float sz = (m_volumeData->spacing_z > 0.0 ? (float)m_volumeData->spacing_z : 1.0f);
        glm::vec3 boxSize = glm::vec3(m_volumeData->width * sx, m_volumeData->height * sy, m_volumeData->depth * sz);
        glm::vec3 boxMin = -0.5f * boxSize;
        glm::vec3 boxMax =  0.5f * boxSize;

        // Build/update slice quad VBO
        if (m_sliceVAO == 0) glGenVertexArrays(1, &m_sliceVAO);
        if (m_sliceVBO == 0) glGenBuffers(1, &m_sliceVBO);

        std::vector<float> quad; // positions only (3 floats)
        quad.reserve(6*3);
        // normalized slice position in [0,1]
        auto clampi = [](int v, int lo, int hi){ return v<lo?lo:(v>hi?hi:v); };
        int w = (int)m_volumeData->width;
        int h = (int)m_volumeData->height;
        int d = (int)m_volumeData->depth;
        if (m_sliceAxis == 0) m_sliceIndex = clampi(m_sliceIndex, 0, d-1);
        else if (m_sliceAxis == 1) m_sliceIndex = clampi(m_sliceIndex, 0, h-1);
        else m_sliceIndex = clampi(m_sliceIndex, 0, w-1);

        if (m_sliceAxis == 0){ // Z
            float s = (m_sliceIndex + 0.5f) / float(std::max(1,d));
            float z = glm::mix(boxMin.z, boxMax.z, s);
            glm::vec3 p0(boxMin.x, boxMin.y, z);
            glm::vec3 p1(boxMax.x, boxMin.y, z);
            glm::vec3 p2(boxMax.x, boxMax.y, z);
            glm::vec3 p3(boxMin.x, boxMax.y, z);
            auto push = [&](glm::vec3 p){ quad.push_back(p.x); quad.push_back(p.y); quad.push_back(p.z); };
            push(p0); push(p1); push(p2); push(p0); push(p2); push(p3);
        } else if (m_sliceAxis == 1){ // Y
            float s = (m_sliceIndex + 0.5f) / float(std::max(1,h));
            float y = glm::mix(boxMin.y, boxMax.y, s);
            glm::vec3 p0(boxMin.x, y, boxMin.z);
            glm::vec3 p1(boxMax.x, y, boxMin.z);
            glm::vec3 p2(boxMax.x, y, boxMax.z);
            glm::vec3 p3(boxMin.x, y, boxMax.z);
            auto push = [&](glm::vec3 p){ quad.push_back(p.x); quad.push_back(p.y); quad.push_back(p.z); };
            push(p0); push(p1); push(p2); push(p0); push(p2); push(p3);
        } else { // X
            float s = (m_sliceIndex + 0.5f) / float(std::max(1,w));
            float x = glm::mix(boxMin.x, boxMax.x, s);
            glm::vec3 p0(x, boxMin.y, boxMin.z);
            glm::vec3 p1(x, boxMax.y, boxMin.z);
            glm::vec3 p2(x, boxMax.y, boxMax.z);
            glm::vec3 p3(x, boxMin.y, boxMax.z);
            auto push = [&](glm::vec3 p){ quad.push_back(p.x); quad.push_back(p.y); quad.push_back(p.z); };
            push(p0); push(p1); push(p2); push(p0); push(p2); push(p3);
        }

        glBindVertexArray(m_sliceVAO);
        glBindBuffer(GL_ARRAY_BUFFER, m_sliceVBO);
        glBufferData(GL_ARRAY_BUFFER, quad.size()*sizeof(float), quad.data(), GL_DYNAMIC_DRAW);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*sizeof(float), (void*)0);
        glEnableVertexAttribArray(0);
        glBindBuffer(GL_ARRAY_BUFFER, 0);

        glUseProgram(m_sliceShader);
        glm::mat4 model = glm::mat4(1.0f);
        glm::mat4 view = m_camera.getViewMatrix();
        glm::mat4 projection = m_camera.getProjectionMatrix();
        glUniformMatrix4fv(glGetUniformLocation(m_sliceShader, "model"), 1, GL_FALSE, glm::value_ptr(model));
        glUniformMatrix4fv(glGetUniformLocation(m_sliceShader, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(m_sliceShader, "projection"), 1, GL_FALSE, glm::value_ptr(projection));
        glUniform3fv(glGetUniformLocation(m_sliceShader, "uBoxMin"), 1, glm::value_ptr(boxMin));
        glUniform3fv(glGetUniformLocation(m_sliceShader, "uBoxMax"), 1, glm::value_ptr(boxMax));
        glUniform1i(glGetUniformLocation(m_sliceShader, "uAxis"), m_sliceAxis);

        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_3D, m_volumeTex3D);
        glUniform1i(glGetUniformLocation(m_sliceShader, "uVolume"), 0);

        if (m_lutTex1D != 0) {
            glActiveTexture(GL_TEXTURE1);
            glBindTexture(GL_TEXTURE_1D, m_lutTex1D);
            glUniform1i(glGetUniformLocation(m_sliceShader, "uLUT"), 1);
        }

        glDisable(GL_CULL_FACE);
        glBindVertexArray(m_sliceVAO);
        glDrawArrays(GL_TRIANGLES, 0, 6);
        glBindVertexArray(0);
    }

    // Draw bounding box lines on top (avoid being occluded by proxy cube depth)
    if (m_showBoundingBox) {
        glDisable(GL_DEPTH_TEST);
        glUseProgram(m_shaderProgram);

    // Set up transformation matrices
    glm::mat4 model = glm::mat4(1.0f); // Identity matrix
    glm::mat4 view = m_camera.getViewMatrix();
    glm::mat4 projection = m_camera.getProjectionMatrix();

    // Pass matrices to the shader
    glUniformMatrix4fv(glGetUniformLocation(m_shaderProgram, "model"), 1, GL_FALSE, glm::value_ptr(model));
    glUniformMatrix4fv(glGetUniformLocation(m_shaderProgram, "view"), 1, GL_FALSE, glm::value_ptr(view));
    glUniformMatrix4fv(glGetUniformLocation(m_shaderProgram, "projection"), 1, GL_FALSE, glm::value_ptr(projection));

        // Draw the bounding box
        glBindVertexArray(m_boundingBoxVAO);
        glDrawArrays(GL_LINES, 0, 24);
        glBindVertexArray(0);
    }
}


void Renderer::setupBoundingBox() {
    if (!isVolumeLoaded()) return;

    float sx = (m_volumeData->spacing_x > 0.0 ? (float)m_volumeData->spacing_x : 1.0f);
    float sy = (m_volumeData->spacing_y > 0.0 ? (float)m_volumeData->spacing_y : 1.0f);
    float sz = (m_volumeData->spacing_z > 0.0 ? (float)m_volumeData->spacing_z : 1.0f);

    float w = m_volumeData->width * sx * m_bboxScale;
    float h = m_volumeData->height * sy * m_bboxScale;
    float d = m_volumeData->depth * sz * m_bboxScale;

    // Center the box at the origin
    float x_min = -w / 2.0f; float x_max = w / 2.0f;
    float y_min = -h / 2.0f; float y_max = h / 2.0f;
    float z_min = -d / 2.0f; float z_max = d / 2.0f;

    // Define the 12 lines of the cube by endpoints
    std::vector<glm::vec3> edges = {
        // Bottom face (z = z_min)
        {x_min, y_min, z_min}, {x_max, y_min, z_min},
        {x_max, y_min, z_min}, {x_max, y_max, z_min},
        {x_max, y_max, z_min}, {x_min, y_max, z_min},
        {x_min, y_max, z_min}, {x_min, y_min, z_min},
        // Top face (z = z_max)
        {x_min, y_min, z_max}, {x_max, y_min, z_max},
        {x_max, y_min, z_max}, {x_max, y_max, z_max},
        {x_max, y_max, z_max}, {x_min, y_max, z_max},
        {x_min, y_max, z_max}, {x_min, y_min, z_max},
        // Vertical edges
        {x_min, y_min, z_min}, {x_min, y_min, z_max},
        {x_max, y_min, z_min}, {x_max, y_min, z_max},
        {x_max, y_max, z_min}, {x_max, y_max, z_max},
        {x_min, y_max, z_min}, {x_min, y_max, z_max}
    };

    // Build interleaved position (xyz) + color (rgb) for each vertex.
    // Color coding by edge axis: X=red, Y=green, Z=blue.
    std::vector<float> vertices;
    vertices.reserve(edges.size() * 6);
    for (size_t i = 0; i < edges.size(); i += 2) {
        glm::vec3 a = edges[i];
        glm::vec3 b = edges[i+1];
        glm::vec3 dir = b - a;
        glm::vec3 color(1.0f, 1.0f, 1.0f);
        // Determine dominant axis (edges are axis-aligned)
        if (std::abs(dir.x) > 0.0f && dir.y == 0.0f && dir.z == 0.0f) {
            color = glm::vec3(1.0f, 0.0f, 0.0f); // X - red
        } else if (std::abs(dir.y) > 0.0f && dir.x == 0.0f && dir.z == 0.0f) {
            color = glm::vec3(0.0f, 1.0f, 0.0f); // Y - green
        } else if (std::abs(dir.z) > 0.0f && dir.x == 0.0f && dir.y == 0.0f) {
            color = glm::vec3(0.0f, 0.0f, 1.0f); // Z - blue
        }
        // Push both endpoints with same color
        vertices.push_back(a.x); vertices.push_back(a.y); vertices.push_back(a.z);
        vertices.push_back(color.r); vertices.push_back(color.g); vertices.push_back(color.b);
        vertices.push_back(b.x); vertices.push_back(b.y); vertices.push_back(b.z);
        vertices.push_back(color.r); vertices.push_back(color.g); vertices.push_back(color.b);
    }

    if (m_boundingBoxVAO == 0) glGenVertexArrays(1, &m_boundingBoxVAO);
    if (m_boundingBoxVBO == 0) glGenBuffers(1, &m_boundingBoxVBO);

    glBindVertexArray(m_boundingBoxVAO);
    glBindBuffer(GL_ARRAY_BUFFER, m_boundingBoxVBO);
    glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(float), vertices.data(), GL_STATIC_DRAW);

    // position
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    // color
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    // Frame the box with the camera only when requested (e.g., after load)
    if (m_shouldFrameCameraNext) {
        m_camera.frameBox(w, h, d);
        m_shouldFrameCameraNext = false;
    }

    std::cout << "  [Renderer::setupBoundingBox] Box dimensions: " << w << "x" << h << "x" << d << std::endl;
}

void Renderer::setupVolumeTexture() {
    if (!isVolumeLoaded()) return;

    // Create 3D texture if needed
    if (m_volumeTex3D == 0){
        glGenTextures(1, &m_volumeTex3D);
    }
    glBindTexture(GL_TEXTURE_3D, m_volumeTex3D);

    // Texture parameters
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

    // Upload data (uint16). Use GL_R16 normalized format so sampler returns [0,1]
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage3D(
        GL_TEXTURE_3D,
        0,
        GL_R16,
        (GLsizei)m_volumeData->width,
        (GLsizei)m_volumeData->height,
        (GLsizei)m_volumeData->depth,
        0,
        GL_RED,
        GL_UNSIGNED_SHORT,
        m_volumeData->data.data()
    );

    // Set swizzle so sampling returns grayscale in all channels if needed
    GLint swizzleMask[] = {GL_RED, GL_RED, GL_RED, GL_ONE};
    glTexParameteriv(GL_TEXTURE_3D, GL_TEXTURE_SWIZZLE_RGBA, swizzleMask);

    glBindTexture(GL_TEXTURE_3D, 0);
}

void Renderer::setupProxyCube() {
    // Create a unit cube centered at origin that will be scaled by box size via model (here model=identity, so we precompute in object-space actual positions)
    float sx = (m_volumeData->spacing_x > 0.0 ? (float)m_volumeData->spacing_x : 1.0f);
    float sy = (m_volumeData->spacing_y > 0.0 ? (float)m_volumeData->spacing_y : 1.0f);
    float sz = (m_volumeData->spacing_z > 0.0 ? (float)m_volumeData->spacing_z : 1.0f);
    float w = m_volumeData->width * sx;
    float h = m_volumeData->height * sy;
    float d = m_volumeData->depth * sz;
    float x0 = -w*0.5f, x1 = w*0.5f;
    float y0 = -h*0.5f, y1 = h*0.5f;
    float z0 = -d*0.5f, z1 = d*0.5f;

    // 12 triangles (36 verts) for cube faces
    std::vector<float> verts = {
        // +X
        x1,y0,z0,  x1,y1,z0,  x1,y1,z1,
        x1,y0,z0,  x1,y1,z1,  x1,y0,z1,
        // -X
        x0,y0,z0,  x0,y0,z1,  x0,y1,z1,
        x0,y0,z0,  x0,y1,z1,  x0,y1,z0,
        // +Y
        x0,y1,z0,  x0,y1,z1,  x1,y1,z1,
        x0,y1,z0,  x1,y1,z1,  x1,y1,z0,
        // -Y
        x0,y0,z0,  x1,y0,z0,  x1,y0,z1,
        x0,y0,z0,  x1,y0,z1,  x0,y0,z1,
        // +Z
        x0,y0,z1,  x1,y0,z1,  x1,y1,z1,
        x0,y0,z1,  x1,y1,z1,  x0,y1,z1,
        // -Z
        x0,y0,z0,  x0,y1,z0,  x1,y1,z0,
        x0,y0,z0,  x1,y1,z0,  x1,y0,z0
    };

    if (m_proxyCubeVAO == 0) glGenVertexArrays(1, &m_proxyCubeVAO);
    if (m_proxyCubeVBO == 0) glGenBuffers(1, &m_proxyCubeVBO);

    glBindVertexArray(m_proxyCubeVAO);
    glBindBuffer(GL_ARRAY_BUFFER, m_proxyCubeVBO);
    glBufferData(GL_ARRAY_BUFFER, verts.size() * sizeof(float), verts.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    // Compile volume shader (fullscreen quad approach)
    std::string volVSsrc = loadShaderFile("vol_fullscreen.vert");
    std::string volFSsrc = loadShaderFile("vol_fullscreen.frag");
    const char* vssc = volVSsrc.c_str();
    const char* fssc = volFSsrc.c_str();

    unsigned int vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vssc, nullptr);
    glCompileShader(vs);
    unsigned int fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fssc, nullptr);
    glCompileShader(fs);
    m_volumeShader = glCreateProgram();
    glAttachShader(m_volumeShader, vs);
    glAttachShader(m_volumeShader, fs);
    glLinkProgram(m_volumeShader);
    glDeleteShader(vs);
    glDeleteShader(fs);
}

// --- Colormap LUT setup ---
// static void colorPreset(int preset, float t, float& r, float& g, float& b) {
//     // 10 simple presets approximating common colormaps
//     t = std::max(0.0f, std::min(1.0f, t));
//     switch (preset) {
//         case 0: { // Grayscale
//             r = g = b = t; break;
//         }
//         case 1: { // Inverted Grayscale
//             r = g = b = 1.0f - t; break;
//         }
//         case 2: { // Hot
//             float x = t;
//             r = std::min(1.0f, 3.0f * x);
//             g = std::min(1.0f, std::max(0.0f, 3.0f * x - 1.0f));
//             b = std::min(1.0f, std::max(0.0f, 3.0f * x - 2.0f));
//             break;
//         }
//         case 3: { // Cool
//             r = t; g = 1.0f - t; b = 1.0f; break;
//         }
//         case 4: { // Spring
//             r = 1.0f; g = t; b = 1.0f - t; break;
//         }
//         case 5: { // Summer
//             r = t; g = 0.5f + 0.5f*t; b = 0.4f; break;
//         }
//         case 6: { // Autumn
//             r = 1.0f; g = t; b = 0.0f; break;
//         }
//         case 7: { // Winter
//             r = 0.0f; g = t; b = 1.0f - t; break;
//         }
//         case 8: { // Jet-like
//             float r1 = std::min(1.0f, std::max(0.0f, 1.5f - std::abs(4.0f*t - 3.0f)));
//             float g1 = std::min(1.0f, std::max(0.0f, 1.5f - std::abs(4.0f*t - 2.0f)));
//             float b1 = std::min(1.0f, std::max(0.0f, 1.5f - std::abs(4.0f*t - 1.0f)));
//             r = r1; g = g1; b = b1; break;
//         }
//         default: { // Viridis-like simple approx
//             r = 0.267f + 0.633f*t; 
//             g = 0.004f + 0.996f*t; 
//             b = 0.329f + 0.671f*(1.0f - t);
//             r = std::min(1.0f, std::max(0.0f, r));
//             g = std::min(1.0f, std::max(0.0f, g));
//             b = std::min(1.0f, std::max(0.0f, b));
//             break;
//         }
//     }
// }

// use tinycolormap
static void colorPreset(int preset, float t, float& r, float& g, float& b){
    // Clamp t to [0,1]
    if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
    using tinycolormap::ColormapType;
    ColormapType type = ColormapType::Viridis;

    // Map our 0..9 presets onto tinycolormap presets
    // 0: Gray, 1: Gray inverted, 2: Hot, 3: Turbo (as cool-ish), 4: Plasma,
    // 5: Cividis, 6: Inferno, 7: Magma, 8: Jet, 9: Viridis
    switch (preset) {
        case 0: type = ColormapType::Gray; t = 1.0f - t; break;
        case 1: type = ColormapType::Gray; break;
        case 2: type = ColormapType::Hot; break;
        case 3: type = ColormapType::Turbo; break;
        case 4: type = ColormapType::Plasma; break;
        case 5: type = ColormapType::Cividis; break;
        case 6: type = ColormapType::Inferno; break;
        case 7: type = ColormapType::Magma; break;
        case 8: type = ColormapType::Jet; break;
        default: type = ColormapType::Viridis; break;
    }

    tinycolormap::Color c = tinycolormap::GetColor(static_cast<double>(t), type);
    r = static_cast<float>(c.r());
    g = static_cast<float>(c.g());
    b = static_cast<float>(c.b());
}


void Renderer::setupFullscreenQuad() {
    // Fullscreen quad in NDC coordinates [-1,1]
    float quadVertices[] = {
        // positions (x, y)
        -1.0f, -1.0f,
         1.0f, -1.0f,
         1.0f,  1.0f,
        -1.0f, -1.0f,
         1.0f,  1.0f,
        -1.0f,  1.0f
    };

    if (m_fullscreenQuadVAO == 0) glGenVertexArrays(1, &m_fullscreenQuadVAO);
    if (m_fullscreenQuadVBO == 0) glGenBuffers(1, &m_fullscreenQuadVBO);

    glBindVertexArray(m_fullscreenQuadVAO);
    glBindBuffer(GL_ARRAY_BUFFER, m_fullscreenQuadVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(quadVertices), quadVertices, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}

void Renderer::setupColormapLUT() {
    const int N = 256;
    std::vector<unsigned char> data(N*4);
    for (int i=0;i<N;++i){
        float t = i / float(N-1);
        float r,g,b; colorPreset(m_colormapPreset, t, r, g, b);
        data[4*i+0] = (unsigned char)std::round(255.0f * r);
        data[4*i+1] = (unsigned char)std::round(255.0f * g);
        data[4*i+2] = (unsigned char)std::round(255.0f * b);
        data[4*i+3] = 255;
    }
    if (m_lutTex1D == 0) glGenTextures(1, &m_lutTex1D);
    glBindTexture(GL_TEXTURE_1D, m_lutTex1D);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA8, N, 0, GL_RGBA, GL_UNSIGNED_BYTE, data.data());
    glBindTexture(GL_TEXTURE_1D, 0);
}

void Renderer::setShowBoundingBox(bool show) { m_showBoundingBox = show; }

void Renderer::setColormapPreset(int presetIndex) {
    m_colormapPreset = std::max(0, std::min(9, presetIndex));
    // Mark for deferred rebuild next frame when context is current
    m_needsGLSetup = true;
}

void Renderer::camera_rotate(float dx, float dy) {
    m_camera.rotate(dx, dy);
}

void Renderer::camera_zoom(float delta) {
    m_camera.zoom(delta);
}

void Renderer::set_camera_angles(float azimuthDeg, float elevationDeg) {
    m_camera.setAngles(azimuthDeg, elevationDeg);
}

void Renderer::setBackgroundColor(float r, float g, float b) {
    m_bgColor = glm::vec3(r, g, b);
}

void Renderer::setBoundingBoxScale(float scale) {
    m_bboxScale = std::max(0.1f, std::min(5.0f, scale));
    m_needsGLSetup = true; // Rebuild bbox VBO with new size next frame
}

void Renderer::frameCameraToBox() {
    if (!isVolumeLoaded()) return;
    // Compute unscaled physical box of the volume
    float sx = (m_volumeData->spacing_x > 0.0 ? (float)m_volumeData->spacing_x : 1.0f);
    float sy = (m_volumeData->spacing_y > 0.0 ? (float)m_volumeData->spacing_y : 1.0f);
    float sz = (m_volumeData->spacing_z > 0.0 ? (float)m_volumeData->spacing_z : 1.0f);
    float w = (float)m_volumeData->width * sx;
    float h = (float)m_volumeData->height * sy;
    float d = (float)m_volumeData->depth * sz;
    m_camera.frameBox(w, h, d);
}

bool Renderer::loadVolume(const std::string& path) {
    std::cout << "      MVR INFO:: Attempting to load volume from path: " << path << std::endl;
    if (!fs::exists(path)) {
        std::cerr << "      MVR ERROR: Path does not exist: " << path << std::endl;
        return false;
    }
    m_volumeData->clear();

    bool success = false;
    if (fs::is_directory(path)) {
        std::cout << "      MVR INFO:: Path is a directory, attempting to load as DICOM series." << std::endl;
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

    // IMPORTANT: Do NOT create GL objects here (no current GL context).
    // Defer GL resource setup until render(), when the QOpenGLWidget context is current.
    if (success) {
        m_needsGLSetup = true;
        m_shouldFrameCameraNext = true; // Frame camera on first bbox build after a successful load
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
