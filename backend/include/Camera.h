//
// Created by akashmaji on 10/4/25.
//

// backend/include/Camera.h

#ifndef CAMERA_H
#define CAMERA_H

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

class Camera {
public:
    Camera();

    void rotate(float deltaAzimuth, float deltaElevation);
    void zoom(float deltaRadius);
    void setAspectRatio(float aspect);

    // Position the camera to frame an axis-aligned box of size w x h x d centered at the origin
    void frameBox(float w, float h, float d);

    glm::mat4 getViewMatrix() const;
    glm::mat4 getProjectionMatrix() const;

private:
    void updateCameraVectors();

    glm::vec3 m_position;
    glm::vec3 m_target;
    glm::vec3 m_up;

    float m_azimuth;    // Horizontal angle
    float m_elevation;  // Vertical angle
    float m_radius;     // Distance from target

    float m_fov;
    float m_aspectRatio;
    float m_nearPlane;
    float m_farPlane;
};

#endif //CAMERA_H