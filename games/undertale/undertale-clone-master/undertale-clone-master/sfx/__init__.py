#!/usr/bin/python3
# coding=utf-8
import pygame
import os

sounds = {}
LOADED = False

def load_all_sounds():
    """
    Explicitly load all sounds. This must be called AFTER pygame.mixer.init().
    """
    global LOADED
    if LOADED:
        return
    
    print("[UNDERTALE SFX] Loading sounds...")
    # Use absolute path relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        files = os.listdir(base_dir)
        for i in files:
            if i.endswith('.wav') or i.endswith('.ogg'):
                try:
                    sound_id = int(i.split('.')[0], 16)
                    full_path = os.path.join(base_dir, i)
                    sounds[sound_id] = pygame.mixer.Sound(full_path)
                except (ValueError, pygame.error) as e:
                    # print(f"[UNDERTALE SFX] Could not load {i}: {e}")
                    pass
        LOADED = True
        print(f"[UNDERTALE SFX] Successfully loaded {len(sounds)} sounds.")
    except Exception as e:
        print(f"[UNDERTALE SFX] Fatal error in load_all_sounds: {e}")

def get_sound(sound) -> pygame.mixer.Sound:
    """
    Return a Sound with this identifier.
    """
    if not LOADED:
        load_all_sounds()
        
    try:
        # Try to parse string ID like '0x123'
        if isinstance(sound, str):
            sound = int(sound, 0)
        return sounds[sound]
    except (KeyError, TypeError, ValueError):
        # Return a silent dummy sound if not found
        return pygame.mixer.Sound(buffer=bytes([0]*44100))
