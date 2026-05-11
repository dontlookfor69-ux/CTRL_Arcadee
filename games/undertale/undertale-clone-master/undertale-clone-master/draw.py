#!/usr/bin/python3
#  coding=utf-8
import math
import pygame
import globals

class Layer:
    def __init__(self):
        self.surface = pygame.Surface((globals.width, globals.height), pygame.SRCALPHA, 32).convert_alpha()
        self.surface_draw = self.surface.copy()
        self.shift = (0, 0)
        self.weight = 0
        self.draw = True
        self.want_removed = False

    def hide(self): self.draw = False
    def show(self): self.draw = True
    def __del__(self): self.destroy()

    def destroy(self):
        self.weight = math.inf
        self.draw = False
        self.want_removed = True

    def flip(self):
        self.surface_draw = self.surface.copy()

    def clear(self):
        self.surface.fill(pygame.Color(0, 0, 0, 0))

def render():
    """Main rendering function to be called from the main thread loop."""
    if not globals.display: return
    
    # Sort layers by weight
    layer_keys = sorted(globals.layers.keys(), reverse=True)
    
    for k in layer_keys:
        layer = globals.layers.get(k)
        if not layer: continue
        
        if layer.want_removed:
            globals.layers.pop(k)
        elif layer.draw:
            globals.display.blit(layer.surface_draw, layer.shift)
    
    # Scale to full screen if needed
    if hasattr(globals, 'real_display') and globals.real_display:
        scaled = pygame.transform.scale(globals.display, globals.real_display.get_size())
        globals.real_display.blit(scaled, (0, 0))
    
    pygame.display.flip()

def init():
    # Threading removed for stability on Raspberry Pi
    print("[UNDERTALE] Renderer initialized (Synchronous)")

def get_layer(weight: int) -> Layer:
    if weight in globals.layers:
        return globals.layers[weight]
    l = Layer()
    l.weight = weight
    globals.layers.update({weight: l})
    return l
