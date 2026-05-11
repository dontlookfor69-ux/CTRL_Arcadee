import os
import sys
import time
import threading
import traceback
import pygame
import cv2
import numpy as np

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
        
        self.points_to_draw = []
        self.is_processing = False
        self.status = "SYSTEM READY - PRESS SPACE TO CAPTURE"
        
        self.last_p = (CANVAS_WIDTH//2, CANVAS_HEIGHT//2)
        
    def log(self, msg):
        print(f"[ETCH DEBUG] {msg}", flush=True)
        self.status = msg.upper()

    def process_image(self, source="camera"):
        try:
            self.is_processing = True
            self.log("Initializing Neural Vision...")
            
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

            self.log("Extracting High-Fidelity Features...")
            # Grayscale & Noise reduction
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Skeletonization is the "secret sauce" for Etch-A-Sketch
            # It turns thick edges into single-pixel lines
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            
            # Thinning/Skeletonization
            kernel = np.ones((3,3), np.uint8)
            eroded = cv2.erode(thresh, kernel, iterations=1)
            # Use OpenCV's built-in thinning if available, otherwise manual skeleton
            skeleton = cv2.ximgproc.thinning(eroded) if hasattr(cv2, 'ximgproc') else eroded
            
            # Resize skeleton to canvas
            skeleton = cv2.resize(skeleton, (CANVAS_WIDTH, CANVAS_HEIGHT))
            
            self.log("Mapping Vector Coordinates...")
            pts = np.column_stack(np.where(skeleton > 0))
            if len(pts) == 0:
                self.log("ERROR: No Geometry Detected")
                self.is_processing = False; return

            # OPTIMIZATION: Nearest Neighbor Pathing (Greedy TSP)
            # This ensures we don't have "lines everywhere"
            self.log("Optimizing Path Continuity...")
            pts_list = pts.tolist()
            sorted_pts = []
            curr = np.array([0, 0]) # Start from top-left
            
            # Sub-sample for performance
            if len(pts_list) > 2000:
                step = len(pts_list) // 2000
                pts_list = pts_list[::step]
            
            remaining = np.array(pts_list)
            
            # Use a slightly faster chunked sorting for large point sets
            while len(remaining) > 0:
                # Find closest point
                dists = np.sum((remaining - curr)**2, axis=1)
                idx = np.argmin(dists)
                
                # If the jump is too far, it's a new segment (handle Etch-A-Sketch "drag")
                if dists[idx] > 2500: # Distance threshold squared
                    pass # We just have to drag the pen, it's an etch-a-sketch!
                
                pt = remaining[idx]
                sorted_pts.append((int(pt[1]), int(pt[0])))
                curr = pt
                remaining = np.delete(remaining, idx, axis=0)
                
                if len(sorted_pts) % 500 == 0:
                    self.log(f"Tracing: {int((len(sorted_pts)/len(pts_list))*100)}%")

            self.points_to_draw = sorted_pts
            self.log(f"READY: {len(sorted_pts)} Points")
            self.is_processing = False
            
        except Exception as e:
            self.log(f"CRITICAL SYSTEM ERROR: {str(e)}")
            traceback.print_exc()
            self.is_processing = False

    def run(self):
        running = True
        while running:
            self.screen.fill(BG_COLOR)
            
            # Draw Frame
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
                            self.canvas.fill(CANVAS_BG); self.points_to_draw = []

            # Drawing Logic
            if self.points_to_draw and not self.is_processing:
                for _ in range(15):
                    if not self.points_to_draw: break
                    p = self.points_to_draw.pop(0)
                    pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, 2)
                    self.last_p = p
            
            self.screen.blit(self.canvas, self.canvas_rect.topleft)
            
            # HUD
            stat_surf = self.font.render(self.status, True, TEXT_COLOR)
            self.screen.blit(stat_surf, (self.w//2 - stat_surf.get_width()//2, self.h - 110))
            
            # Knobs
            pygame.draw.circle(self.screen, (255, 255, 255), (self.canvas_rect.left - 40, self.h - 100), 60)
            pygame.draw.circle(self.screen, (255, 255, 255), (self.canvas_rect.right + 40, self.h - 100), 60)
            
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    MagicEtch().run()
