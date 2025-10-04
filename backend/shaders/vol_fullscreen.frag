#version 330 core
in vec2 vScreenPos;
out vec4 FragColor;

uniform sampler3D uVolume;
uniform sampler1D uLUT;
uniform vec3 uBoxMin;
uniform vec3 uBoxMax;
uniform vec3 uCamPos;
uniform mat4 uInvViewProj;
uniform float uStep;

vec3 worldToTex(vec3 p){
    return (p - uBoxMin) / (uBoxMax - uBoxMin);
}

bool boxIntersect(vec3 ro, vec3 rd, out float t0, out float t1){
    vec3 inv = 1.0/rd;
    vec3 t0s = (uBoxMin - ro) * inv;
    vec3 t1s = (uBoxMax - ro) * inv;
    vec3 tsmaller = min(t0s, t1s);
    vec3 tbigger  = max(t0s, t1s);
    t0 = max(max(tsmaller.x, tsmaller.y), tsmaller.z);
    t1 = min(min(tbigger.x,  tbigger.y),  tbigger.z);
    return t1 >= t0;
}

void main(){
    // Reconstruct world position from screen position
    vec4 clipPos = vec4(vScreenPos, 0.0, 1.0);
    vec4 worldPos = uInvViewProj * clipPos;
    worldPos /= worldPos.w;
    
    vec3 ro = uCamPos;
    vec3 rd = normalize(worldPos.xyz - uCamPos);

    float tEnter, tExit;
    if (!boxIntersect(ro, rd, tEnter, tExit)) {
        discard;
    }

    float tStart = max(tEnter, 0.0) + uStep * 0.5;
    float tEnd   = tExit;
    if (tEnd <= tStart) {
        discard;
    }

    float valMax = 0.0;
    for (float t = tStart; t < tEnd; t += uStep) {
        vec3 pw = ro + rd * t;
        vec3 tc = worldToTex(pw);
        if (any(lessThan(tc, vec3(0.0))) || any(greaterThan(tc, vec3(1.0)))) {
            break;
        }
        float s = texture(uVolume, tc).r;
        valMax = max(valMax, s);
    }

    FragColor = texture(uLUT, clamp(valMax, 0.0, 1.0));
}
