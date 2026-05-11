#!/usr/bin/python3
# coding=utf-8
"""
Undertale Clone Launcher — Ultra Robust Edition
Logs to stdout and /tmp/undertale_v3.log
"""

import sys
import os
import time
import traceback

LOG_PATH = "/tmp/undertale_v3.log"

def dbg(msg):
    line = f"[UNDERTALE] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a") as f: f.write(f"{time.strftime('%H:%M:%S')} {line}\n")
    except: pass

# --- Initial Setup ---
try:
    with open(LOG_PATH, "w") as f: f.write("=== START ===\n")
except: pass

dbg(f"Python: {sys.version}")
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

# --- Pygame Init ---
dbg("Initializing Pygame...")
import pygame
try:
    pygame.init()
    pygame.mixer.init()
    dbg("Pygame OK")
except Exception as e:
    dbg(f"Pygame Init Failed: {e}")
    sys.exit(1)

# --- Display Setup ---
dbg("Setting up display...")
try:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    dbg(f"Fullscreen OK: {screen.get_size()}")
except:
    dbg("Fullscreen failed, using windowed...")
    screen = pygame.display.set_mode((640, 480))

# --- Late Imports ---
dbg("Loading game modules...")
try:
    import globals as g
    import sfx
    sfx.load_all_sounds() 
    
    import frisk
    import rooms
    import sprite
    import typer
    import draw
    dbg("Modules OK")
except Exception as e:
    dbg(f"Module Load Error: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- Globals setup ---
g.real_display = screen
g.display = pygame.Surface((640, 480))

def main():
    dbg("Starting game loop...")
    try:
        g.start_time = time.time()
        chara = frisk.Frisk()
        try:
            chara.load('file0')
        except:
            dbg("No save found, using intro room")
            g.room = rooms.room_introstory()
        
        g.chara = chara
        draw.init()
        
        # Room enter logic (Safe thread)
        import threading
        t = threading.Thread(target=g.room.on_enter, daemon=True)
        t.start()

        clock = pygame.time.Clock()
        while g.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    g.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        g.running = False
            
            if g.room:
                g.room.draw()
            
            # Use our new synchronous renderer
            draw.render()
            clock.tick(30)
            
    except Exception as e:
        dbg(f"Runtime Exception: {e}")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()
