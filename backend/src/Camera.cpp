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
    : m_target(0.0f, 0.0f, 0.0f), m_up(0.0f, 1.0f, 0.0f),
      m_azimuth(0.0f), m_elevation(0.0f), m_radius(5.0f),
      m_fov(45.0f), m_aspectRatio(16.0f / 9.0f), m_nearPlane(0.1f), m_farPlane(100.0f)
{
    updateCameraVectors();
}

void Camera::rotate(float deltaAzimuth, float deltaElevation) {
    m_azimuth += deltaAzimuth;
    m_elevation += deltaElevation;

    // Clamp elevation to prevent flipping
    m_elevation = std::max(-89.0f, std::min(89.0f, m_elevation));

    updateCameraVectors();
}

void Camera::zoom(float deltaRadius) {
    m_radius -= deltaRadius;
    m_radius = std::max(0.1f, m_radius); // Prevent zooming inside the target
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
}

glm::mat4 Camera::getViewMatrix() const {
    // glm::lookAt creates the view matrix that transforms world coordinates to camera space
    return glm::lookAt(m_position, m_target, m_up);
}

glm::mat4 Camera::getProjectionMatrix() const {
    // Creates a perspective projection matrix
    return glm::perspective(glm::radians(m_fov), m_aspectRatio, m_nearPlane, m_farPlane);
}