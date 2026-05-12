import pygame
import random

_scanline_surface = None

def apply_crt(surface, time_ms):
    """
    Applies authentic arcade CRT effects to a pygame surface:
    - Persistent scanlines
    - Vignette (dark corners)
    - Subtle static/noise flicker
    """
    global _scanline_surface
    width, height = surface.get_size()

    # 1. SCANLINES (Pre-generated for performance)
    if _scanline_surface is None or _scanline_surface.get_size() != (width, height):
        _scanline_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 3):
            pygame.draw.line(_scanline_surface, (0, 0, 0, 60), (0, y), (width, y))
    
    surface.blit(_scanline_surface, (0, 0))

    # 2. VIGNETTE
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    # Simple radial gradient approximation using circles
    for i in range(10):
        alpha = int(40 * (i / 10.0))
        size = int(width * (1.0 + i * 0.1))
        # Draw a large circle with alpha that fades out
        # Actually a simpler vignette is to draw onto a surface and blur, 
        # but for performance we just draw a few thick borders
        rect = pygame.Rect(0, 0, width, height)
        inset = i * 20
        pygame.draw.rect(vignette, (0, 0, 0, alpha), rect.inflate(-inset, -inset), 30, border_radius=100)
    surface.blit(vignette, (0, 0))

    # 3. SUBTLE STATIC NOISE (0.5% of pixels)
    # We draw random tiny white/gray dots that flicker based on time
    if (time_ms // 100) % 2 == 0:
        for _ in range(int(width * height * 0.0005)):
            rx = random.randint(0, width - 1)
            ry = random.randint(0, height - 1)
            c = random.randint(150, 255)
            surface.set_at((rx, ry), (c, c, c, 30))

    # 4. SUBTLE SCREEN FLICKER
    if random.random() < 0.02:
        flicker = pygame.Surface((width, height), pygame.SRCALPHA)
        flicker.fill((255, 255, 255, 5))
        surface.blit(flicker, (0, 0))
