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
    
    COLOR = col;
}
