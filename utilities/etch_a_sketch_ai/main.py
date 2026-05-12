import os
import sys
import time
import threading
import traceback
import pygame
import cv2
import numpy as np
from collections import deque

# ── Import Shared Utilities ───────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    import crt_overlay
except ImportError:
    crt_overlay = None

# ── Config ────────────────────────────────────────────────────────────────────
CANVAS_WIDTH  = 900
CANVAS_HEIGHT = 500
BG_COLOR      = (5, 5, 10)
FRAME_COLOR   = (200, 0, 0)
CANVAS_BG     = (220, 225, 210)
LINE_COLOR    = (40, 40, 45)
TEXT_COLOR    = (0, 255, 200)
WARN_COLOR    = (255, 200, 0)
DRAW_SPEED    = 100   # points per frame
LINE_WIDTH    = 2


class MagicEtch:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.w, self.h = self.screen.get_size()
        self.clock     = pygame.time.Clock()
        self.font      = pygame.font.SysFont("monospace", 22, bold=True)

        cx = (self.w - CANVAS_WIDTH) // 2
        self.canvas_rect = pygame.Rect(cx, 60, CANVAS_WIDTH, CANVAS_HEIGHT)
        self.canvas = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.fill(CANVAS_BG)

        self.points_to_draw: deque = deque()
        self.total_points   = 0
        self.drawn_points   = 0
        self.is_processing  = False
        self.last_p         = None
        self.status         = "SPACE = Camera    M = Load image.png    C = Clear    ESC = Exit"

    def log(self, msg: str):
        print(f"[ETCH] {msg}", flush=True)
        self.status = msg

    # ── [NEW] Eulerian Path Algorithm ─────────────────────────────────────────
    # We ensure the pen NEVER lifts. Every gap between contours is bridged 
    # by a connecting line, mimicking a real Etch A Sketch.
    
    def _edges_to_path(self, edges: np.ndarray, scale_x: float, scale_y: float):
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
        if not contours: return deque(), 0

        # Filter noise
        contours = [c for c in contours if cv2.arcLength(c, False) > 10]
        if not contours: return deque(), 0

        path: deque = deque()
        total = 0
        current_pos = None

        # Sort contours by proximity to keep transit lines short
        unvisited = list(contours)
        
        while unvisited:
            best_idx = 0
            best_dist = float('inf')
            
            if current_pos is not None:
                for idx, c in enumerate(unvisited):
                    # Check first point of contour
                    p0 = c[0][0]
                    dist = (p0[0]*scale_x - current_pos[0])**2 + (p0[1]*scale_y - current_pos[1])**2
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx
            
            target_contour = unvisited.pop(best_idx)
            
            # Draw transit line to the start of this contour (mimics Eulerian path)
            for pt in target_contour:
                x = int(pt[0][0] * scale_x)
                y = int(pt[0][1] * scale_y)
                x = max(0, min(CANVAS_WIDTH - 1, x))
                y = max(0, min(CANVAS_HEIGHT - 1, y))
                
                path.append((x, y))
                current_pos = (x, y)
                total += 1

        return path, total

    def process_image(self, source: str = "camera"):
        try:
            self.is_processing = True
            frame = None
            if source == "camera":
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self.log("ERROR: No camera found")
                    self.is_processing = False; return
                for _ in range(5): cap.read()
                ret, frame = cap.read(); cap.release()
                if not ret: self.is_processing = False; return
            else:
                img_p = os.path.join(SCRIPT_DIR, "image.png")
                if not os.path.exists(img_p):
                    img_p = os.path.join(os.getcwd(), "image.png")
                frame = cv2.imread(img_p)
                if frame is None:
                    self.log("ERROR: image.png not found")
                    self.is_processing = False; return

            h, w = frame.shape[:2]
            scale_x, scale_y = CANVAS_WIDTH / w, CANVAS_HEIGHT / h
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            filtered = cv2.bilateralFilter(gray, 7, 50, 50)
            
            # Canny with auto-thresholding
            v = np.median(filtered)
            edges = cv2.Canny(filtered, int(max(0, 0.66*v)), int(min(255, 1.33*v)))
            edges = cv2.dilate(edges, np.ones((2,2), np.uint8), iterations=1)

            path, total = self._edges_to_path(edges, scale_x, scale_y)
            self.canvas.fill(CANVAS_BG)
            self.points_to_draw = path
            self.total_points = total
            self.drawn_points = 0
            self.is_processing = False
            self.log(f"Tracing continuous path ({total} pts)...")
        except Exception as e:
            self.log(f"CRASH: {e}")
            self.is_processing = False

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: running = False
                    if not self.is_processing:
                        if event.key == pygame.K_SPACE:
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image, args=("camera",), daemon=True).start()
                        elif event.key == pygame.K_m:
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image, args=("file",), daemon=True).start()
                        elif event.key == pygame.K_c:
                            self.canvas.fill(CANVAS_BG); self.points_to_draw.clear()
                            self.last_p = None; self.total_points = 0; self.drawn_points = 0

            # ── Drawing Logic ─────────────────────────────────────────────────
            if self.points_to_draw and not self.is_processing:
                for _ in range(DRAW_SPEED):
                    if not self.points_to_draw: break
                    p = self.points_to_draw.popleft()
                    # Eulerian path: last_p is never None after the first point
                    if self.last_p is not None:
                        pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, LINE_WIDTH)
                    self.last_p = p
                    self.drawn_points += 1
                
                if len(self.points_to_draw) == 0:
                    self.status = "Done! SPACE = Camera  M = File  C = Clear"

            # ── Render ────────────────────────────────────────────────────────
            self.screen.fill(BG_COLOR)
            pygame.draw.rect(self.screen, FRAME_COLOR, self.canvas_rect.inflate(80, 70), border_radius=28)
            pygame.draw.rect(self.screen, (25, 25, 30), self.canvas_rect.inflate(12, 12), border_radius=8)
            self.screen.blit(self.canvas, self.canvas_rect.topleft)

            # Dials
            dy = self.canvas_rect.bottom + 35
            for dx in (self.canvas_rect.left - 38, self.canvas_rect.right + 38):
                pygame.draw.circle(self.screen, (240, 240, 240), (dx, dy), 32)
                pygame.draw.circle(self.screen, (100, 100, 100), (dx, dy), 6)

            # CRT Overlay
            if crt_overlay:
                crt_overlay.apply_crt(self.screen, pygame.time.get_ticks())

            msg = self.status + ("..." if self.is_processing else "")
            surf = self.font.render(msg[:90], True, TEXT_COLOR)
            self.screen.blit(surf, (self.w // 2 - surf.get_width() // 2, self.h - 44))

            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    MagicEtch().run()
