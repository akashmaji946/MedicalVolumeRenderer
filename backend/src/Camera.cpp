//
// Created by akashmaji on 10/4/25.
//

// backend/src/Camera.cpp

#include "../include/Camera.h"
#include <cmath>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

Camera::Camera()
    : m_target(0.0f, 0.0f, 0.0f), m_up(0.0f, 1.0f, 0.0f), m_right(1.0f, 0.0f, 0.0f),
      m_azimuth(0.0f), m_elevation(0.0f), m_radius(5.0f),
      m_fov(45.0f), m_aspectRatio(16.0f / 9.0f), m_nearPlane(0.1f), m_farPlane(100.0f)
{
    updateCameraVectors();
}

void Camera::rotate(float deltaAzimuth, float deltaElevation) {
    m_azimuth += deltaAzimuth;
    m_elevation += deltaElevation;
    
    // Wrap azimuth to keep it bounded
    while (m_azimuth >= 360.0f) m_azimuth -= 360.0f;
    while (m_azimuth <   0.0f)  m_azimuth += 360.0f;
    
    // Clamp elevation to prevent gimbal lock at poles (stay just shy of ±90°)
    m_elevation = std::max(-89.9f, std::min(89.9f, m_elevation));

    updateCameraVectors();
}

void Camera::zoom(float deltaRadius) {
    m_radius -= deltaRadius;
    m_radius = std::max(0.1f, m_radius); // Prevent zooming inside the target
    updateCameraVectors();
}

void Camera::setAngles(float azimuthDeg, float elevationDeg) {
    m_azimuth = azimuthDeg;
    // Wrap azimuth to [0,360)
    while (m_azimuth >= 360.0f) m_azimuth -= 360.0f;
    while (m_azimuth <   0.0f)  m_azimuth += 360.0f;
    // Clamp elevation to avoid gimbal lock
    m_elevation = std::max(-89.9f, std::min(89.9f, elevationDeg));
    updateCameraVectors();
}

void Camera::setAspectRatio(float aspect) {
    m_aspectRatio = aspect;
}

void Camera::updateCameraVectors() {
    // Calculate position from spherical coordinates
    float elev_rad = glm::radians(m_elevation);
    float azim_rad = glm::radians(m_azimuth);

    m_position.x = m_radius * cos(elev_rad) * sin(azim_rad);
    m_position.y = m_radius * sin(elev_rad);
    m_position.z = m_radius * cos(elev_rad) * cos(azim_rad);

    // Build stable orthonormal basis (elevation is clamped, so no pole crossing)
    glm::vec3 forward = glm::normalize(m_target - m_position);
    const glm::vec3 worldUp(0.0f, 1.0f, 0.0f);
    
    m_right = glm::normalize(glm::cross(worldUp, forward));
    m_up = glm::normalize(glm::cross(forward, m_right));
}

glm::mat4 Camera::getViewMatrix() const {
    // glm::lookAt creates the view matrix that transforms world coordinates to camera space
    return glm::lookAt(m_position, m_target, m_up);
}

glm::mat4 Camera::getProjectionMatrix() const {
    // Creates a perspective projection matrix
    return glm::perspective(glm::radians(m_fov), m_aspectRatio, m_nearPlane, m_farPlane);
}

void Camera::frameBox(float w, float h, float d) {
    // Ensure positive sizes
    w = std::max(w, 1e-3f);
    h = std::max(h, 1e-3f);
    d = std::max(d, 1e-3f);

    // Frame the box centered at origin. Choose a gentle default angle
    m_azimuth = 45.0f;
    m_elevation = 20.0f;

    // Compute radius so the largest dimension fits within the vertical FOV
    float boxRadius = 0.5f * std::sqrt(w*w + h*h + d*d);
    float fovRad = glm::radians(m_fov);
    // distance to fit the sphere of radius boxRadius inside view cone
    float dist = boxRadius / std::sin(fovRad * 0.5f);
    // Keep some margin
    m_radius = dist * 1.2f;

    // Adjust clipping planes so the box is not clipped
    // Place near a bit in front of the camera target distance, far beyond the box
    float nearTarget = std::max(0.01f, m_radius - 2.0f * boxRadius);
    float farTarget  = std::max(nearTarget + 1.0f, m_radius + 2.0f * boxRadius);
    m_nearPlane = nearTarget;
    m_farPlane  = farTarget;

    // Focus the camera at the center
    m_target = glm::vec3(0.0f, 0.0f, 0.0f);
    m_up = glm::vec3(0.0f, 1.0f, 0.0f);
    m_right = glm::vec3(1.0f, 0.0f, 0.0f);

    // Update position
    updateCameraVectors();
}