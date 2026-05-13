import pygame
import numpy as np

_scanline_surf = None
_vignette_surf = None
_last_size = (0, 0)

def apply_crt(surface: pygame.Surface, time_ms: int):
    """
    Applies a high-quality software CRT effect:
    1. Dense scanlines (every 2px, semi-transparent dark lines)
    2. Vignette (dark corners fading to black)
    3. Subtle green phosphor tint
    4. Very subtle full-screen flicker (brightness only, no pixels)
    
    This implementation uses blit() with SRCALPHA surfaces to avoid the 
    alpha-discard bug in set_at() on regular surfaces.
    """
    global _scanline_surf, _vignette_surf, _last_size
    
    w, h = surface.get_size()
    
    # Rebuild cached surfaces if size changed
    if (w, h) != _last_size:
        _last_size = (w, h)
        
        # --- SCANLINES ---
        # Every 2 pixels — dense like the reference images
        _scanline_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        _scanline_surf.fill((0, 0, 0, 0))
        for y in range(0, h, 2):
            pygame.draw.line(_scanline_surf, (0, 0, 0, 110), (0, y), (w, y))
        
        # --- VIGNETTE ---
        # Draw concentric border rectangles getting darker toward the corners
        _vignette_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        _vignette_surf.fill((0, 0, 0, 0))
        steps = 30
        for i in range(steps):
            alpha = int(180 * (i / steps) ** 2.5)  # Quadratic falloff for realistic vignette
            inset = int((steps - i) * (min(w, h) / (steps * 2.2)))
            rect = pygame.Rect(inset, inset, w - inset * 2, h - inset * 2)
            if rect.width > 0 and rect.height > 0:
                pygame.draw.rect(_vignette_surf, (0, 0, 0, alpha), rect, max(1, inset // 2), border_radius=inset)
    
    # --- APPLY PHOSPHOR TINT ---
    # Very subtle green cast like old monitors
    tint = pygame.Surface((w, h), pygame.SRCALPHA)
    tint.fill((0, 255, 0, 8))
    surface.blit(tint, (0, 0))
    
    # --- APPLY SCANLINES ---
    surface.blit(_scanline_surf, (0, 0))
    
    # --- APPLY VIGNETTE ---
    surface.blit(_vignette_surf, (0, 0))
    
    # --- SUBTLE BRIGHTNESS FLICKER ---
    # Dims the whole screen slightly every ~3 seconds
    flicker_cycle = (time_ms // 3000) % 7
    if flicker_cycle == 0 and (time_ms % 3000) < 50:
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 18))
        surface.blit(dim, (0, 0))
