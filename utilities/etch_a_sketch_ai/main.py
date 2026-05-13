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
UTILS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, UTILS_DIR)
try:
    import crt_overlay
except ImportError:
    crt_overlay = None

# ── Config ────────────────────────────────────────────────────────────────────
CANVAS_WIDTH  = 1200 
CANVAS_HEIGHT = 700
BG_COLOR      = (5, 5, 15)
FRAME_COLOR   = (255, 30, 60) # [BRIGHTER] Retro Red
CANVAS_BG     = (245, 248, 245)
LINE_COLOR    = (35, 35, 40)
TEXT_COLOR    = (0, 255, 200)
DRAW_SPEED    = 250
LINE_WIDTH    = 2

class MagicEtch:
    def __init__(self):
        pygame.init()
        pygame.mixer.pre_init(44100, -16, 2, 4096)
        
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.w, self.h = self.screen.get_size()
        self.clock     = pygame.time.Clock()
        
        try:
            self.font_key = pygame.font.SysFont("monospace", 20, bold=True)
            self.font_desc = pygame.font.SysFont("monospace", 16)
        except:
            self.font_key = pygame.font.Font(None, 24)
            self.font_desc = pygame.font.Font(None, 20)

        cx = (self.w - CANVAS_WIDTH) // 2
        cy = (self.h - CANVAS_HEIGHT) // 2 - 40
        self.canvas_rect = pygame.Rect(cx, cy, CANVAS_WIDTH, CANVAS_HEIGHT)
        self.canvas = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.fill(CANVAS_BG)

        self.points_to_draw: deque = deque()
        self.total_points   = 0
        self.drawn_points   = 0
        self.is_processing  = False
        self.last_p         = None
        
        self.cursor_x = CANVAS_WIDTH // 2
        self.cursor_y = CANVAS_HEIGHT // 2
        self.manual_last_p = (self.cursor_x, self.cursor_y)

    def _edges_to_path(self, edges: np.ndarray, scale_x: float, scale_y: float):
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
        if not contours: return deque(), 0
        contours = [c for c in contours if cv2.arcLength(c, True) > 20]
        if not contours: return deque(), 0

        path: deque = deque()
        total = 0
        unvisited = []
        for c in contours:
            pts = []
            for pt in c:
                x = int(pt[0][0] * scale_x)
                y = int(pt[0][1] * scale_y)
                pts.append((max(0, min(CANVAS_WIDTH-1, x)), max(0, min(CANVAS_HEIGHT-1, y))))
            unvisited.append(pts)

        current_pos = (self.cursor_x, self.cursor_y)
        while unvisited:
            best_dist = float('inf'); best_idx = -1; start_at = 0
            for i, c in enumerate(unvisited):
                for p_idx, p in enumerate(c):
                    d = (p[0]-current_pos[0])**2 + (p[1]-current_pos[1])**2
                    if d < best_dist:
                        best_dist = d; best_idx = i; start_at = p_idx
            target = unvisited.pop(best_idx)
            ordered_contour = target[start_at:] + target[:start_at]
            for pt in ordered_contour:
                path.append(pt); total += 1
            current_pos = ordered_contour[-1]
        return path, total

    def process_image(self, source: str = "camera"):
        try:
            self.is_processing = True
            frame = None
            if source == "camera":
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self.is_processing = False; return
                for _ in range(5): cap.read()
                ret, frame = cap.read(); cap.release()
                if not ret: self.is_processing = False; return
            else:
                img_p = os.path.join(SCRIPT_DIR, "image.png")
                if not os.path.exists(img_p): img_p = os.path.join(os.getcwd(), "image.png")
                frame = cv2.imread(img_p)
                if frame is None: self.is_processing = False; return

            frame = cv2.resize(frame, (800, 600))
            h, w = frame.shape[:2]
            scale_x, scale_y = CANVAS_WIDTH / w, CANVAS_HEIGHT / h
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            edges = cv2.Canny(filtered, 50, 150)
            kernel = np.ones((2,2), np.uint8)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            path, total = self._edges_to_path(edges, scale_x, scale_y)
            self.canvas.fill(CANVAS_BG)
            self.points_to_draw = path
            self.total_points = total; self.drawn_points = 0; self.is_processing = False
        except Exception as e:
            print(f"CRASH: {traceback.format_exc()}"); self.is_processing = False

    def _draw_controls_bar(self):
        bar_y = self.h - 80
        bar_rect = pygame.Rect(0, bar_y, self.w, 80)
        pygame.draw.rect(self.screen, (10, 10, 25), bar_rect)
        pygame.draw.line(self.screen, (0, 180, 140), (0, bar_y), (self.w, bar_y), 2)
        controls = [("SPACE", "Snap"), ("M", "Load"), ("C", "Clear"), ("↑↓←→", "Manual Draw"), ("ESC", "Exit")]
        col_width = self.w // len(controls)
        for i, (key, desc) in enumerate(controls):
            x = i * col_width + col_width // 2
            key_surf = self.font_key.render(f"[{key}]", True, (0, 255, 200))
            self.screen.blit(key_surf, key_surf.get_rect(center=(x, bar_y + 22)))
            desc_surf = self.font_desc.render(desc, True, (160, 160, 160))
            self.screen.blit(desc_surf, desc_surf.get_rect(center=(x, bar_y + 52)))

    def run(self):
        running = True
        while running:
            current_time = pygame.time.get_ticks()
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

            # [NEW] Manual drawing whenever AI is not active
            if not self.is_processing and not self.points_to_draw:
                keys = pygame.key.get_pressed()
                moved = False; spd = 4
                if keys[pygame.K_LEFT]:  self.cursor_x = max(0, self.cursor_x - spd); moved = True
                if keys[pygame.K_RIGHT]: self.cursor_x = min(CANVAS_WIDTH-1, self.cursor_x + spd); moved = True
                if keys[pygame.K_UP]:    self.cursor_y = max(0, self.cursor_y - spd); moved = True
                if keys[pygame.K_DOWN]:  self.cursor_y = min(CANVAS_HEIGHT-1, self.cursor_y + spd); moved = True
                if moved:
                    pygame.draw.line(self.canvas, LINE_COLOR, self.manual_last_p, (self.cursor_x, self.cursor_y), LINE_WIDTH)
                    self.manual_last_p = (self.cursor_x, self.cursor_y)
                else: self.manual_last_p = (self.cursor_x, self.cursor_y)

            if self.points_to_draw and not self.is_processing:
                for _ in range(DRAW_SPEED):
                    if not self.points_to_draw: break
                    p = self.points_to_draw.popleft()
                    if self.last_p is not None: pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, LINE_WIDTH)
                    self.last_p = p; self.drawn_points += 1; self.cursor_x, self.cursor_y = p
                self.manual_last_p = (self.cursor_x, self.cursor_y)

            self.screen.fill(BG_COLOR)
            pygame.draw.rect(self.screen, FRAME_COLOR, self.canvas_rect.inflate(80, 70), border_radius=28)
            pygame.draw.rect(self.screen, (25, 25, 30), self.canvas_rect.inflate(12, 12), border_radius=8)
            self.screen.blit(self.canvas, self.canvas_rect.topleft)
            dy = self.canvas_rect.bottom + 35
            for dx in (self.canvas_rect.left - 38, self.canvas_rect.right + 38):
                pygame.draw.circle(self.screen, (240, 240, 240), (dx, dy), 32)
                pygame.draw.circle(self.screen, (100, 100, 100), (dx, dy), 6)
            self._draw_controls_bar()
            if crt_overlay: crt_overlay.apply_crt(self.screen, current_time)
            
            # Reduce CRT washout on the canvas area
            canvas_brighten = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
            canvas_brighten.fill((255, 255, 255, 35))  # Very subtle white overlay to counteract darkening
            self.screen.blit(canvas_brighten, self.canvas_rect.topleft)

            if self.is_processing:
                overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0,0))
                proc_text = self.font_key.render("AI IS ANALYZING IMAGE...", True, (255, 255, 255))
                self.screen.blit(proc_text, proc_text.get_rect(center=(self.w//2, self.h//2)))
            pygame.display.flip(); self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    MagicEtch().run()
