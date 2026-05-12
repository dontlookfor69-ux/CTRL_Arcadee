// scanline.shader (Godot 3 GLES2-compatible)
shader_type canvas_item;

uniform float scanline_count = 540.0;
uniform float scanline_opacity = 0.18;
uniform float flicker_speed = 8.0;

void fragment() {
    vec4 col = texture(SCREEN_TEXTURE, SCREEN_UV);
    
    // Scanlines
    float line = mod(floor(SCREEN_UV.y * scanline_count), 2.0);
    float dark = 1.0 - scanline_opacity * line;
    
    // Subtle time-based flicker
    float flicker = 1.0 - 0.015 * sin(TIME * flicker_speed);
    
    col.rgb *= dark * flicker;
    
    // Vignette
    vec2 uv2 = SCREEN_UV * (1.0 - SCREEN_UV.yx);
    float vig = pow(uv2.x * uv2.y * 15.0, 0.35);
    col.rgb *= vig;
    
    COLOR = col;
}
