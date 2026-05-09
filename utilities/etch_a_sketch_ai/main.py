import os
import sys
import time
import pygame
import cv2
import numpy as np

try:
    import evdev
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    print("Warning: evdev not available. Spinners will not work on this OS.")

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("Warning: rembg not available. Background removal disabled.")

# --- Constants ---
WIDTH, HEIGHT = 800, 600
FRAME_COLOR = (200, 30, 30) # Classic Red
BG_COLOR = (200, 200, 200) # Gray canvas
LINE_COLOR = (50, 50, 50)  # Dark gray line
KNOB_COLOR = (240, 240, 240)
TEXT_COLOR = (255, 255, 255)
CURSOR_COLOR = (255, 0, 0)
SPEED = 2

# Drawing Area (Canvas)
CANVAS_RECT = pygame.Rect(50, 50, 700, 400)

def find_spinners():
    """Find the evdev devices for the spinners (rotary encoders)."""
    if not EVDEV_AVAILABLE:
        return None, None
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    spinner_x = None
    spinner_y = None
    for dev in devices:
        if "spinner" in dev.name.lower() or "mouse" in dev.name.lower():
            if spinner_x is None:
                spinner_x = dev
            elif spinner_y is None:
                spinner_y = dev
    return spinner_x, spinner_y

def capture_and_process():
    """Capture webcam, remove background, extract edges."""
    if not REMBG_AVAILABLE:
        return None
        
    cap = cv2.VideoCapture(0)
    # Let camera warm up
    time.sleep(0.5)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Error: Could not read from webcam.")
        return None
        
    # Remove background
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = remove(img_rgb)
    
    # Convert to grayscale and get edges
    gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    
    # Resize edges to fit the drawing canvas
    edges_resized = cv2.resize(edges, (CANVAS_RECT.width, CANVAS_RECT.height))
    return edges_resized

def draw_frame(screen, font):
    """Draws the red frame, white knobs, and HUD text."""
    screen.fill(FRAME_COLOR)
    
    # Draw knobs (circles at bottom left and bottom right)
    pygame.draw.circle(screen, KNOB_COLOR, (100, 520), 50)
    pygame.draw.circle(screen, KNOB_COLOR, (700, 520), 50)
    
    # Draw HUD text
    text1 = font.render("SPACE: Capture Photo", True, TEXT_COLOR)
    text2 = font.render("C: Clear Canvas", True, TEXT_COLOR)
    text3 = font.render("ESC: Exit", True, TEXT_COLOR)
    
    screen.blit(text1, (300, 470))
    screen.blit(text2, (300, 500))
    screen.blit(text3, (300, 530))

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etch A Sketch AI")
    clock = pygame.time.Clock()
    
    try:
        font = pygame.font.SysFont("arial", 20, bold=True)
        large_font = pygame.font.SysFont("arial", 40, bold=True)
    except:
        font = pygame.font.Font(None, 30)
        large_font = pygame.font.Font(None, 50)
    
    # Persistent surface for drawing
    canvas = pygame.Surface((CANVAS_RECT.width, CANVAS_RECT.height))
    canvas.fill(BG_COLOR)
    
    spinner_x, spinner_y = find_spinners()
    
    x, y = CANVAS_RECT.width // 2, CANVAS_RECT.height // 2
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_c:
                    canvas.fill(BG_COLOR)
                elif event.key == pygame.K_SPACE:
                    # Draw "Processing" overlay
                    draw_frame(screen, font)
                    screen.blit(canvas, CANVAS_RECT.topleft)
                    
                    overlay = pygame.Surface((CANVAS_RECT.width, CANVAS_RECT.height))
                    overlay.set_alpha(150)
                    overlay.fill((0, 0, 0))
                    screen.blit(overlay, CANVAS_RECT.topleft)
                    
                    proc_text = large_font.render("PROCESSING IMAGE...", True, (255, 255, 255))
                    text_rect = proc_text.get_rect(center=CANVAS_RECT.center)
                    screen.blit(proc_text, text_rect)
                    pygame.display.flip()
                    
                    # Capture and process
                    edges = capture_and_process()
                    if edges is not None:
                        for row in range(CANVAS_RECT.height):
                            for col in range(CANVAS_RECT.width):
                                if edges[row, col] > 128:
                                    pygame.draw.rect(canvas, LINE_COLOR, (col, row, 1, 1))

        # Handle keyboard for testing
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]: dx = -SPEED
        if keys[pygame.K_RIGHT]: dx = SPEED
        if keys[pygame.K_UP]: dy = -SPEED
        if keys[pygame.K_DOWN]: dy = SPEED

        # Handle evdev spinners
        if spinner_x is not None:
            try:
                for event in spinner_x.read():
                    if event.type == evdev.ecodes.EV_REL:
                        if event.code == evdev.ecodes.REL_X:
                            dx += event.value
            except BlockingIOError:
                pass
                
        if spinner_y is not None:
            try:
                for event in spinner_y.read():
                    if event.type == evdev.ecodes.EV_REL:
                        if event.code in (evdev.ecodes.REL_Y, evdev.ecodes.REL_X, evdev.ecodes.REL_WHEEL):
                            dy += event.value
            except BlockingIOError:
                pass

        if dx != 0 or dy != 0:
            new_x = max(0, min(CANVAS_RECT.width - 1, x + dx))
            new_y = max(0, min(CANVAS_RECT.height - 1, y + dy))
            pygame.draw.line(canvas, LINE_COLOR, (x, y), (new_x, new_y), 2)
            x, y = new_x, new_y

        # Render everything
        draw_frame(screen, font)
        
        # Draw canvas border
        pygame.draw.rect(screen, (0, 0, 0), CANVAS_RECT.inflate(4, 4), 4)
        
        # Blit canvas
        screen.blit(canvas, CANVAS_RECT.topleft)
        
        # Draw cursor on canvas
        cursor_pos = (CANVAS_RECT.left + int(x), CANVAS_RECT.top + int(y))
        pygame.draw.circle(screen, CURSOR_COLOR, cursor_pos, 3)
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
