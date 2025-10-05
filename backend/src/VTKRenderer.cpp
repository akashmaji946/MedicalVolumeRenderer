// backend/src/VTKRenderer.cpp

#include "../include/VTKRenderer.h"

#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>

#include <glm/gtc/type_ptr.hpp>
#include "../include/tinycolormap.h"
#include <GLFW/glfw3.h>

#ifndef SHADERS_DIR
    #define SHADERS_DIR "../shaders"
#endif

namespace fs = std::filesystem;

static std::string loadShaderFile(const char* filename) {
    std::string fullPath = std::string(SHADERS_DIR) + "/" + filename;
    std::ifstream file(fullPath);
    if (!file.is_open()) {
        std::cerr << "[VTKRenderer::loadShaderFile] ERROR: Cannot open shader file: " << fullPath << std::endl;
        return std::string();
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// Simple ASCII VTK parser for STRUCTURED_POINTS with SCALARS blocks
static VTKVolumeData parseVTK(const std::string& filename) {
    VTKVolumeData volume;
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "[VTKRenderer] Error: Could not open VTK file: " << filename << std::endl;
        return volume;
    }

    std::string line;
    long long point_count = 0;
    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string keyword;
        ss >> keyword;
        if (keyword == "DIMENSIONS") {
            ss >> volume.dimensions.x >> volume.dimensions.y >> volume.dimensions.z;
        } else if (keyword == "SPACING") {
            ss >> volume.spacing.x >> volume.spacing.y >> volume.spacing.z;
        } else if (keyword == "ORIGIN") {
            ss >> volume.origin.x >> volume.origin.y >> volume.origin.z;
        } else if (keyword == "POINT_DATA") {
            ss >> point_count;
        } else if (keyword == "SCALARS") {
            std::string fieldName, fieldType; int numComponents = 1;
            ss >> fieldName >> fieldType >> numComponents;
            // read LOOKUP_TABLE line
            std::getline(file, line);
            VTKVolumeData::Field field; field.name = fieldName; field.data.reserve(point_count * numComponents);
            double v;
            for (long long i = 0; i < point_count * numComponents; ++i) {
                if (!(file >> v)) break;
                field.data.push_back(static_cast<float>(v));
            }
            volume.fields.push_back(std::move(field));
        } else if (keyword == "FIELD") {
            std::string fieldKeyword; int numFields = 0; ss >> fieldKeyword >> numFields;
            for (int f = 0; f < numFields; ++f) {
                std::string fieldName, fieldType; int numComponents = 1, numTuples = 0;
                file >> fieldName >> numComponents >> numTuples >> fieldType;
                VTKVolumeData::Field field; field.name = fieldName; field.data.reserve((long long)numComponents * numTuples);
                double v;
                for (long long i = 0; i < (long long)numComponents * numTuples; ++i) {
                    if (!(file >> v)) break;
                    field.data.push_back(static_cast<float>(v));
                }
                volume.fields.push_back(std::move(field));
            }
        }
    }

    // Normalize each field and compute min/max
    for (auto& f : volume.fields) {
        if (f.data.empty()) continue;
        auto [minIt, maxIt] = std::minmax_element(f.data.begin(), f.data.end());
        f.minVal = *minIt; f.maxVal = *maxIt;
        if (f.maxVal - f.minVal > 1e-6f) {
            for (auto& x : f.data) x = (x - f.minVal) / (f.maxVal - f.minVal);
        } else {
            for (auto& x : f.data) x = 0.5f;
        }
    }

    std::cout << "[VTKRenderer] Parsed VTK: dims="
              << volume.dimensions.x << "x" << volume.dimensions.y << "x" << volume.dimensions.z
              << ", fields=" << volume.fields.size() << std::endl;
    return volume;
}

VTKRenderer::VTKRenderer() {
    m_volume = std::make_unique<VTKVolumeData>();
}

bool VTKRenderer::loadVTK(const std::string& filename) {
    if (!fs::exists(filename)) {
        std::cerr << "[VTKRenderer] File not found: " << filename << std::endl;
        return false;
    }
    *m_volume = parseVTK(filename);
    m_currentField = 0;
    if (m_volume->empty()) {
        std::cerr << "[VTKRenderer] Empty or invalid VTK volume" << std::endl;
        return false;
    }
    m_needsGLSetup = true;
    return true;
}

