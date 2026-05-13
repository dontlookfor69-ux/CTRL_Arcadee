// scanline.shader (Godot 3 GLES2-compatible)
shader_type canvas_item;

uniform float scanline_count = 1080.0;
uniform float scanline_opacity = 0.45;

void fragment() {
    vec4 col = texture(SCREEN_TEXTURE, SCREEN_UV);
    
    // Dense Scanlines (matched to reference images)
    float line = mod(floor(SCREEN_UV.y * scanline_count), 2.0);
    float dark = 1.0 - scanline_opacity * line;
    
    col.rgb *= dark;
    
    // Phosphor color shift (Subtle RGB cast)
    col.r *= 1.02;
    col.g *= 0.98;
    col.b *= 1.01;
    
    // Vignette (Darkening corners)
    vec2 uv2 = SCREEN_UV * (1.0 - SCREEN_UV.yx);
    float vig = pow(uv2.x * uv2.y * 15.0, 0.35);
    col.rgb *= vig;
    
    // Analog TV noise
    float noise = fract(sin(dot(SCREEN_UV + vec2(float(int(TIME * 30.0)) * 0.01, 0.0), vec2(12.9898, 78.233))) * 43758.5453);
    col.rgb += noise * 0.04;

    // Horizontal sync jitter (subtle)
    float jitter = sin(TIME * 47.0 + SCREEN_UV.y * 300.0) * 0.0005;
    vec4 jitter_col = texture(SCREEN_TEXTURE, SCREEN_UV + vec2(jitter, 0.0));
    col.rgb = mix(col.rgb, jitter_col.rgb, 0.3);
    
    COLOR = col;
}
