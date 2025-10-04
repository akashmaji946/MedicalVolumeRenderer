#version 330 core
in vec3 vWorldPos;
out vec4 FragColor;

uniform sampler3D uVolume;
uniform sampler1D uLUT;     // 1D colormap
uniform vec3 uBoxMin;
uniform vec3 uBoxMax;
uniform vec3 uCamPos;
uniform float uStep; // in world units

vec3 worldToTex(vec3 p){
    return (p - uBoxMin) / (uBoxMax - uBoxMin);
}

float boxExitT(vec3 ro, vec3 rd){
    vec3 inv = 1.0/rd;
    vec3 t0 = (uBoxMin - ro) * inv;
    vec3 t1 = (uBoxMax - ro) * inv;
    vec3 tmax = max(t0, t1);
    return min(min(tmax.x, tmax.y), tmax.z);
}

void main(){
    vec3 ro = uCamPos;
    vec3 rd = normalize(vWorldPos - uCamPos);

    vec3 p = vWorldPos + rd * uStep * 0.5;

    float tExit = boxExitT(p, rd);
    float valMax = 0.0;

    for(float t=0.0; t < tExit; t += uStep){
        vec3 pw = p + rd * t;
        vec3 tc = worldToTex(pw);
        if(any(lessThan(tc, vec3(0.0))) || any(greaterThan(tc, vec3(1.0)))){
            break;
        }
        float s = texture(uVolume, tc).r;
        valMax = max(valMax, s);
    }

    FragColor = texture(uLUT, clamp(valMax, 0.0, 1.0));
}