void VTKRenderer::init() {
    if (!gladLoadGL()) {
        std::cerr << "[VTKRenderer::init] Failed to initialize GLAD" << std::endl;
        return;
    }
    std::cout << "[VTKRenderer::init] OpenGL: " << glGetString(GL_VERSION) << std::endl;
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glClearColor(m_bgColor.r, m_bgColor.g, m_bgColor.b, 1.0f);

    // Compile bbox shader
    std::string bboxVSsrc = loadShaderFile("bbox.vert");
    std::string bboxFSsrc = loadShaderFile("bbox.frag");
    const char* bboxVS = bboxVSsrc.c_str();
    const char* bboxFS = bboxFSsrc.c_str();
    unsigned int vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &bboxVS, nullptr); glCompileShader(vs);
    unsigned int fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &bboxFS, nullptr); glCompileShader(fs);
    m_bboxProgram = glCreateProgram();
    glAttachShader(m_bboxProgram, vs);
    glAttachShader(m_bboxProgram, fs);
    glLinkProgram(m_bboxProgram);
    glDeleteShader(vs); glDeleteShader(fs);
}

void VTKRenderer::resize(int width, int height) {
    glViewport(0, 0, width, height);
    m_camera.setAspectRatio((float)width / (float)height);
}

void VTKRenderer::setupFullscreenQuad() {
    if (m_fullscreenQuadVAO != 0) return;
    float quadVertices[] = {
        -1.0f, -1.0f,
         1.0f, -1.0f,
         1.0f,  1.0f,
        -1.0f, -1.0f,
         1.0f,  1.0f,
        -1.0f,  1.0f
    };
    glGenVertexArrays(1, &m_fullscreenQuadVAO);
    glGenBuffers(1, &m_fullscreenQuadVBO);
    glBindVertexArray(m_fullscreenQuadVAO);
    glBindBuffer(GL_ARRAY_BUFFER, m_fullscreenQuadVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(quadVertices), quadVertices, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}

void VTKRenderer::setupColormapLUT() {
    // Build or rebuild LUT according to current preset using tinycolormap
    const int N = 256;
    std::vector<unsigned char> data(N*4);
    auto mapPreset = [](int preset){
        using tinycolormap::ColormapType;
        switch (preset) {
            case 0: return ColormapType::Gray;    // Grayscale (we'll invert t below)
            case 1: return ColormapType::Gray;    // Grayscale normal
            case 2: return ColormapType::Hot;     // Hot
            case 3: return ColormapType::Turbo;   // Cool-ish
            case 4: return ColormapType::Plasma;  // Spring-like
            case 5: return ColormapType::Cividis; // Summer-like
            case 6: return ColormapType::Inferno; // Autumn-like
            case 7: return ColormapType::Magma;   // Winter-like
            case 8: return ColormapType::Jet;     // Jet-like
            default:return ColormapType::Viridis; // Viridis-like
        }
    };
    using tinycolormap::GetColor;
    using tinycolormap::ColormapType;
    ColormapType type = mapPreset(m_colormapPreset);
    for (int i=0;i<N;++i){
        float t = i / float(N-1);
        // For preset 0 we invert like in Renderer mapping
        if (m_colormapPreset == 0) t = 1.0f - t;
        auto c = GetColor(static_cast<double>(t), type);
        data[4*i+0] = (unsigned char)std::round(255.0 * c.r());
        data[4*i+1] = (unsigned char)std::round(255.0 * c.g());
        data[4*i+2] = (unsigned char)std::round(255.0 * c.b());
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

void VTKRenderer::setupBoundingBox() {
    // Create VAO/VBO if missing, else update buffer with new scaled geometry
    float sx = std::max(0.0001f, m_volume->spacing.x);
    float sy = std::max(0.0001f, m_volume->spacing.y);
    float sz = std::max(0.0001f, m_volume->spacing.z);
    float w = m_volume->dimensions.x * sx * m_bboxScale;
    float h = m_volume->dimensions.y * sy * m_bboxScale;
    float d = m_volume->dimensions.z * sz * m_bboxScale;
    float x_min = -w/2.f, x_max = w/2.f;
    float y_min = -h/2.f, y_max = h/2.f;
    float z_min = -d/2.f, z_max = d/2.f;

    std::vector<glm::vec3> edges = {
        {x_min, y_min, z_min}, {x_max, y_min, z_min},
        {x_max, y_min, z_min}, {x_max, y_max, z_min},
        {x_max, y_max, z_min}, {x_min, y_max, z_min},
        {x_min, y_max, z_min}, {x_min, y_min, z_min},
        {x_min, y_min, z_max}, {x_max, y_min, z_max},
        {x_max, y_min, z_max}, {x_max, y_max, z_max},
        {x_max, y_max, z_max}, {x_min, y_max, z_max},
        {x_min, y_max, z_max}, {x_min, y_min, z_max},
        {x_min, y_min, z_min}, {x_min, y_min, z_max},
        {x_max, y_min, z_min}, {x_max, y_min, z_max},
        {x_max, y_max, z_min}, {x_max, y_max, z_max},
        {x_min, y_max, z_min}, {x_min, y_max, z_max}
    };

    std::vector<float> vertices; vertices.reserve(edges.size() * 6);
    for (size_t i=0;i<edges.size();i+=2) {
        glm::vec3 a = edges[i]; glm::vec3 b = edges[i+1];
        glm::vec3 color(1.f,1.f,1.f);
        glm::vec3 dir = b-a;
        if (std::abs(dir.x) > 0.0f && dir.y == 0.0f && dir.z == 0.0f) color = glm::vec3(1,0,0);
        else if (std::abs(dir.y) > 0.0f && dir.x == 0.0f && dir.z == 0.0f) color = glm::vec3(0,1,0);
        else if (std::abs(dir.z) > 0.0f && dir.x == 0.0f && dir.y == 0.0f) color = glm::vec3(0,0,1);
        vertices.insert(vertices.end(), {a.x,a.y,a.z, color.r,color.g,color.b});
        vertices.insert(vertices.end(), {b.x,b.y,b.z, color.r,color.g,color.b});
    }

    if (m_boundingBoxVAO == 0) glGenVertexArrays(1, &m_boundingBoxVAO);
    if (m_boundingBoxVBO == 0) glGenBuffers(1, &m_boundingBoxVBO);
    glBindVertexArray(m_boundingBoxVAO);
    glBindBuffer(GL_ARRAY_BUFFER, m_boundingBoxVBO);
    glBufferData(GL_ARRAY_BUFFER, vertices.size()*sizeof(float), vertices.data(), GL_STATIC_DRAW);
    // Set up attributes if first time
    if (glGetAttribLocation(m_bboxProgram, "position") || true) {
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6*sizeof(float), (void*)0);
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6*sizeof(float), (void*)(3*sizeof(float)));
        glEnableVertexAttribArray(1);
    }
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}

void VTKRenderer::setColormapPreset(int presetIndex) {
    m_colormapPreset = std::max(0, std::min(9, presetIndex));
    // Rebuild LUT next render
    m_needsGLSetup = true;
}

void VTKRenderer::setupVolumeTexture() {
    if (!isVolumeLoaded()) return;
    if (m_volumeTex3D == 0) glGenTextures(1, &m_volumeTex3D);
    glBindTexture(GL_TEXTURE_3D, m_volumeTex3D);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

    auto& f = m_volume->fields[m_currentField];
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage3D(
        GL_TEXTURE_3D, 0, GL_R32F,
        (GLsizei)m_volume->dimensions.x,
        (GLsizei)m_volume->dimensions.y,
        (GLsizei)m_volume->dimensions.z,
        0,
        GL_RED, GL_FLOAT,
        f.data.data()
    );
    GLint swizzleMask[] = {GL_RED, GL_RED, GL_RED, GL_ONE};
    glTexParameteriv(GL_TEXTURE_3D, GL_TEXTURE_SWIZZLE_RGBA, swizzleMask);
    glBindTexture(GL_TEXTURE_3D, 0);
}

void VTKRenderer::render() {
    glClearColor(m_bgColor.r, m_bgColor.g, m_bgColor.b, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    if (!isVolumeLoaded()) return;

    if (m_needsGLSetup) {
        // Build or rebuild GL resources tied to the current context
        setupVolumeTexture();
        setupFullscreenQuad();
        setupBoundingBox();
        setupColormapLUT();
        // compile volume shader
        if (m_volumeShader == 0) {
            std::string volVSsrc = loadShaderFile("vol_fullscreen.vert");
            std::string volFSsrc = loadShaderFile("vol_fullscreen.frag");
            const char* vssc = volVSsrc.c_str();
            const char* fssc = volFSsrc.c_str();
            unsigned int vs = glCreateShader(GL_VERTEX_SHADER);
            glShaderSource(vs, 1, &vssc, nullptr); glCompileShader(vs);
            unsigned int fs = glCreateShader(GL_FRAGMENT_SHADER);
            glShaderSource(fs, 1, &fssc, nullptr); glCompileShader(fs);
            m_volumeShader = glCreateProgram();
            glAttachShader(m_volumeShader, vs);
            glAttachShader(m_volumeShader, fs);
            glLinkProgram(m_volumeShader);
            glDeleteShader(vs); glDeleteShader(fs);
        }
        m_needsGLSetup = false;
    }

    // Volume raymarch pass (fullscreen)
    if (!m_sliceMode && m_volumeTex3D != 0 && m_volumeShader != 0 && m_fullscreenQuadVAO != 0) {
        // Build simple matrices like the existing Renderer
        glm::mat4 view = m_camera.getViewMatrix();
        glm::mat4 projection = m_camera.getProjectionMatrix();
        glm::mat4 viewProj = projection * view;
        glm::mat4 invViewProj = glm::inverse(viewProj);
        glm::mat4 invView = glm::inverse(view);
        glm::vec3 camPos = glm::vec3(invView[3]);

        float sx = std::max(0.0001f, m_volume->spacing.x);
        float sy = std::max(0.0001f, m_volume->spacing.y);
        float sz = std::max(0.0001f, m_volume->spacing.z);
        glm::vec3 boxSize(m_volume->dimensions.x * sx, m_volume->dimensions.y * sy, m_volume->dimensions.z * sz);
        glm::vec3 boxMin = -0.5f * boxSize;
        glm::vec3 boxMax =  0.5f * boxSize;

        glUseProgram(m_volumeShader);
        glUniformMatrix4fv(glGetUniformLocation(m_volumeShader, "uInvViewProj"), 1, GL_FALSE, glm::value_ptr(invViewProj));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uCamPos"), 1, glm::value_ptr(camPos));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uBoxMin"), 1, glm::value_ptr(boxMin));
        glUniform3fv(glGetUniformLocation(m_volumeShader, "uBoxMax"), 1, glm::value_ptr(boxMax));

        float diag = glm::length(boxSize);
        float step = std::max(0.001f, diag / 256.0f);
        glUniform1f(glGetUniformLocation(m_volumeShader, "uStep"), step);

        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_3D, m_volumeTex3D);
        glUniform1i(glGetUniformLocation(m_volumeShader, "uVolume"), 0);

        if (m_lutTex1D != 0) {
            glActiveTexture(GL_TEXTURE1);
            glBindTexture(GL_TEXTURE_1D, m_lutTex1D);
            glUniform1i(glGetUniformLocation(m_volumeShader, "uLUT"), 1);
        }

        glDisable(GL_DEPTH_TEST);
        glBindVertexArray(m_fullscreenQuadVAO);
        glDrawArrays(GL_TRIANGLES, 0, 6);
        glBindVertexArray(0);
        glEnable(GL_DEPTH_TEST);
    }

    // Slicer mode: draw a single textured slice quad inside the bbox
    if (m_sliceMode && m_volumeTex3D != 0) {
        // Lazy compile slice shader if needed
        if (m_sliceShader == 0) {
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

        // Compute box based on spacing/dims
        float sx = std::max(0.0001f, m_volume->spacing.x);
        float sy = std::max(0.0001f, m_volume->spacing.y);
        float sz = std::max(0.0001f, m_volume->spacing.z);
        glm::vec3 boxSize(m_volume->dimensions.x * sx, m_volume->dimensions.y * sy, m_volume->dimensions.z * sz);
        glm::vec3 boxMin = -0.5f * boxSize;
        glm::vec3 boxMax =  0.5f * boxSize;

        // Build/update slice quad VBO
        if (m_sliceVAO == 0) glGenVertexArrays(1, &m_sliceVAO);
        if (m_sliceVBO == 0) glGenBuffers(1, &m_sliceVBO);

        std::vector<float> quad; // positions only
        quad.reserve(6*3);
        auto clampi = [](int v, int lo, int hi){ return v<lo?lo:(v>hi?hi:v); };
        int X = (int)m_volume->dimensions.x;
        int Y = (int)m_volume->dimensions.y;
        int Z = (int)m_volume->dimensions.z;
        if (m_sliceAxis == 0) m_sliceIndex = clampi(m_sliceIndex, 0, Z-1);
        else if (m_sliceAxis == 1) m_sliceIndex = clampi(m_sliceIndex, 0, Y-1);
        else m_sliceIndex = clampi(m_sliceIndex, 0, X-1);

        if (m_sliceAxis == 0) { // Z
            float s = (m_sliceIndex + 0.5f) / float(std::max(1, Z));
            float z = glm::mix(boxMin.z, boxMax.z, s);
            glm::vec3 p0(boxMin.x, boxMin.y, z);
            glm::vec3 p1(boxMax.x, boxMin.y, z);
            glm::vec3 p2(boxMax.x, boxMax.y, z);
            glm::vec3 p3(boxMin.x, boxMax.y, z);
            auto push = [&](glm::vec3 p){ quad.push_back(p.x); quad.push_back(p.y); quad.push_back(p.z); };
            push(p0); push(p1); push(p2); push(p0); push(p2); push(p3);
        } else if (m_sliceAxis == 1) { // Y
            float s = (m_sliceIndex + 0.5f) / float(std::max(1, Y));
            float y = glm::mix(boxMin.y, boxMax.y, s);
            glm::vec3 p0(boxMin.x, y, boxMin.z);
            glm::vec3 p1(boxMax.x, y, boxMin.z);
            glm::vec3 p2(boxMax.x, y, boxMax.z);
            glm::vec3 p3(boxMin.x, y, boxMax.z);
            auto push = [&](glm::vec3 p){ quad.push_back(p.x); quad.push_back(p.y); quad.push_back(p.z); };
            push(p0); push(p1); push(p2); push(p0); push(p2); push(p3);
        } else { // X
            float s = (m_sliceIndex + 0.5f) / float(std::max(1, X));
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

    // Draw bbox on top (respect toggle)
    if (m_showBoundingBox && m_boundingBoxVAO != 0 && m_bboxProgram != 0) {
        glDisable(GL_DEPTH_TEST);
        glUseProgram(m_bboxProgram);
        glm::mat4 model(1.0f);
        glm::mat4 view = m_camera.getViewMatrix();
        glm::mat4 projection = m_camera.getProjectionMatrix();
        glUniformMatrix4fv(glGetUniformLocation(m_bboxProgram, "model"), 1, GL_FALSE, glm::value_ptr(model));
        glUniformMatrix4fv(glGetUniformLocation(m_bboxProgram, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(m_bboxProgram, "projection"), 1, GL_FALSE, glm::value_ptr(projection));
        glBindVertexArray(m_boundingBoxVAO);
        glDrawArrays(GL_LINES, 0, 24);
        glBindVertexArray(0);
        glEnable(GL_DEPTH_TEST);
    }
}

void VTKRenderer::camera_rotate(float dx, float dy) { m_camera.rotate(dx, dy); }
void VTKRenderer::camera_zoom(float delta) { m_camera.zoom(delta); }
void VTKRenderer::set_camera_angles(float azimuthDeg, float elevationDeg) { m_camera.setAngles(azimuthDeg, elevationDeg); }

void VTKRenderer::setSliceMode(bool enabled) { m_sliceMode = enabled; }
void VTKRenderer::setSliceAxis(int axis) { m_sliceAxis = std::max(0, std::min(2, axis)); }
void VTKRenderer::setSliceIndex(int index) { m_sliceIndex = std::max(0, index); }

int VTKRenderer::getNumFields() const { return static_cast<int>(m_volume ? m_volume->fields.size() : 0); }
int VTKRenderer::getCurrentFieldIndex() const { return m_currentField; }
void VTKRenderer::setCurrentFieldIndex(int idx) { m_currentField = std::max(0, std::min(idx, getNumFields()-1)); m_needsGLSetup = true; }

bool VTKRenderer::isVolumeLoaded() const { return m_volume && !m_volume->empty(); }
VTKVolumeData* VTKRenderer::getVTKVolume() { return m_volume.get(); }

unsigned int VTKRenderer::getVolumeWidth() const { return m_volume ? (unsigned)m_volume->dimensions.x : 0; }
unsigned int VTKRenderer::getVolumeHeight() const { return m_volume ? (unsigned)m_volume->dimensions.y : 0; }
unsigned int VTKRenderer::getVolumeDepth() const { return m_volume ? (unsigned)m_volume->dimensions.z : 0; }
float VTKRenderer::getSpacingX() const { return m_volume ? m_volume->spacing.x : 0.f; }
float VTKRenderer::getSpacingY() const { return m_volume ? m_volume->spacing.y : 0.f; }
float VTKRenderer::getSpacingZ() const { return m_volume ? m_volume->spacing.z : 0.f; }

void VTKRenderer::setShowBoundingBox(bool show) {
    m_showBoundingBox = show;
}

void VTKRenderer::frameCameraToBox() {
    if (!isVolumeLoaded()) return;
    float sx = std::max(0.0001f, m_volume->spacing.x);
    float sy = std::max(0.0001f, m_volume->spacing.y);
    float sz = std::max(0.0001f, m_volume->spacing.z);
    float w = m_volume->dimensions.x * sx;
    float h = m_volume->dimensions.y * sy;
    float d = m_volume->dimensions.z * sz;
    m_camera.frameBox(w, h, d);
}

void VTKRenderer::setBoundingBoxScale(float scale) {
    m_bboxScale = std::max(0.1f, std::min(5.0f, scale));
    // Rebuild bbox next frame
    m_needsGLSetup = true;
}
