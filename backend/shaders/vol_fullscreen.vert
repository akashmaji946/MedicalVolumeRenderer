#version 330 core
layout (location = 0) in vec2 aPos; // NDC position [-1,1]
out vec2 vScreenPos;
void main(){
    vScreenPos = aPos;
    gl_Position = vec4(aPos, 0.0, 1.0);
}
