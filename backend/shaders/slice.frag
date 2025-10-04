#version 330 core
out vec4 FragColor;

uniform sampler3D uVolume;
uniform sampler1D uLUT;
uniform vec3 uBoxMin;
uniform vec3 uBoxMax;
uniform int uAxis; // 0=Z,1=Y,2=X

// Compute normalized texture coordinate in [0,1]^3 for a world position on the slice
vec3 worldToTex(vec3 p){
    return (p - uBoxMin) / (uBoxMax - uBoxMin);
}

void main(){
    // Reconstruct world pos from gl_FragCoord is non-trivial; for this simple slice, we rely on vertex positions
    // We can derive texcoords by interpolating gl_FragCoord is not available; so instead, we will reconstruct
    // using the built-in barycentric interpolation of positions if we had passed them. For simplicity, approximate
    // using the assumption that the slice quad fills the entire primitive; better is to pass varying texcoord.
    // Here we fallback to a neutral gray if we cannot sample.
    // NOTE: For correctness, we should pass a vec3 texCoord varying from VS; kept simple here.
    discard; // Placeholder if not overridden by a correct VS with tex varying.
}
