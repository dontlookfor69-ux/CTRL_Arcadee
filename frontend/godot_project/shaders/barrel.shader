// barrel.shader (Godot 3 GLES2-compatible)
shader_type canvas_item;

uniform float curvature = 0.15;

void fragment() {
    vec2 uv = SCREEN_UV - 0.5;
    float r2 = dot(uv, uv);
    uv *= 1.0 + curvature * r2;
    uv += 0.5;
    
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        COLOR = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        // Chromatic Aberration (RGB Fringing)
        vec4 col;
        col.r = texture(SCREEN_TEXTURE, uv + vec2(0.001, 0.0)).r;
        col.g = texture(SCREEN_TEXTURE, uv).g;
        col.b = texture(SCREEN_TEXTURE, uv - vec2(0.001, 0.0)).b;
        col.a = 1.0;
        COLOR = col;
    }
}
