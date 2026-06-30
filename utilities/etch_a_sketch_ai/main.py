import os
import sys
import math
import time
import threading
import traceback
import pygame
import cv2
import numpy as np
from collections import deque

# ── Import Shared Utilities ───────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR  = os.path.join(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, UTILS_DIR)
try:
    import crt_overlay
except ImportError:
    crt_overlay = None

# ── Palette ───────────────────────────────────────────────────────────────────
BG_TOP        = (18,  8,  28)
BG_BOT        = (6,   2,  12)
FRAME_OUTER   = (172,  30,  42)   # deep red outer edge
FRAME_INNER   = (220,  55,  70)   # lighter red face
FRAME_SHADOW  = (80,   10,  18)   # dark shadow edge
CANVAS_BG     = (195, 195, 200) # Silver/gray
LINE_COLOR    = (45, 45, 50)    # Dark gray drawing line
KNOB_LIGHT    = (245, 245, 250)
KNOB_MID      = (190, 190, 200)
KNOB_DARK     = (90,  90, 105)
KNOB_TICK     = (60,  60,  75)
TEXT_CYAN     = (0,  230, 200)
TEXT_WHITE    = (255, 255, 255)
TEXT_DIM      = (140, 140, 160)
BADGE_COLORS  = {
    "DIALS":     (40,  80, 180),
    "X":         (180, 40,  40),
    "Y":         (40, 140,  60),
    "C":         (160, 100,   0),
    "BACK":      (80,  40, 120),
}

# ── Layout constants ──────────────────────────────────────────────────────────
CANVAS_W   = 1180
CANVAS_H   = 660
FRAME_PAD  = 52     # frame thickness around canvas
KNOB_R     = 38
BAR_H      = 90

# ── Input constants ───────────────────────────────────────────────────────────
_BTN_X        = 0
_BTN_Y        = 3
_BTN_BACK     = 6
_BTN_C        = 7
_BTN_START    = 9
_DIAL_DEADZONE = 0.08
_DIAL_SPEED    = 6
DRAW_SPEED    = 250
LINE_WIDTH    = 2


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))


def _draw_circle_gradient(surf, center, radius, inner_col, outer_col, steps=30):
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        col = _lerp_color(inner_col, outer_col, 1.0 - t)
        pygame.draw.circle(surf, col, center, r)


def _draw_3d_rect(surf, rect, bg, light=(255,255,255), dark=(60,60,60), bw=3):
    pygame.draw.rect(surf, bg, rect)
    x, y, w, h = rect
    for i in range(bw):
        pygame.draw.line(surf, light, (x+i, y+i), (x+w-1-i, y+i))
        pygame.draw.line(surf, light, (x+i, y+i), (x+i, y+h-1-i))
        pygame.draw.line(surf, dark,  (x+w-1-i, y+i),   (x+w-1-i, y+h-1-i))
        pygame.draw.line(surf, dark,  (x+i,     y+h-1-i),(x+w-1-i, y+h-1-i))


