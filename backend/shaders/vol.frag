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
    // Build ray from camera through this fragment
    vec3 ro = uCamPos;
    vec3 rd = normalize(vWorldPos - uCamPos);

    float tEnter, tExit;
    if (!boxIntersect(ro, rd, tEnter, tExit)) {
        discard; // ray misses the volume box
    }

    // If starting inside, tEnter may be negative; clamp to 0 so we start at the camera
    float tStart = max(tEnter, 0.0) + uStep * 0.5;
    float tEnd   = tExit;
    if (tEnd <= tStart) {
        discard;
    }

    float valMax = 0.0;
    for (float t = tStart; t < tEnd; t += uStep) {
        vec3 pw = ro + rd * t;
        vec3 tc = worldToTex(pw);
        // Clamp check is not strictly needed since slabs limited [tStart,tEnd], but keep safety
        if (any(lessThan(tc, vec3(0.0))) || any(greaterThan(tc, vec3(1.0)))) {
            break;
        }
        float s = texture(uVolume, tc).r;
        valMax = max(valMax, s);
    }

    FragColor = texture(uLUT, clamp(valMax, 0.0, 1.0));
}
