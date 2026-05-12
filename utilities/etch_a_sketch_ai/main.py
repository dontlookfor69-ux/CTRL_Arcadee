import os
import sys
import time
import threading
import traceback
import pygame
import cv2
import numpy as np
from collections import deque
from scipy.spatial import cKDTree

# --- Configuration ---
CANVAS_WIDTH, CANVAS_HEIGHT = 900, 500
BG_COLOR = (5, 5, 10)
FRAME_COLOR = (200, 0, 0)
CANVAS_BG = (220, 225, 210)
LINE_COLOR = (40, 40, 45)
TEXT_COLOR = (0, 255, 200)

class MagicEtch:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.w, self.h = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24, bold=True)
        
        self.canvas_rect = pygame.Rect((self.w - CANVAS_WIDTH)//2, 60, CANVAS_WIDTH, CANVAS_HEIGHT)
        self.canvas = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.fill(CANVAS_BG)
        
        self.points_to_draw = deque()
        self.is_processing = False
        self.status = "SYSTEM READY - PRESS SPACE TO CAPTURE"
        
        self.last_p = (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)
        
    def log(self, msg):
        print(f"[ETCH DEBUG] {msg}", flush=True)
        self.status = msg.upper()

    def _sort_points_kdtree(self, pts):
        """O(n log n) nearest-neighbor path using KD-tree."""
        if len(pts) == 0: return deque()
        tree = cKDTree(pts)
        visited = set()
        path = deque()
        current = 0
        visited.add(0)
        path.append((int(pts[0][1]), int(pts[0][0])))
        
        PEN_LIFT_THRESH = 30  # pixels
        
        for i in range(len(pts) - 1):
            # Query k=10 to find the closest unvisited point
            dists, idxs = tree.query(pts[current], k=min(10, len(pts)))
            next_idx = None
            next_dist = 0
            for d, idx in zip(dists, idxs):
                if idx not in visited:
                    next_idx = idx
                    next_dist = d
                    break
            
            if next_idx is None: break
            
            if next_dist > PEN_LIFT_THRESH:
                path.append(None) # pen lift
                
            visited.add(next_idx)
            path.append((int(pts[next_idx][1]), int(pts[next_idx][0])))
            current = next_idx
            
            if i % 500 == 0:
                self.log(f"Tracing: {int((i / len(pts)) * 100)}%")
                
        return path

    def process_image(self, source="camera"):
        try:
            self.is_processing = True
            self.log("Initializing Vision Pipeline...")

            frame = None
            if source == "camera":
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self.log("ERROR: Camera Offline")
                    self.is_processing = False; return
                time.sleep(1.0)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    self.log("ERROR: Frame Capture Failed")
                    self.is_processing = False; return
            else:
                p = os.path.join(os.path.dirname(__file__), "image.png")
                if not os.path.exists(p):
                    self.log("ERROR: Missing image.png")
                    self.is_processing = False; return
                frame = cv2.imread(p)

            self.log("Running Edge Detection (Canny)...")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(gray, threshold1=50, threshold2=150)

            # Optional: thin further if ximgproc is available
            if hasattr(cv2, 'ximgproc') and hasattr(cv2.ximgproc, 'thinning'):
                edges = cv2.ximgproc.thinning(edges)
            else:
                kernel = np.ones((2, 2), np.uint8)
                edges = cv2.erode(edges, kernel, iterations=1)

            edges = cv2.resize(edges, (CANVAS_WIDTH, CANVAS_HEIGHT))

            self.log("Extracting Contour Points...")
            pts = np.column_stack(np.where(edges > 0)) # y, x
            if len(pts) == 0:
                self.log("ERROR: No Edges Detected")
                self.is_processing = False; return

            if len(pts) > 3000:
                step = len(pts) // 3000
                pts = pts[::step]

            self.log(f"Sorting {len(pts)} points via KD-Tree...")
            self.points_to_draw = self._sort_points_kdtree(pts)
            self.last_p = (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)
            self.log(f"READY: {len(self.points_to_draw)} path nodes")
            self.is_processing = False

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            traceback.print_exc()
            self.is_processing = False

    def run(self):
        running = True
        while running:
            self.screen.fill(BG_COLOR)
            pygame.draw.rect(self.screen, FRAME_COLOR, self.canvas_rect.inflate(100, 100), border_radius=40)
            pygame.draw.rect(self.screen, (30, 30, 35), self.canvas_rect.inflate(20, 20), border_radius=10)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: running = False
                    if not self.is_processing:
                        if event.key == pygame.K_SPACE:
                            threading.Thread(target=self.process_image, args=("camera",), daemon=True).start()
                        if event.key == pygame.K_m:
                            threading.Thread(target=self.process_image, args=("file",), daemon=True).start()
                        if event.key == pygame.K_c:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw = deque()
                            self.last_p = (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)

            if self.points_to_draw and not self.is_processing:
                for _ in range(20):
                    if not self.points_to_draw: break
                    p = self.points_to_draw.popleft()
                    if p is None:
                        if self.points_to_draw:
                            self.last_p = self.points_to_draw[0] if self.points_to_draw[0] is not None else self.last_p
                    else:
                        pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, 2)
                        self.last_p = p
            
            self.screen.blit(self.canvas, self.canvas_rect.topleft)
            stat_surf = self.font.render(self.status, True, TEXT_COLOR)
            self.screen.blit(stat_surf, (self.w//2 - stat_surf.get_width()//2, self.h - 110))
            pygame.draw.circle(self.screen, (255, 255, 255), (self.canvas_rect.left - 40, self.h - 100), 60)
            pygame.draw.circle(self.screen, (255, 255, 255), (self.canvas_rect.right + 40, self.h - 100), 60)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    MagicEtch().run()
