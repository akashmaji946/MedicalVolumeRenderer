#version 330 core
in vec3 vWorldPos;
out vec4 FragColor;

uniform sampler3D uVolume;
uniform sampler1D uLUT;
uniform vec3 uBoxMin;
uniform vec3 uBoxMax;
uniform int uAxis; // 0=Z,1=Y,2=X (reserved if needed later)

vec3 worldToTex(vec3 p){
    return (p - uBoxMin) / (uBoxMax - uBoxMin);
}

void main(){
    vec3 tc = worldToTex(vWorldPos);
    // Clamp to [0,1] to avoid sampling outside volume
    if (any(lessThan(tc, vec3(0.0))) || any(greaterThan(tc, vec3(1.0)))){
        discard;
    }
    float val = texture(uVolume, tc).r;
    FragColor = texture(uLUT, clamp(val, 0.0, 1.0));
}
