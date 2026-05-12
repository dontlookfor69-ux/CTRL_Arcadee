import os
import sys
import time
import threading
import traceback
import pygame
import cv2
import numpy as np
from collections import deque

# ── Config ────────────────────────────────────────────────────────────────────
CANVAS_WIDTH  = 900
CANVAS_HEIGHT = 500
BG_COLOR      = (5, 5, 10)
FRAME_COLOR   = (200, 0, 0)
CANVAS_BG     = (220, 225, 210)
LINE_COLOR    = (40, 40, 45)
TEXT_COLOR    = (0, 255, 200)
WARN_COLOR    = (255, 200, 0)
DRAW_SPEED    = 80   # points per frame — raise for faster drawing
LINE_WIDTH    = 2

# Resolve script directory reliably regardless of working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class MagicEtch:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Etch A Sketch AI")
        self.w, self.h = self.screen.get_size()
        self.clock     = pygame.time.Clock()
        self.font      = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_sm   = pygame.font.SysFont("monospace", 16)

        # Canvas sits centred horizontally, below the top
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

    # ── Logging ───────────────────────────────────────────────────────────────
    def log(self, msg: str):
        print(f"[ETCH] {msg}", flush=True)
        self.status = msg

    # ── Core algorithm: contour-following ─────────────────────────────────────
    # The old KD-tree approach connects random nearby pixels → ugly zigzags.
    # cv2.findContours returns ORDERED point sequences along each edge, so
    # each contour is already a smooth stroke.  O(n) instead of O(n log n),
    # and the result looks like a real pen drawing.

    def _edges_to_path(self, edges: np.ndarray, scale_x: float, scale_y: float):
        """Convert a Canny edge image into an ordered drawing path."""
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_TC89_KCOS,   # smooth approximation of curves
        )

        if not contours:
            return deque(), 0

        # Drop noise (very short contours add clutter, no detail)
        contours = [c for c in contours if cv2.arcLength(c, False) > 8]

        # Longest first → important features appear before fine detail
        contours = sorted(contours, key=lambda c: len(c), reverse=True)

        path: deque = deque()
        total = 0
        for contour in contours:
            first_in_contour = True
            for pt in contour:
                x = int(pt[0][0] * scale_x)
                y = int(pt[0][1] * scale_y)
                # Clamp to canvas
                x = max(0, min(CANVAS_WIDTH  - 1, x))
                y = max(0, min(CANVAS_HEIGHT - 1, y))
                if first_in_contour:
                    path.append(None)   # pen lift: move without drawing
                    first_in_contour = False
                path.append((x, y))
                total += 1

        return path, total

    # ── Image processing (runs on worker thread) ──────────────────────────────
    def process_image(self, source: str = "camera"):
        try:
            self.is_processing = True
            self.last_p = None
            frame = None

            # ── Capture / load ────────────────────────────────────────────────
            if source == "camera":
                self.log("Opening camera...")
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    self.log("ERROR: No camera found — connect a USB webcam")
                    self.is_processing = False
                    return
                # Discard the first few frames — cameras need a warm-up moment
                for _ in range(6):
                    cap.read()
                    time.sleep(0.05)
                ret, frame = cap.read()
                cap.release()
                if not ret or frame is None:
                    self.log("ERROR: Camera read failed")
                    self.is_processing = False
                    return
                self.log("Camera capture OK")

            else:   # source == "file"
                # Search common locations for image.png / image.jpg
                candidates = [
                    os.path.join(SCRIPT_DIR, "image.png"),
                    os.path.join(SCRIPT_DIR, "image.jpg"),
                    os.path.join(SCRIPT_DIR, "image.jpeg"),
                    os.path.join(os.getcwd(), "image.png"),
                    os.path.join(os.getcwd(), "image.jpg"),
                ]
                img_path = next((p for p in candidates if os.path.isfile(p)), None)
                if img_path is None:
                    self.log(f"ERROR: Put image.png next to main.py  ({SCRIPT_DIR})")
                    self.is_processing = False
                    return
                frame = cv2.imread(img_path)
                if frame is None:
                    self.log(f"ERROR: Could not read image  ({img_path})")
                    self.is_processing = False
                    return
                self.log(f"Loaded: {os.path.basename(img_path)}")

            # ── Pre-processing ────────────────────────────────────────────────
            h, w = frame.shape[:2]
            scale_x = CANVAS_WIDTH  / w
            scale_y = CANVAS_HEIGHT / h

            self.log("Running edge detection...")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Equalise contrast so dark images still yield good edges
            gray = cv2.equalizeHist(gray)

            # Bilateral filter: keeps edges sharp while removing texture noise.
            # (Gaussian blur, used before, smears the edges we want to detect.)
            filtered = cv2.bilateralFilter(gray, 7, 50, 50)

            # Auto-threshold Canny: adapts to image brightness
            median = float(np.median(filtered))
            lo = max(0,   int(0.55 * median))
            hi = min(255, int(1.45 * median))
            edges = cv2.Canny(filtered, lo, hi)

            # Tiny dilate to reconnect edges that Canny left with 1-pixel gaps
            kernel = np.ones((2, 2), np.uint8)
            edges  = cv2.dilate(edges, kernel, iterations=1)

            # ── Build drawing path ────────────────────────────────────────────
            self.log("Tracing contours...")
            path, total = self._edges_to_path(edges, scale_x, scale_y)

            if total == 0:
                self.log("ERROR: No edges found — try better lighting or a clearer image")
                self.is_processing = False
                return

            self.canvas.fill(CANVAS_BG)
            self.points_to_draw = path
            self.total_points   = total
            self.drawn_points   = 0
            self.log(f"Drawing {total} points — hold tight!")
            self.is_processing  = False

        except Exception as exc:
            self.log(f"CRASH: {exc}")
            traceback.print_exc()
            self.is_processing = False

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            # ── Events ────────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    if not self.is_processing:
                        if event.key == pygame.K_SPACE:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw.clear()
                            self.last_p = None
                            threading.Thread(
                                target=self.process_image,
                                args=("camera",),
                                daemon=True,
                            ).start()

                        elif event.key == pygame.K_m:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw.clear()
                            self.last_p = None
                            threading.Thread(
                                target=self.process_image,
                                args=("file",),
                                daemon=True,
                            ).start()

                        elif event.key == pygame.K_c:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw.clear()
                            self.last_p = None
                            self.total_points  = 0
                            self.drawn_points  = 0
                            self.status = "Cleared.  SPACE = Camera    M = Load image.png"

            # ── Draw queued points ────────────────────────────────────────────
            if self.points_to_draw and not self.is_processing:
                for _ in range(DRAW_SPEED):
                    if not self.points_to_draw:
                        break
                    p = self.points_to_draw.popleft()
                    if p is None:
                        self.last_p = None          # pen lift
                    else:
                        if self.last_p is not None:
                            pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, LINE_WIDTH)
                        self.last_p = p
                        self.drawn_points += 1

                remaining = len(self.points_to_draw)
                if remaining > 0 and self.total_points > 0:
                    pct = int(100 * self.drawn_points / self.total_points)
                    self.status = f"Drawing... {pct}%  ({remaining} points left)"
                elif remaining == 0 and self.total_points > 0:
                    self.status = "Done!    SPACE = Camera    M = Load image.png    C = Clear"

            # ── Render ────────────────────────────────────────────────────────
            self.screen.fill(BG_COLOR)

            # Red frame (Etch-A-Sketch body)
            pygame.draw.rect(
                self.screen, FRAME_COLOR,
                self.canvas_rect.inflate(80, 70), border_radius=28,
            )
            # Inner bezel
            pygame.draw.rect(
                self.screen, (25, 25, 30),
                self.canvas_rect.inflate(12, 12), border_radius=8,
            )

            # Canvas
            self.screen.blit(self.canvas, self.canvas_rect.topleft)

            # Dials
            dial_y = self.canvas_rect.bottom + 35
            for dial_x in (self.canvas_rect.left - 38, self.canvas_rect.right + 38):
                pygame.draw.circle(self.screen, (240, 240, 240), (dial_x, dial_y), 32)
                pygame.draw.circle(self.screen, (180, 180, 180), (dial_x, dial_y), 32, 3)
                pygame.draw.circle(self.screen, (100, 100, 100), (dial_x, dial_y),  6)

            # Status / progress bar
            if self.is_processing:
                dots = "." * ((int(time.time() * 3) % 3) + 1)
                msg  = self.status + dots
                surf = self.font.render(msg, True, WARN_COLOR)
            else:
                surf = self.font.render(self.status[:90], True, TEXT_COLOR)

            self.screen.blit(surf, (self.w // 2 - surf.get_width() // 2, self.h - 44))

            # Progress bar (only while drawing)
            if self.total_points > 0 and self.drawn_points < self.total_points:
                bar_w = CANVAS_WIDTH
                bar_x = self.canvas_rect.left
                bar_y = self.canvas_rect.bottom + 8
                fill  = int(bar_w * self.drawn_points / self.total_points)
                pygame.draw.rect(self.screen, (60, 60, 60),  (bar_x, bar_y, bar_w, 6), border_radius=3)
                pygame.draw.rect(self.screen, TEXT_COLOR,    (bar_x, bar_y, fill,  6), border_radius=3)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    MagicEtch().run()