class MagicEtch:
    def __init__(self):
        pygame.init()
        pygame.mixer.pre_init(44100, -16, 2, 4096)

        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()
            self.joysticks.append(j)

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.display.set_caption("Magic Etch-A-Sketch AI")
        self.W, self.H = self.screen.get_size()
        self.clock = pygame.time.Clock()

        # Fonts
        try:
            self.font_title  = pygame.font.SysFont("georgia", 32, bold=True, italic=True)
            self.font_badge  = pygame.font.SysFont("monospace", 17, bold=True)
            self.font_desc   = pygame.font.SysFont("monospace", 15)
            self.font_hud    = pygame.font.SysFont("monospace", 14)
            self.font_knob   = pygame.font.SysFont("monospace", 13, bold=True)
        except:
            self.font_title  = pygame.font.Font(None, 40)
            self.font_badge  = pygame.font.Font(None, 20)
            self.font_desc   = pygame.font.Font(None, 18)
            self.font_hud    = pygame.font.Font(None, 16)
            self.font_knob   = pygame.font.Font(None, 16)

        # Canvas placement — centered, above the controls bar
        total_frame_w = CANVAS_W + FRAME_PAD * 2
        total_frame_h = CANVAS_H + FRAME_PAD * 2 + KNOB_R * 2 + 24  # knobs below
        fx = (self.W - total_frame_w) // 2
        fy = (self.H - BAR_H - total_frame_h) // 2

        self.frame_rect  = pygame.Rect(fx, fy, total_frame_w, total_frame_h)
        self.canvas_rect = pygame.Rect(fx + FRAME_PAD, fy + FRAME_PAD + 20, CANVAS_W, CANVAS_H)

        # Knob centres (bottom-left and bottom-right of frame)
        knob_y = self.frame_rect.bottom - KNOB_R - 8
        self.knob_l = (self.frame_rect.left  + FRAME_PAD // 2, knob_y)
        self.knob_r = (self.frame_rect.right - FRAME_PAD // 2, knob_y)
        self.knob_angle_l = 0.0
        self.knob_angle_r = 0.0

        # Canvas surface
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.canvas.fill(CANVAS_BG)

        # Pre-render background gradient
        self.bg_surf = self._make_bg()

        # Pre-render the static frame
        self.frame_surf = self._make_frame_surf()

        # Drawing state
        self.points_to_draw: deque = deque()
        self.total_points  = 0
        self.drawn_points  = 0
        self.is_processing = False
        self.last_p        = None
        self.cursor_x      = CANVAS_W // 2
        self.cursor_y      = CANVAS_H // 2
        self.manual_last_p = (self.cursor_x, self.cursor_y)
        self._mouse_accum_x = 0.0
        self._mouse_accum_y = 0.0
        self._spin_angle    = 0.0   # for processing spinner

    # ── Background ────────────────────────────────────────────────────────────
    def _make_bg(self):
        surf = pygame.Surface((self.W, self.H))
        for y in range(self.H):
            t = y / self.H
            col = _lerp_color(BG_TOP, BG_BOT, t)
            pygame.draw.line(surf, col, (0, y), (self.W, y))
        # Scanline overlay — subtle
        scan = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for y in range(0, self.H, 3):
            pygame.draw.line(scan, (0, 0, 0, 18), (0, y), (self.W, y))
        surf.blit(scan, (0, 0))
        return surf

    # ── Static Frame Surface ──────────────────────────────────────────────────
    def _make_frame_surf(self):
        fw = self.frame_rect.width
        fh = self.frame_rect.height
        surf = pygame.Surface((fw, fh), pygame.SRCALPHA)

        # Outer drop shadow
        pygame.draw.rect(surf, (10, 10, 10, 150), pygame.Rect(5, 5, fw, fh), border_radius=20)

        # Flat red body
        body = pygame.Rect(0, 0, fw, fh)
        pygame.draw.rect(surf, (214, 24, 33), body, border_radius=20)
        
        # Inner glow / bevel on red body
        pygame.draw.rect(surf, (245, 60, 70), body, width=3, border_radius=20)
        pygame.draw.rect(surf, (160, 10, 15), pygame.Rect(1, 1, fw-2, fh-2), width=4, border_radius=20)

        # Canvas cut-out (transparent hole)
        canvas_local = pygame.Rect(FRAME_PAD, FRAME_PAD + 20, CANVAS_W, CANVAS_H)
        pygame.draw.rect(surf, (0, 0, 0, 0), canvas_local, border_radius=10)

        # Frame inner shadow / bevel depth around canvas
        pygame.draw.rect(surf, (120, 10, 15), canvas_local.inflate(12, 12), border_radius=12)
        pygame.draw.rect(surf, (240, 240, 240), canvas_local.inflate(4, 4), border_radius=10)
        pygame.draw.rect(surf, (20, 20, 20, 255), canvas_local.inflate(2, 2), width=3, border_radius=10)

        # Title text on frame above canvas
        magic_text = pygame.font.SysFont("monospace", 14, bold=True).render("MAGIC", True, (255, 215, 0)) if pygame.font.get_init() else self.font_hud.render("MAGIC", True, (255, 215, 0))
        title = self.font_title.render("Etch A Sketch", True, (255, 215, 0))
        
        # Shadow for text
        title_shadow = self.font_title.render("Etch A Sketch", True, (100, 10, 10))
        surf.blit(title_shadow, title_shadow.get_rect(centerx=fw // 2 + 2, top=14))
        surf.blit(title, title.get_rect(centerx=fw // 2, top=12))
        surf.blit(magic_text, magic_text.get_rect(centerx=fw // 2, top=45))

        # Brand accent lines
        pygame.draw.line(surf, (255, 215, 0), (fw // 2 - 120, 30), (fw // 2 - 40, 30), 2)
        pygame.draw.line(surf, (255, 215, 0), (fw // 2 + 40, 30), (fw // 2 + 120, 30), 2)

        return surf

    # ── Knob drawing ──────────────────────────────────────────────────────────
    def _draw_knob(self, surf, cx, cy, angle, label):
        # Drop shadow
        pygame.draw.circle(surf, (100, 10, 15), (cx + 3, cy + 3), KNOB_R)
        
        # Base white knob
        pygame.draw.circle(surf, (250, 250, 250), (cx, cy), KNOB_R)
        
        # Outer rim shading for 3D effect
        pygame.draw.circle(surf, (200, 200, 205), (cx, cy), KNOB_R, 6)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), KNOB_R - 4, 3)
        
        # Ridges for grip
        num_ridges = 16
        for i in range(num_ridges):
            r_angle = angle + i * (2 * math.pi / num_ridges)
            x1 = cx + int((KNOB_R - 6) * math.cos(r_angle))
            y1 = cy + int((KNOB_R - 6) * math.sin(r_angle))
            x2 = cx + int((KNOB_R) * math.cos(r_angle))
            y2 = cy + int((KNOB_R) * math.sin(r_angle))
            pygame.draw.line(surf, (180, 180, 185), (x1, y1), (x2, y2), 2)
            
        # Center indentation
        pygame.draw.circle(surf, (220, 220, 225), (cx, cy), KNOB_R // 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), KNOB_R // 2, 2)

    # ── Controls bar ─────────────────────────────────────────────────────────
    def _draw_controls_bar(self):
        bar_y = self.H - BAR_H
        bar_rect = pygame.Rect(0, bar_y, self.W, BAR_H)

        # Bar background
        bar_surf = pygame.Surface((self.W, BAR_H), pygame.SRCALPHA)
        bar_surf.fill((8, 4, 18, 220))
        self.screen.blit(bar_surf, (0, bar_y))

        # Top separator line with glow
        pygame.draw.line(self.screen, (0, 180, 150), (0, bar_y),     (self.W, bar_y), 2)
        pygame.draw.line(self.screen, (0,  80,  60), (0, bar_y + 2), (self.W, bar_y + 2), 1)

        controls = [
            ("DIALS",  "Draw / Move"),
            ("X",      "Snap Photo"),
            ("Y",      "Load Image"),
            ("C",      "Clear"),
            ("BACK",   "Exit"),
        ]
        col_w = self.W // len(controls)
        for i, (key, desc) in enumerate(controls):
            cx = i * col_w + col_w // 2
            bg = BADGE_COLORS.get(key, (60, 60, 80))

            # Badge
            badge_rect = pygame.Rect(cx - 46, bar_y + 10, 92, 30)
            _draw_3d_rect(self.screen, badge_rect, bg,
                          light=tuple(min(255, c + 60) for c in bg),
                          dark=tuple(max(0, c - 40) for c in bg), bw=2)
            key_surf = self.font_badge.render(f"[{key}]", True, TEXT_WHITE)
            self.screen.blit(key_surf, key_surf.get_rect(center=badge_rect.center))

            # Description
            desc_surf = self.font_desc.render(desc, True, TEXT_DIM)
            self.screen.blit(desc_surf, desc_surf.get_rect(centerx=cx, top=bar_y + 46))

    # ── Status HUD ────────────────────────────────────────────────────────────
    def _draw_hud(self):
        # Top-right pill
        if self.total_points > 0:
            pct = int(self.drawn_points / self.total_points * 100)
            text = f"DRAWING  {pct:3d}%"
            col  = TEXT_CYAN
        else:
            text = "MANUAL MODE"
            col  = (180, 180, 220)

        hud_surf = self.font_hud.render(text, True, col)
        hx = self.W - hud_surf.get_width() - 24
        hy = 12
        pill = pygame.Rect(hx - 10, hy - 4, hud_surf.get_width() + 20, hud_surf.get_height() + 8)
        pill_bg = pygame.Surface((pill.width, pill.height), pygame.SRCALPHA)
        pill_bg.fill((0, 0, 0, 160))
        pygame.draw.rect(pill_bg, col + (80,), (0, 0, pill.width, pill.height),
                         width=1, border_radius=8)
        self.screen.blit(pill_bg, (pill.x, pill.y))
        self.screen.blit(hud_surf, (hx, hy))

    # ── Canvas vignette ───────────────────────────────────────────────────────
    def _draw_canvas_vignette(self):
        v = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
        strength = 120
        for i in range(30):
            t = i / 29
            a = int(strength * (1.0 - t))
            col = (0, 0, 0, a)
            pygame.draw.rect(v, col, (i, i, CANVAS_W - i*2, CANVAS_H - i*2), width=1)
        self.screen.blit(v, self.canvas_rect.topleft)

    # ── Manual cursor ─────────────────────────────────────────────────────────
    def _draw_cursor(self):
        if self.points_to_draw:
            return
        ax = self.canvas_rect.left + self.cursor_x
        ay = self.canvas_rect.top  + self.cursor_y
        col = (0, 200, 160)
        size = 8
        pygame.draw.line(self.screen, col, (ax - size, ay), (ax + size, ay), 1)
        pygame.draw.line(self.screen, col, (ax, ay - size), (ax, ay + size), 1)
        pygame.draw.circle(self.screen, col, (ax, ay), 3, 1)

    # ── Processing overlay ────────────────────────────────────────────────────
    def _draw_processing_overlay(self, t_ms):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 195))
        self.screen.blit(overlay, (0, 0))

        # Spinner
        cx, cy = self.W // 2, self.H // 2 - 40
        spokes = 12
        for i in range(spokes):
            angle = self._spin_angle + i * (2 * math.pi / spokes)
            brightness = int(255 * (i / spokes))
            col = (brightness, brightness, brightness)
            x1 = cx + int(22 * math.cos(angle))
            y1 = cy + int(22 * math.sin(angle))
            x2 = cx + int(38 * math.cos(angle))
            y2 = cy + int(38 * math.sin(angle))
            pygame.draw.line(self.screen, col, (x1, y1), (x2, y2), 3)

        # Text
        blink = (int(t_ms / 500) % 2 == 0)
        msg = self.font_title.render("AI IS ANALYZING IMAGE...", True,
                                     TEXT_CYAN if blink else (0, 160, 130))
        self.screen.blit(msg, msg.get_rect(centerx=self.W // 2, top=cy + 55))
        sub = self.font_desc.render("Please wait — processing edges", True, TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(centerx=self.W // 2, top=cy + 92))

    # ── Edge path builder ────────────────────────────────────────────────────
    def _edges_to_path(self, edges, scale_x, scale_y):
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
        if not contours: return deque(), 0
        contours = [c for c in contours if cv2.arcLength(c, True) > 20]
        if not contours: return deque(), 0

        path = deque()
        total = 0
        unvisited = []
        for c in contours:
            pts = []
            for pt in c:
                x = int(pt[0][0] * scale_x)
                y = int(pt[0][1] * scale_y)
                pts.append((max(0, min(CANVAS_W-1, x)), max(0, min(CANVAS_H-1, y))))
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
            ordered = target[start_at:] + target[:start_at]
            for pt in ordered:
                path.append(pt); total += 1
            current_pos = ordered[-1]
        return path, total

    def process_image(self, source="camera"):
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
            scale_x, scale_y = CANVAS_W / w, CANVAS_H / h
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            edges = cv2.Canny(filtered, 50, 150)
            kernel = np.ones((2, 2), np.uint8)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            path, total = self._edges_to_path(edges, scale_x, scale_y)
            self.canvas.fill(CANVAS_BG)
            self.points_to_draw = path
            self.total_points = total
            self.drawn_points = 0
            self.is_processing = False
        except Exception:
            print(traceback.format_exc())
            self.is_processing = False

    def run(self):
        running = True
        pygame.mouse.get_rel()
        while running:
            t_ms = pygame.time.get_ticks()
            self._spin_angle = (t_ms / 120.0) % (2 * math.pi)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if not self.is_processing:
                        if event.key == pygame.K_SPACE:
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image,
                                             args=("camera",), daemon=True).start()
                        elif event.key == pygame.K_m:
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image,
                                             args=("file",), daemon=True).start()
                        elif event.key == pygame.K_c:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw.clear()
                            self.last_p = None
                            self.total_points = 0; self.drawn_points = 0

                if event.type == pygame.JOYBUTTONDOWN:
                    btn = event.button
                    if btn == _BTN_BACK:
                        running = False
                    elif not self.is_processing:
                        if btn in (_BTN_X, _BTN_START):
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image,
                                             args=("camera",), daemon=True).start()
                        elif btn == _BTN_Y:
                            self.points_to_draw.clear(); self.last_p = None
                            threading.Thread(target=self.process_image,
                                             args=("file",), daemon=True).start()
                        elif btn == _BTN_C:
                            self.canvas.fill(CANVAS_BG)
                            self.points_to_draw.clear()
                            self.last_p = None
                            self.total_points = 0; self.drawn_points = 0

                if event.type == pygame.MOUSEMOTION:
                    self._mouse_accum_x += event.rel[0]
                    self._mouse_accum_y += event.rel[1]

            # ── Manual drawing ────────────────────────────────────────────
            if not self.is_processing and not self.points_to_draw:
                dx, dy = 0.0, 0.0
                keys = pygame.key.get_pressed()
                spd = 4
                if keys[pygame.K_LEFT]:  dx -= spd
                if keys[pygame.K_RIGHT]: dx += spd
                if keys[pygame.K_UP]:    dy -= spd
                if keys[pygame.K_DOWN]:  dy += spd

                if self.joysticks:
                    joy = self.joysticks[0]
                    if joy.get_numaxes() >= 2:
                        ax = joy.get_axis(0)
                        ay = joy.get_axis(1)
                        if abs(ax) > _DIAL_DEADZONE: dx += ax * _DIAL_SPEED
                        if abs(ay) > _DIAL_DEADZONE: dy += ay * _DIAL_SPEED
                    if joy.get_numhats() > 0:
                        hx, hy = joy.get_hat(0)
                        if hx < -0.5: dx -= _DIAL_SPEED
                        elif hx > 0.5: dx += _DIAL_SPEED
                        if hy < -0.5: dy += _DIAL_SPEED # In Pygame, HAT up is (0,1), but screen up is -y
                        elif hy > 0.5: dy -= _DIAL_SPEED

                dx += self._mouse_accum_x
                dy += self._mouse_accum_y
                self._mouse_accum_x = 0.0
                self._mouse_accum_y = 0.0

                if abs(dx) > 0.5 or abs(dy) > 0.5:
                    self.cursor_x = max(0, min(CANVAS_W-1, self.cursor_x + int(dx)))
                    self.cursor_y = max(0, min(CANVAS_H-1, self.cursor_y + int(dy)))
                    pygame.draw.line(self.canvas, LINE_COLOR,
                                     self.manual_last_p,
                                     (self.cursor_x, self.cursor_y), LINE_WIDTH)
                    # Spin knobs visually
                    self.knob_angle_l += dx * 0.04
                    self.knob_angle_r += dy * 0.04
                self.manual_last_p = (self.cursor_x, self.cursor_y)

            # ── Auto draw ─────────────────────────────────────────────────
            if self.points_to_draw and not self.is_processing:
                for _ in range(DRAW_SPEED):
                    if not self.points_to_draw: break
                    p = self.points_to_draw.popleft()
                    if self.last_p is not None:
                        pygame.draw.line(self.canvas, LINE_COLOR, self.last_p, p, LINE_WIDTH)
                    self.last_p = p
                    self.drawn_points += 1
                    self.cursor_x, self.cursor_y = p
                self.manual_last_p = (self.cursor_x, self.cursor_y)

            # ── Render ────────────────────────────────────────────────────
            self.screen.blit(self.bg_surf, (0, 0))

            # Frame
            self.screen.blit(self.frame_surf, self.frame_rect.topleft)

            # Canvas
            self.screen.blit(self.canvas, self.canvas_rect.topleft)
            self._draw_canvas_vignette()

            # Knobs (animated)
            self._draw_knob(self.screen, *self.knob_l, self.knob_angle_l, "H")
            self._draw_knob(self.screen, *self.knob_r, self.knob_angle_r, "V")

            # Cursor crosshair
            if not self.is_processing:
                self._draw_cursor()

            # Controls bar
            self._draw_controls_bar()

            # HUD
            self._draw_hud()

            # CRT overlay
            if crt_overlay:
                crt_overlay.apply_crt(self.screen, t_ms)
                # Counteract darkening on the canvas
                brighten = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)
                brighten.fill((255, 255, 255, 30))
                self.screen.blit(brighten, self.canvas_rect.topleft)

            # Processing spinner overlay
            if self.is_processing:
                self._draw_processing_overlay(t_ms)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    MagicEtch().run()
