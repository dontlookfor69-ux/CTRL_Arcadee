import pygame
import random
import math
import sys
import os
import cv2
import numpy as np
import json

LYRIC_OFFSETS_FILE = "lyric_offsets.json"
def load_lyric_offsets():
    if os.path.exists(LYRIC_OFFSETS_FILE):
        try:
            with open(LYRIC_OFFSETS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_lyric_offsets(offsets):
    with open(LYRIC_OFFSETS_FILE, "w") as f:
        json.dump(offsets, f)

# Initialize Pygame
pygame.init()
pygame.mixer.init()
pygame.mouse.set_visible(False)

# Set resolution to 1920x1080
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
# Force full screen with scaling to match 1920x1080 logically
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Just Shapes & Beats Remake")
clock = pygame.time.Clock()

# --- Constants & Colors ---
COLORS = {
    'bg': (5, 5, 5),
    'blue': (0, 183, 255),
    'yellow': (255, 235, 59),
    'orange': (255, 152, 0),
    'pink': (255, 40, 105),
    'enemy': (255, 0, 102),
    'white': (255, 255, 255),
    'ui_bg': (20, 20, 20, 180),
    'green': (76, 175, 80)
}

SHAPE_TYPES = ['square', 'triangle', 'octagon', 'circle']
SHAPE_COLORS = {
    'square': COLORS['blue'],
    'triangle': COLORS['yellow'],
    'octagon': COLORS['orange'],
    'circle': COLORS['green']
}

# --- Asset Loading ---
MEDIA_PATH = "Media"
LOGO_IMG = None
BG_IMG = None

if os.path.exists(os.path.join(MEDIA_PATH, "Logo.png")):
    LOGO_IMG = pygame.image.load(os.path.join(MEDIA_PATH, "Logo.png")).convert_alpha()

if os.path.exists(os.path.join(MEDIA_PATH, "Just Shapes And Beats Background.png")):
    BG_IMG = pygame.image.load(os.path.join(MEDIA_PATH, "Just Shapes And Beats Background.png")).convert()
    # Smoothscale to ensure it covers EVERYTHING
    BG_IMG = pygame.transform.smoothscale(BG_IMG, (SCREEN_WIDTH, SCREEN_HEIGHT))

def load_music_safely(path):
    if os.path.exists(path):
        pygame.mixer.music.load(path)
    else:
        media_dir = os.path.dirname(path)
        fallback_path = None
        if os.path.exists(media_dir):
            for f in os.listdir(media_dir):
                if f.endswith(".mp3"):
                    fallback_path = os.path.join(media_dir, f)
                    break
        if fallback_path and os.path.exists(fallback_path):
            print(f"[WARNING] Music file not found: {path}. Falling back to: {fallback_path}")
            pygame.mixer.music.load(fallback_path)
        else:
            print(f"[ERROR] Music file not found and no fallback: {path}")

def parse_lrc(filepath):
    lyrics = []
    if not os.path.exists(filepath):
        return lyrics
    import re
    # Match [mm:ss.xx] or [mm:ss.xxx]
    pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\](.*)')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    m = int(match.group(1))
                    s = int(match.group(2))
                    ms_part = match.group(3)
                    # Handle 2 or 3 digits for ms
                    if len(ms_part) == 2:
                        ms = int(ms_part) * 10
                    else:
                        ms = int(ms_part)
                    text = match.group(4).strip()
                    time_ms = m * 60000 + s * 1000 + ms
                    if text: # Ignore blank lyrics
                        lyrics.append({'time': time_ms, 'text': text})
    except Exception as e:
        print(f"[ERROR] Failed to parse LRC {filepath}: {e}")
    # Sort just in case
    lyrics.sort(key=lambda x: x['time'])
    return lyrics

SONGS = {
    "Cool Friends": {"path": os.path.join(MEDIA_PATH, "Cool Friends.mp3"), "img": os.path.join(MEDIA_PATH, "Cool Friends.png"), "bpm": 128, "artist": "Silva Hound", "diff": 8},
    "Annihilate": {"path": os.path.join(MEDIA_PATH, "Annihilate.mp3"), "img": os.path.join(MEDIA_PATH, "Annihilate.jpeg"), "bpm": 140, "artist": "Destroid", "diff": 14},
    "CLOSE TO ME": {"path": os.path.join(MEDIA_PATH, "CLOSE TO ME.mp3"), "img": os.path.join(MEDIA_PATH, "Close To Me.jpg"), "bpm": 130, "artist": "Sabrepulse", "diff": 11},
    "Final Boss": {"path": os.path.join(MEDIA_PATH, "Final Boss.mp3"), "img": os.path.join(MEDIA_PATH, "Final Boss.png"), "bpm": 150, "artist": "Nitro Fun", "diff": 15},
    "Never Gonna Give You Up": {"path": os.path.join(MEDIA_PATH, "Never Gonna Give You Up.ogg"), "img": os.path.join(MEDIA_PATH, "Never Gonna Give You Up.png"), "bpm": 113, "artist": "Rick Astley", "diff": 5}
}

# Load song images
for name, data in SONGS.items():
    if data["img"] != "?" and os.path.exists(data["img"]):
        data["surf"] = pygame.image.load(data["img"]).convert()
        data["surf"] = pygame.transform.scale(data["surf"], (400, 400))
    else:
        data["surf"] = None

# --- Fonts ---
_font_cache = {}
def get_font(size, bold=True):
    key = (size, bold)
    if key not in _font_cache:
        try:
            _font_cache[key] = pygame.font.SysFont('Arial', size, bold=bold)
        except:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]

font_xl = get_font(120)
font_large = get_font(80)
font_medium = get_font(40)
font_small = get_font(24, False)

_text_cache = {}
def get_rendered_text(text, size, color, bold=True):
    key = (text, size, color, bold)
    if key not in _text_cache:
        f = get_font(size, bold)
        _text_cache[key] = f.render(text, True, color)
    return _text_cache[key]

_shape_cache = {}
def get_shape_surf(shape, size, color, alpha):
    key = (shape, size, color, alpha)
    if key not in _shape_cache:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        draw_color = (*color, alpha)
        if shape == 'square':
            pygame.draw.rect(surf, draw_color, (0, 0, size, size))
        elif shape == 'triangle':
            pygame.draw.polygon(surf, draw_color, [(size/2, 0), (size, size), (0, size)])
        elif shape == 'circle':
            pygame.draw.circle(surf, draw_color, (size/2, size/2), size/2)
        elif shape == 'octagon':
            draw_octagon(surf, draw_color, (0, 0, size, size))
        _shape_cache[key] = surf
    return _shape_cache[key]

_obs_cache = {}
def get_obs_surf(type, size, color, alpha):
    key = (type, size, color, alpha)
    if key not in _obs_cache:
        s = max(1, int(size))
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        if type == 'rect':
            pygame.draw.rect(surf, (*color, alpha), (0, 0, s, s))
        elif type == 'circle':
            pygame.draw.circle(surf, (*color, alpha), (s/2, s/2), s/2)
        elif type == 'triangle':
            pygame.draw.polygon(surf, (*color, alpha), [(s/2, 0), (s, s), (0, s)])
        _obs_cache[key] = surf
    return _obs_cache[key]
# --- Global State ---
class GameState:
    MENU = "menu"
    SKINS = "skins"
    LEVEL_SELECT = "level_select"
    PLAYING = "playing"
    VIDEO = "video"
    GAMEOVER = "gameover"
    COMPLETED = "completed"
    PAUSED = "paused"
    SETTINGS = "settings"
    WARNING = "warning"
    LEVEL_MAKER = "level_maker"
    LEVEL_CONFIG = "level_config"

class App:
    def __init__(self):
        self.state = GameState.WARNING
        self.is_p2_enabled = False
        self.p1_shape = 'square'
        self.p2_shape = 'triangle'
        self.selected_level_idx = 0
        self.levels = list(SONGS.keys())
        self.shake_amount = 0
        self.health = 100
        self.max_health = 100
        self.last_beat_time = 0
        self.beat_interval = 500
        self.active_level = None
        self.video_cap = None
        self.running = True
        self.fade_alpha = 0
        self.end_screen_timer = 0
        self.video_fps = None
        self.current_frame = -1
        self.video_start_time = 0
        self.last_frame = None
        self.lyric_offsets = load_lyric_offsets()
        self.debug_menu = False
        
        # Level Maker State
        self.lm_query = ""
        self.lm_status = "Type Song Name & Press Enter"
        self.lm_state = 0
        self.level_maker_anim = 0.0
        self.delete_mode = False
        self.delete_confirm = None

        # Animation state
        self.scroll_y = 0
        self.target_scroll_y = 0
        self.item_offsets = [0] * len(self.levels)
        
        # Particle System for Menu
        self.particles = []
        for _ in range(30):
            self.particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.randint(5, 15),
                'speed': random.uniform(0.5, 2.0),
                'color': random.choice([COLORS['pink'], COLORS['blue']])
            })

        self.menu_idx = 0
        self.menu_options = ["Level Selection", "Skins", "Settings", "Toggle Player 2: OFF", "Exit Game"]
        self.players = []
        self.menu_sel_lerp = [0.0] * len(self.menu_options)
        
        # Audio / Settings state
        self.global_volume = 0.8
        pygame.mixer.music.set_volume(self.global_volume)
        
        # Pause state variables
        self.pause_idx = 0
        self.pause_options = ["Resume", f"Volume: {int(self.global_volume * 100)}%", "Exit Level"]
        self.pause_scale = 0.0
        self.pause_exiting = False
        self.pause_exit_action = 'resume'
        self.pause_hover_y = 160.0
        self.pause_sel_lerp = [0.0] * len(self.pause_options)
        
        # Settings state variables
        self.text_glitches = True
        self.hq_processing = False
        self.settings_idx = 0
        self.settings_options = [f"Music Volume: {int(self.global_volume * 100)}%", f"Text Glitches: {'ON' if self.text_glitches else 'OFF'}", f"HQ Processing (Laptop): {'ON' if self.hq_processing else 'OFF'}", "Back"]

        if not pygame.joystick.get_init():
            pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()

    def toggle_p2(self):
        self.is_p2_enabled = not self.is_p2_enabled
        self.menu_options[3] = f"Toggle Player 2: {'ON' if self.is_p2_enabled else 'OFF'}"

# --- Utility Functions ---
def draw_octagon(surface, color, rect):
    x, y, w, h = rect
    s = w / (1 + math.sqrt(2))
    points = [
        (x + s, y), (x + w - s, y),
        (x + w, y + s), (x + w, y + h - s),
        (x + w - s, y + h), (x + s, y + h),
        (x, y + h - s), (x, y + s)
    ]
    pygame.draw.polygon(surface, color, points)

def draw_shape(surface, shape, color, pos, size, alpha=255):
    x, y = pos
    size = int(size)
    if alpha < 255:
        target_surf = get_shape_surf(shape, size, color, alpha)
        surface.blit(target_surf, (x - size/2, y - size/2))
    else:
        rect = (x - size/2, y - size/2, size, size)
        if shape == 'square':
            pygame.draw.rect(surface, color, rect)
        elif shape == 'triangle':
            pygame.draw.polygon(surface, color, [(x, y - size/2), (x + size/2, y + size/2), (x - size/2, y + size/2)])
        elif shape == 'circle':
            pygame.draw.circle(surface, color, (x, y), size/2)
        elif shape == 'octagon':
            draw_octagon(surface, color, rect)

# --- Entities ---
class Player:
    def __init__(self, id, shape):
        self.id = id
        self.shape = shape
        self.size = 25
        self.speed = 11
        self.dash_dist = 140
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.dash_energy = 100
        self.max_dash_energy = 100
        self.invuln_timer = 0
        self.is_dashing = False
        self.trail = []
        self.reset()

    def reset(self):
        self.x = SCREEN_WIDTH // 2 + (50 if self.id == 2 else -50)
        self.y = SCREEN_HEIGHT // 2
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.dash_energy = 100
        self.invuln_timer = 0
        self.is_dashing = False
        self.trail = []

    def update(self, dt, app):
        if self.dash_cooldown > 0: self.dash_cooldown -= dt
        if self.invuln_timer > 0: self.invuln_timer -= dt
        if self.dash_energy < self.max_dash_energy:
            self.dash_energy = min(self.max_dash_energy, self.dash_energy + 0.05 * dt)

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        if self.id == 1:
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1
            dash_key = keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT]
            
            if hasattr(app, 'joysticks') and len(app.joysticks) > 0:
                j = app.joysticks[0]
                if j.get_numaxes() >= 2:
                    if j.get_axis(0) < -0.3: dx -= 1
                    elif j.get_axis(0) > 0.3: dx += 1
                    if j.get_axis(1) < -0.3: dy -= 1
                    elif j.get_axis(1) > 0.3: dy += 1
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    if hx < 0: dx -= 1
                    elif hx > 0: dx += 1
                    if hy > 0: dy -= 1
                    elif hy < 0: dy += 1
                if j.get_button(0) or j.get_button(1) or j.get_button(9): dash_key = True
        else:
            if keys[pygame.K_UP]: dy -= 1
            if keys[pygame.K_DOWN]: dy += 1
            if keys[pygame.K_LEFT]: dx -= 1
            if keys[pygame.K_RIGHT]: dx += 1
            dash_key = keys[pygame.K_RETURN] or keys[pygame.K_RSHIFT]
            
            if hasattr(app, 'joysticks') and len(app.joysticks) > 1:
                j = app.joysticks[1]
                if j.get_numaxes() >= 2:
                    if j.get_axis(0) < -0.3: dx -= 1
                    elif j.get_axis(0) > 0.3: dx += 1
                    if j.get_axis(1) < -0.3: dy -= 1
                    elif j.get_axis(1) > 0.3: dy += 1
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    if hx < 0: dx -= 1
                    elif hx > 0: dx += 1
                    if hy > 0: dy -= 1
                    elif hy < 0: dy += 1
                if j.get_button(0) or j.get_button(1) or j.get_button(9): dash_key = True

        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0: self.is_dashing = False
            self.trail.append({'x': self.x, 'y': self.y, 'alpha': 150})
        else:
            if dx != 0 or dy != 0:
                mag = math.sqrt(dx*dx + dy*dy)
                self.x += (dx / mag) * self.speed
                self.y += (dy / mag) * self.speed
            
            if dash_key and self.dash_cooldown <= 0 and self.dash_energy >= 35:
                self.start_dash(dx, dy, app)

        self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
        self.y = max(self.size, min(SCREEN_HEIGHT - self.size, self.y))

        for t in self.trail: t['alpha'] -= 10
        self.trail = [t for t in self.trail if t['alpha'] > 0]

    def start_dash(self, dx, dy, app):
        if dx == 0 and dy == 0:
            dx = -1 if self.id == 1 else 1
        mag = math.sqrt(dx*dx + dy*dy)
        self.x += (dx/mag) * self.dash_dist
        self.y += (dy/mag) * self.dash_dist
        self.is_dashing = True
        self.dash_energy -= 35
        self.dash_timer = 150
        self.dash_cooldown = 100
        self.invuln_timer = 250
        app.shake_amount = 8

    def draw(self, surface):
        color = SHAPE_COLORS[self.shape]
        for t in self.trail:
            draw_shape(surface, self.shape, color, (t['x'], t['y']), self.size, t['alpha'])
        if self.invuln_timer > 0 and (pygame.time.get_ticks() // 50) % 2 == 0:
            return
        draw_shape(surface, self.shape, color, (self.x, self.y), self.size)

class Obstacle:
    def __init__(self, x, y, size, vx, vy, type='rect', warning=1000, damage=10, alpha=255, rot_speed=None, lifespan=None):
        self.x = x
        self.y = y
        self.size = size
        self.vx = vx
        self.vy = vy
        self.type = type
        self.warning = warning
        self.active = False
        self.timer = 0
        self.rotation = 0
        self.rot_speed = random.uniform(-5, 5) if rot_speed is None else rot_speed
        self.damage = damage
        self.alpha = alpha
        self.lifespan = lifespan

    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning:
            self.active = True
            
            self.x += self.vx
            self.y += self.vy
            self.rotation += self.rot_speed
            
            if self.lifespan is not None:
                self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 100) + 50
            warn_color = (*COLORS['enemy'], alpha)
            if self.type == 'rect':
                pygame.draw.rect(surface, warn_color, (self.x - self.size/2, self.y - self.size/2, self.size, self.size), 2)
            elif self.type == 'circle':
                pygame.draw.circle(surface, warn_color, (self.x, self.y), self.size/2, 2)
            elif self.type == 'triangle':
                pygame.draw.polygon(surface, warn_color, [(self.x, self.y - self.size/2), (self.x + self.size/2, self.y + self.size/2), (self.x - self.size/2, self.y + self.size/2)], 2)
        else:
            color = COLORS['enemy']
            last_beat = app.active_level.last_beat_time if app.active_level else 0
            pulse = max(0, 1 - (level_elapsed - last_beat) / 200) * 10
            s = int(self.size + pulse)
            
            if self.alpha == 255:
                if self.type == 'rect':
                    if self.rotation % 360 == 0:
                        pygame.draw.rect(surface, color, (self.x - s/2, self.y - s/2, s, s))
                    else:
                        angle_rad = math.radians(-self.rotation)
                        cos_a = math.cos(angle_rad)
                        sin_a = math.sin(angle_rad)
                        hs = s / 2
                        pts = [
                            (self.x - hs*cos_a + hs*sin_a, self.y - hs*sin_a - hs*cos_a),
                            (self.x + hs*cos_a + hs*sin_a, self.y + hs*sin_a - hs*cos_a),
                            (self.x + hs*cos_a - hs*sin_a, self.y + hs*sin_a + hs*cos_a),
                            (self.x - hs*cos_a - hs*sin_a, self.y - hs*sin_a + hs*cos_a)
                        ]
                        pygame.draw.polygon(surface, color, pts)
                elif self.type == 'triangle':
                    angle_rad = math.radians(-self.rotation)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    hs = s / 2
                    pts = [(0, -hs), (hs, hs), (-hs, hs)]
                    rpts = [(self.x + px*cos_a - py*sin_a, self.y + px*sin_a + py*cos_a) for px, py in pts]
                    pygame.draw.polygon(surface, color, rpts)
                elif self.type == 'circle':
                    pygame.draw.circle(surface, color, (self.x, self.y), s/2)
            else:
                obs_surf = get_obs_surf(self.type, s, color, self.alpha)
                if self.type in ['rect', 'triangle'] and self.rotation % 360 != 0:
                    rot_surf = pygame.transform.rotate(obs_surf, self.rotation)
                    rect = rot_surf.get_rect(center=(self.x, self.y))
                    surface.blit(rot_surf, rect.topleft)
                else:
                    surface.blit(obs_surf, (self.x - s/2, self.y - s/2))

    def check_collision(self, player):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        dist = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
        return dist < (self.size + player.size) / 2

# --- Levels ---
class Level:
    def __init__(self, name, app):
        self.name = name
        self.app = app
        self.obstacles = []
        self.elapsed_ms = 0
        self.last_beat_time = 0
        self.config = SONGS[name]
        self.bpm = self.config.get('bpm', 120)
        self.app.beat_interval = (60 / self.bpm) * 1000
        self.finished = False
        
        # Load Lyrics
        self.lyrics = []
        self.current_lyric_idx = -1
        music_path = self.config.get("path", "")
        if music_path:
            # First try exact same name but .lrc
            lrc_path = os.path.splitext(music_path)[0] + ".lrc"
            if not os.path.exists(lrc_path):
                # spotdl might use slightly different names
                media_dir = os.path.dirname(music_path)
                if os.path.exists(media_dir):
                    artist = self.config.get('artist', '').lower()
                    for f in os.listdir(media_dir):
                        if f.endswith('.lrc') and artist in f.lower() and name.lower() in f.lower():
                            lrc_path = os.path.join(media_dir, f)
                            break
            self.lyrics = parse_lrc(lrc_path)

    def update(self, dt):
        self.elapsed_ms += dt
        self.spawn_patterns(self.elapsed_ms)
        for obs in self.obstacles[:]:
            obs.update(dt, self.app)
            if obs.x < -1000 or obs.x > SCREEN_WIDTH + 1000 or obs.y < -1000 or obs.y > SCREEN_HEIGHT + 1000:
                self.obstacles.remove(obs)
            elif getattr(obs, 'lifespan', None) is not None and obs.lifespan <= 0:
                if obs in self.obstacles: self.obstacles.remove(obs)
            else:
                for p in self.app.players:
                    if obs.check_collision(p):
                        self.app.health -= obs.damage
                        self.app.shake_amount = 15
                        p.invuln_timer = 1000
                        if obs in self.obstacles: self.obstacles.remove(obs)

    def spawn_patterns(self, elapsed):
        if self.elapsed_ms - self.last_beat_time > self.app.beat_interval:
            self.last_beat_time = self.elapsed_ms
            self.app.shake_amount = 4
            self.on_beat(elapsed)

    def on_beat(self, elapsed): pass

    def draw_extra(self, surface): pass

    def draw_background(self, surface):
        level_progress = min(1.0, self.elapsed_ms / 210000.0)
        beat_pulse = max(0, 1.0 - (self.elapsed_ms % 530) / 530.0) if self.name == "Never Gonna Give You Up" else 0
        
        if hasattr(self, 'rms_curve') and self.rms_curve:
            idx = int((self.elapsed_ms + self.app.lyric_offsets.get(self.name, 0)) / 100)
            if idx >= 0 and idx < len(self.rms_curve):
                energy = self.rms_curve[idx]["energy"]
                beat_pulse += energy * 1.5
                level_progress += energy * 0.5
                
        # Flash background slightly red on beats
        bg_r = max(0, min(255, int(COLORS['bg'][0] + (COLORS['pink'][0] - COLORS['bg'][0]) * level_progress * 0.3 * beat_pulse)))
        bg_g = max(0, min(255, int(COLORS['bg'][1] + (COLORS['pink'][1] - COLORS['bg'][1]) * level_progress * 0.3 * beat_pulse)))
        bg_b = max(0, min(255, int(COLORS['bg'][2] + (COLORS['pink'][2] - COLORS['bg'][2]) * level_progress * 0.3 * beat_pulse)))
        surface.fill((bg_r, bg_g, bg_b))
        
        # Dynamic Neon Grid
        grid_offset = (self.elapsed_ms * 0.1) % 60
        grid_alpha = int(20 + 40 * level_progress + 20 * beat_pulse)
        grid_color = (max(0, min(255, bg_r+grid_alpha)), max(0, min(255, bg_g+grid_alpha)), max(0, min(255, bg_b+grid_alpha)))
        
        for x in range(int(-grid_offset), SCREEN_WIDTH, 60):
            pygame.draw.line(surface, grid_color, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(int(-grid_offset), SCREEN_HEIGHT, 60):
            pygame.draw.line(surface, grid_color, (0, y), (SCREEN_WIDTH, y))

    def draw_background_lyrics(self, surface):
        if not getattr(self, 'lyrics', None) or not self.lyrics:
            return
            
        offset = self.app.lyric_offsets.get(self.name, 0)
        
        # Find current lyric efficiently supporting dynamic offsets
        idx = -1
        for i, l in enumerate(self.lyrics):
            if self.elapsed_ms >= l['time'] + offset:
                idx = i
            else:
                break
                
        self.current_lyric_idx = idx
        
        if self.current_lyric_idx >= 0:
            lyric_data = self.lyrics[self.current_lyric_idx]
            lyric_text = lyric_data['text']
            lyric_time = lyric_data['time'] + offset
            
            # Figure out duration of the lyric (either to next lyric or default to 3 seconds)
            next_time = lyric_time + 3000
            if self.current_lyric_idx + 1 < len(self.lyrics):
                next_time = self.lyrics[self.current_lyric_idx + 1]['time'] + offset
                
            duration = next_time - lyric_time
            time_since_lyric = self.elapsed_ms - lyric_time
            
            # Only display if we haven't exceeded the duration, or some padding
            if time_since_lyric < duration:
                level_progress = min(1.0, self.elapsed_ms / 200000.0)
                
                # 1. Base scale and alpha
                alpha = 255
                if time_since_lyric < 200:
                    alpha = int((time_since_lyric / 200) * 255)
                elif duration - time_since_lyric < 200:
                    alpha = int(((duration - time_since_lyric) / 200) * 255)
                
                # Glitch and Pulse intensity driven by audio
                energy = 0
                if hasattr(self, 'rms_curve') and self.rms_curve:
                    idx = int((self.elapsed_ms + self.app.lyric_offsets.get(self.name, 0)) / 100)
                    if idx >= 0 and idx < len(self.rms_curve):
                        energy = self.rms_curve[idx]["energy"]
                        
                glitch_active = getattr(self.app, 'text_glitches', True) and (energy > 0.6)
                
                beat_pulse = 1.0
                time_since_beat = self.elapsed_ms - self.last_beat_time
                if time_since_beat < 150:
                    beat_pulse = 1.0 + (150 - time_since_beat) / 150 * (0.05 + energy * 0.2)
                    
                if glitch_active:
                    beat_pulse += energy * 0.1
                    
                font_size = int(70 * beat_pulse)
                
                # Check for overflow and scale font down
                tmp_surf = get_font(font_size).render(lyric_text, True, (255, 255, 255))
                while tmp_surf.get_width() > SCREEN_WIDTH - 100 and font_size > 20:
                    font_size -= 4
                    tmp_surf = get_font(font_size).render(lyric_text, True, (255, 255, 255))
                
                base_x = SCREEN_WIDTH // 2
                base_y = SCREEN_HEIGHT // 2  # Moved to the middle of the screen
                
                anim_type = 0
                # Animate based on song energy
                if energy < 0.3: anim_type = 0
                elif energy < 0.6: anim_type = 1
                elif energy < 0.8: anim_type = 2
                else: anim_type = 3
                
                t = time_since_lyric / max(1, duration) # 0.0 to 1.0
                
                scale_x, scale_y = 1.0, 1.0
                rot_angle = 0
                
                if anim_type == 0: # Calm Pulse
                    pulse_t = (time_since_lyric % 1000) / 1000.0
                    scale_x = 1.0 + math.sin(pulse_t * math.pi) * 0.02
                    scale_y = 1.0 + math.cos(pulse_t * math.pi) * 0.02
                elif anim_type == 1: # Verse Stretch
                    pulse_t = (time_since_lyric % 500) / 500.0
                    scale_x = 1.0 + math.sin(pulse_t * math.pi) * 0.05
                    scale_y = 1.0 + math.cos(pulse_t * math.pi) * 0.05
                elif anim_type == 2: # Pre-Chorus Tense (glitchy)
                    if time_since_lyric % 150 < 75:
                        glitch_active = True
                        base_x += random.randint(-5, 5)
                        base_y += random.randint(-5, 5)
                elif anim_type == 3: # Chorus Slam
                    if t < 0.05:
                        scale_x = 1.5 - (t / 0.05) * 0.5
                        scale_y = 1.5 - (t / 0.05) * 0.5
                    else:
                        pulse_t = (time_since_lyric % 250) / 250.0
                        scale_x = 1.0 + math.sin(pulse_t * math.pi) * 0.1
                        scale_y = 1.0 + math.cos(pulse_t * math.pi) * 0.1
                
                if glitch_active:
                    glitch_dist = int(5 * energy)
                    base_x += random.randint(-glitch_dist, glitch_dist)
                    base_y += random.randint(-glitch_dist, glitch_dist)
                
                base_x = max(100, min(SCREEN_WIDTH - 100, base_x))
                base_y = max(100, min(SCREEN_HEIGHT - 100, base_y))
                
                def apply_transform(surf):
                    if scale_x != 1.0 or scale_y != 1.0:
                        w, h = surf.get_width(), surf.get_height()
                        surf = pygame.transform.smoothscale(surf, (max(1, int(w * scale_x)), max(1, int(h * scale_y))))
                    if rot_angle != 0:
                        surf = pygame.transform.rotate(surf, rot_angle)
                    return surf

                # Draw black outline
                base_border_surf = get_rendered_text(lyric_text, font_size, (0, 0, 0))
                border_surf = apply_transform(base_border_surf)
                border_surf.set_alpha(alpha)
                rect_b = border_surf.get_rect(center=(base_x, base_y))
                
                offsets = [(-3, -3), (3, -3), (-3, 3), (3, 3)]
                for ox, oy in offsets:
                    surface.blit(border_surf, (rect_b.x + ox, rect_b.y + oy))
                
                # Chromatic Aberration Layers
                c_dist = int(2 + 10 * energy)
                offsets_and_colors = [
                    (random.randint(-c_dist*2, -c_dist) if glitch_active else -2, random.randint(-5, 5) if glitch_active else 0, (255, 0, 80)),
                    (random.randint(c_dist, c_dist*2) if glitch_active else 2, random.randint(-5, 5) if glitch_active else 0, (0, 255, 200)),
                    (0, 0, (255, 255, 255))
                ]
                
                for ox, oy, color in offsets_and_colors:
                    base_txt_surf = get_rendered_text(lyric_text, font_size, color)
                    txt_surf = apply_transform(base_txt_surf)
                    draw_alpha = alpha
                    if glitch_active and random.random() < 0.4:
                        draw_alpha = int(alpha * 0.3)
                    txt_surf.set_alpha(draw_alpha)
                    
                    rect = txt_surf.get_rect(center=(base_x + ox, base_y + oy))
                    surface.blit(txt_surf, rect.topleft)

class CoolFriendsLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.boss_img_path = SONGS[name]["img"]
        if os.path.exists(self.boss_img_path):
            self.boss_img = pygame.image.load(self.boss_img_path).convert_alpha()
        else:
            self.boss_img = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.circle(self.boss_img, COLORS['pink'], (100, 100), 100) # pink circle boss fallback
        self.boss_img = pygame.transform.smoothscale(self.boss_img, (200, 200))
        self.boss_x = SCREEN_WIDTH // 2
        self.boss_y = SCREEN_HEIGHT // 2
        self.boss_target_x = self.boss_x
        self.boss_target_y = self.boss_y
        self.attack_mode = 0
        self.last_attack_change = 0
        
        # Red smiley tint setup
        self.tint = pygame.Surface(self.boss_img.get_size(), pygame.SRCALPHA)
        self.tint.fill((255, 0, 0, 100)) # subtle red tint

    def update(self, dt):
        super().update(dt)
        self.boss_x += (self.boss_target_x - self.boss_x) * 0.05
        self.boss_y += (self.boss_target_y - self.boss_y) * 0.05

    def on_beat(self, elapsed):
        sec = elapsed / 1000.0
        level_progress = min(1.0, elapsed / 180000.0)

        if sec - self.last_attack_change > max(1.5, 4.0 - level_progress * 2.5):
            self.attack_mode = (self.attack_mode + 1) % 4
            self.last_attack_change = sec
            self.boss_x = random.randint(200, SCREEN_WIDTH - 200) # Teleport instantly on beat!
            self.boss_y = random.randint(200, SCREEN_HEIGHT - 200)
            self.boss_target_x = self.boss_x
            self.boss_target_y = self.boss_y
            self.app.shake_amount = 15 + int(10 * level_progress)

        intensity_mult = 1 + int(level_progress * 1.5)

        if self.attack_mode == 0:
            count = 8 * intensity_mult
            for i in range(count):
                angle = i * (math.pi / (count / 2.0)) + sec
                speed = 5 + 3 * level_progress
                self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 40, math.cos(angle)*speed, math.sin(angle)*speed, 'circle', max(100, 500 - int(level_progress*300))))
        elif self.attack_mode == 1:
            for _ in range(intensity_mult):
                angle = sec * 5 + random.uniform(0, math.pi*2)
                speed = 8 + 4 * level_progress
                self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 30, math.cos(angle)*speed, math.sin(angle)*speed, 'circle', 0))
                self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 30, math.cos(angle + math.pi)*speed, math.sin(angle + math.pi)*speed, 'circle', 0))
        elif self.attack_mode == 2:
            for _ in range(intensity_mult):
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), -50, 60, 0, 10 + 5*level_progress, 'rect', 200))
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 50, 60, 0, -10 - 5*level_progress, 'rect', 200))
        elif self.attack_mode == 3:
            if self.app.players:
                for _ in range(intensity_mult):
                    p = random.choice(self.app.players)
                    dx = p.x - self.boss_x
                    dy = p.y - self.boss_y
                    mag = math.sqrt(dx*dx + dy*dy)
                    if mag > 0:
                        speed = 12 + 6 * level_progress
                        angle_offset = random.uniform(-0.3, 0.3) * level_progress
                        base_angle = math.atan2(dy, dx) + angle_offset
                        self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 40, math.cos(base_angle)*speed, math.sin(base_angle)*speed, 'circle', max(50, 300 - int(level_progress*200))))

    def draw_extra(self, surface):
        pulse = 1.0 + math.sin(self.elapsed_ms * 0.01) * 0.05
        w, h = int(200 * pulse), int(200 * pulse)
        scaled_img = pygame.transform.smoothscale(self.boss_img, (w, h))
        
        # Apply red tint since user mentioned red smiley
        tint_scaled = pygame.transform.scale(self.tint, (w, h))
        scaled_img.blit(tint_scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        rect = scaled_img.get_rect(center=(int(self.boss_x), int(self.boss_y)))
        surface.blit(scaled_img, rect.topleft)

class AnnihilateLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.attack_tick = 0
        self.background_text = ""
        self.text_particles = []
        
        # Trigger flags
        self.exp1_triggered = False
        self.exp2_triggered = False
        self.exp3_triggered = False
        self.fall_triggered = False

        # Load Spikey ball image
        self.spikey_img = None
        if os.path.exists(os.path.join(MEDIA_PATH, "Spikey.png")):
            try:
                self.spikey_img = pygame.image.load(os.path.join(MEDIA_PATH, "Spikey.png")).convert_alpha()
                self.spikey_img = pygame.transform.smoothscale(self.spikey_img, (150, 150))
            except Exception as e:
                print("Failed to load Spikey.png:", e)

    def spawn_explosion(self, center_x, center_y):
        self.app.shake_amount = 40
        level_progress = min(1.0, self.elapsed_ms / 300000.0)
        count = int(25 + 25 * level_progress)
        for i in range(count):
            angle = i * (math.pi / (count / 2.0)) + random.uniform(-0.1, 0.1)
            speed = random.uniform(10 + 5*level_progress, 20 + 10*level_progress)
            self.obstacles.append(Obstacle(
                center_x, center_y, 30, 
                math.cos(angle) * speed, math.sin(angle) * speed, 
                type=random.choice(['circle', 'triangle']), warning=0, damage=10
            ))

    def update(self, dt):
        super().update(dt)
        elapsed = self.elapsed_ms
        sec = elapsed / 1000.0

        # Harder: Border spikey collision check all of phase 2 (95000 ms to 186000 ms)
        if 95000 <= elapsed < 186000:
            t_appear = 1.0
            if elapsed < 97000:
                t_appear = (elapsed - 95000) / 2000.0
            elif elapsed >= 184000:
                t_appear = max(0.0, 1.0 - (elapsed - 184000) / 2000.0)
            
            spikey_depth = 75 * t_appear
            for p in self.app.players:
                if p.invuln_timer <= 0:
                    hit = False
                    if p.x < spikey_depth: hit = True
                    elif p.x > SCREEN_WIDTH - spikey_depth: hit = True
                    elif p.y < spikey_depth: hit = True
                    elif p.y > SCREEN_HEIGHT - spikey_depth: hit = True
                    if hit:
                        self.app.health -= 15 # spikey damage
                        self.app.shake_amount = 20
                        p.invuln_timer = 1000

        # Precise explosion triggers at 4:52 (292000), 4:56.5 (296500), and 5:00 (300000)
        if elapsed >= 292000 and not self.exp1_triggered:
            self.exp1_triggered = True
            self.spawn_explosion(random.randint(300, SCREEN_WIDTH - 300), random.randint(200, SCREEN_HEIGHT - 200))
        if elapsed >= 296500 and not self.exp2_triggered:
            self.exp2_triggered = True
            self.spawn_explosion(random.randint(300, SCREEN_WIDTH - 300), random.randint(200, SCREEN_HEIGHT - 200))
        if elapsed >= 300000 and not self.exp3_triggered:
            self.exp3_triggered = True
            self.spawn_explosion(random.randint(300, SCREEN_WIDTH - 300), random.randint(200, SCREEN_HEIGHT - 200))

        # Gravity and physics trigger for falling text at 5:04 (304000)
        if elapsed >= 304000 and not self.fall_triggered:
            self.fall_triggered = True
            full_text = "YOU HAVE BEEN DESTROYED."
            font = get_font(80, bold=True)
            char_widths = [font.render(c, True, (255, 0, 0)).get_width() for c in full_text]
            total_width = sum(char_widths)
            start_x = SCREEN_WIDTH // 2 - total_width // 2
            current_x = start_x
            for i, char in enumerate(full_text):
                if char != " ":
                    self.text_particles.append({
                        'char': char,
                        'x': current_x + char_widths[i] // 2,
                        'y': SCREEN_HEIGHT // 2,
                        'vx': random.uniform(-6, 6),
                        'vy': random.uniform(-12, -4), # slight pop up then downward plunge
                        'rot': 0,
                        'rot_speed': random.uniform(-10, 10)
                    })
                current_x += char_widths[i]

        # Update text particle positions & physics
        for p in self.text_particles:
            p['x'] += p['vx'] * (dt / 16.0)
            p['y'] += p['vy'] * (dt / 16.0)
            p['vy'] += 0.45 * (dt / 16.0) # gravity effect
            p['rot'] += p['rot_speed'] * (dt / 16.0)

        # Background text & special phase control based on elapsed time
        if 92000 <= elapsed < 95000:
            self.obstacles.clear()
            sub = elapsed - 92000
            if sub < 400:
                self.background_text = "YOU"
            elif sub < 800:
                self.background_text = "YOU HAVE"
            elif sub < 1200:
                self.background_text = "YOU HAVE BEEN"
            elif sub < 1600:
                self.background_text = "YOU HAVE BEEN DES"
            else:
                self.background_text = "YOU HAVE BEEN DESTROYED."
        elif 186000 <= elapsed < 197500:
            ratio = (elapsed - 186000) / (197500 - 186000)
            flicker_interval = max(30, int(500 * (1 - ratio)))
            if (elapsed // flicker_interval) % 2 == 0:
                self.background_text = "YOU HAVE BEEN DESTROYED."
            else:
                self.background_text = ""
        elif 197500 <= elapsed < 199000:
            self.background_text = "YOU HAVE BEEN DESTROYED."
        elif 290000 <= elapsed < 292000:
            self.obstacles.clear()
            self.background_text = ""
        elif 292000 <= elapsed < 304000:
            self.background_text = ""
            for t_exp in [292000, 296500, 300000]:
                if t_exp <= elapsed < t_exp + 800:
                    sub_elapsed = elapsed - t_exp
                    if sub_elapsed < 200 or (400 <= sub_elapsed < 600):
                        self.background_text = "YOU HAVE BEEN DESTROYED."
                    break
        else:
            self.background_text = ""

    def on_beat(self, elapsed):
        sec = self.elapsed_ms / 1000.0
        self.attack_tick += 1

        level_progress = min(1.0, self.elapsed_ms / 300000.0)
        intensity_mult = 1 + int(level_progress * 1.5)

        if self.elapsed_ms < 92000:
            cycle_sec = sec % 15.0
            if cycle_sec >= 11.0:
                return # Silence rest period between events: let active obstacles play out!

            block = int(sec // 15)
            mode = block % 2
            if mode == 0:
                for _ in range(intensity_mult):
                    self.obstacles.append(Obstacle(-50, random.randint(100, SCREEN_HEIGHT-100), 120, 24 + 10*level_progress, 0, 'rect', 180))
                    self.obstacles.append(Obstacle(SCREEN_WIDTH+50, random.randint(100, SCREEN_HEIGHT-100), 120, -24 - 10*level_progress, 0, 'rect', 180))
            elif mode == 1:
                x = 0 if random.random() < 0.5 else SCREEN_WIDTH
                y = random.randint(100, SCREEN_HEIGHT-100)
                count = 8 + int(4 * level_progress)
                for i in range(count):
                    angle = i * (math.pi / (count/2.0)) - math.pi/2
                    if x == SCREEN_WIDTH:
                        angle += math.pi
                    self.obstacles.append(Obstacle(x, y, 35, math.cos(angle)*(16 + 8*level_progress), math.sin(angle)*(16 + 8*level_progress), 'circle', 120))
        elif 92000 <= self.elapsed_ms < 95000:
            pass # No beat spawns during transition sequence
        elif 95000 <= self.elapsed_ms < 186000:
            cycle_sec = (sec - 95.0) % 15.0
            if cycle_sec >= 11.0:
                return # Silence rest period between events: let active obstacles play out!

            block = int((sec - 95.0) // 15)
            mode = block % 3
            if mode == 0:
                # Two top down stompers at once! (Slightly easier)
                self.obstacles.append(Obstacle(random.randint(100, SCREEN_WIDTH//2), -100, 180, 0, 22, 'rect', 300, rot_speed=0))
                self.obstacles.append(Obstacle(random.randint(SCREEN_WIDTH//2, SCREEN_WIDTH-100), -100, 180, 0, 22, 'rect', 300, rot_speed=0))
            elif mode == 1:
                # Expanding triangle rings (Slightly easier: 10 triangles, slower)
                for i in range(10):
                    angle = i * (math.pi / 5)
                    self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 40, math.cos(angle)*13, math.sin(angle)*13, 'triangle', 250))
            elif mode == 2:
                # Dual tracking spiral attacks! (Slightly easier: slower, more warning)
                if self.app.players:
                    p = random.choice(self.app.players)
                    dx, dy = p.x - SCREEN_WIDTH//2, p.y - SCREEN_HEIGHT//2
                    mag = math.sqrt(dx*dx + dy*dy)
                    if mag > 0:
                        self.obstacles.append(Obstacle(SCREEN_WIDTH//3, SCREEN_HEIGHT//2, 40, (dx/mag)*11, (dy/mag)*11, 'circle', 250))
                        self.obstacles.append(Obstacle((2*SCREEN_WIDTH)//3, SCREEN_HEIGHT//2, 40, (dx/mag)*11, (dy/mag)*11, 'circle', 250))
        elif 186000 <= self.elapsed_ms < 199000:
            # Medium beat spawns during the heavy flicker sequence
            if self.attack_tick % 3 == 0:
                self.obstacles.append(Obstacle(-50, random.randint(100, SCREEN_HEIGHT-100), 90, 22, 0, 'rect', 150))
        elif 199000 <= self.elapsed_ms < 290000:
            cycle_sec = (sec - 199.0) % 15.0
            if cycle_sec >= 11.0:
                return # Silence rest period between events: let active obstacles play out!

            block = int((sec - 199.0) // 15)
            mode = block % 4
            if mode == 0:
                for _ in range(intensity_mult):
                    self.obstacles.append(Obstacle(-50, random.randint(100, SCREEN_HEIGHT-100), 120, 26 + 10*level_progress, 0, 'rect', 120))
            elif mode == 1:
                count = 15 + int(10 * level_progress)
                for i in range(count):
                    angle = i * (math.pi / (count/2.0))
                    speed = 14 + 10*level_progress
                    self.obstacles.append(Obstacle(random.randint(100, SCREEN_WIDTH-100), 0, 30, math.cos(angle)*speed, math.sin(angle)*speed, 'circle', 100))
            elif mode == 2:
                for _ in range(intensity_mult):
                    for p in self.app.players:
                        self.obstacles.append(Obstacle(p.x + random.randint(-50, 50), -50, 60, 0, 25 + 15*level_progress, 'triangle', 90))
            elif mode == 3:
                for _ in range(intensity_mult):
                    self.obstacles.append(Obstacle(-50, random.randint(100, SCREEN_HEIGHT-100), 120, 25 + 10*level_progress, 0, 'rect', 120))
                    self.obstacles.append(Obstacle(SCREEN_WIDTH+50, random.randint(100, SCREEN_HEIGHT-100), 120, -25 - 10*level_progress, 0, 'rect', 120))
        else:
            pass # No beat spawns in final explosion timeline

    def draw_extra(self, surface):
        elapsed = self.elapsed_ms

        # Draw spikey border hazard in Phase 2
        if 95000 <= elapsed < 186000 and self.spikey_img:
            t_appear = 1.0
            if elapsed < 97000:
                t_appear = (elapsed - 95000) / 2000.0
            elif elapsed >= 184000:
                t_appear = max(0.0, 1.0 - (elapsed - 184000) / 2000.0)
            
            offset = 75 * (1.0 - t_appear)
            rot_angle = (self.elapsed_ms // 5) % 360
            rot_spikey = pygame.transform.rotate(self.spikey_img, rot_angle)
            half_s = rot_spikey.get_width() // 2
            
            # Top/Bottom borders
            for x in range(0, SCREEN_WIDTH + 150, 150):
                surface.blit(rot_spikey, (x - half_s, 0 - half_s - int(offset)))
                surface.blit(rot_spikey, (x - half_s, SCREEN_HEIGHT - half_s + int(offset)))
                
            # Left/Right borders
            for y in range(150, SCREEN_HEIGHT, 150):
                surface.blit(rot_spikey, (0 - half_s - int(offset), y - half_s))
                surface.blit(rot_spikey, (SCREEN_WIDTH - half_s + int(offset), y - half_s))
        
        # If we have not fallen apart yet, render background text
        if elapsed < 304000:
            if self.background_text:
                font = get_font(100, bold=True)
                txt_surf = font.render(self.background_text, True, (255, 0, 0)) # Red text in the background
                rect = txt_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                surface.blit(txt_surf, rect.topleft)
        else:
            # Render falling characters
            font = get_font(80, bold=True)
            for p in self.text_particles:
                char_surf = font.render(p['char'], True, (255, 0, 0))
                rot_surf = pygame.transform.rotate(char_surf, p['rot'])
                rect = rot_surf.get_rect(center=(int(p['x']), int(p['y'])))
                surface.blit(rot_surf, rect.topleft)

class CloseToMeLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.phase = 0
        self.last_arm_spawn = 0
        self.arms = [] # List of {'side': x, 'y': y, 'life': ms}

    def on_beat(self, elapsed):
        sec = elapsed / 1000.0
        level_progress = min(1.0, elapsed / 120000.0)
        intensity = 1 + int(level_progress * 2)
        
        if sec < 25:
            if len(self.obstacles) < 5 + intensity * 2:
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 60, random.uniform(-4 - 2*level_progress, 4 + 2*level_progress), random.uniform(-4 - 2*level_progress, 4 + 2*level_progress), 'rect', 800))
        
        if 25 <= sec < 26 and self.phase == 0:
            self.phase = 1
            self.obstacles.clear()
            self.app.shake_amount = 30
            warn_h = SCREEN_HEIGHT * 0.9
            # Warning block
            self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT + warn_h//2, SCREEN_WIDTH * 2, 0, -20, 'rect', 0, damage=0, alpha=100, rot_speed=0))

        if 26 <= sec < 38:
            if self.phase == 1: 
                self.phase = 2
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT + 500, SCREEN_WIDTH * 2, 0, -25 - 10*level_progress, 'rect', 500, rot_speed=0))
            elif self.phase == 2 and sec > 31:
                self.phase = 3
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, -500, SCREEN_WIDTH * 2, 0, 25 + 10*level_progress, 'rect', 500, rot_speed=0))

        if 38 <= sec < 60:
            arm_interval = max(200, 600 - int(level_progress * 300))
            if self.elapsed_ms - self.last_arm_spawn > arm_interval:
                self.last_arm_spawn = self.elapsed_ms
                for _ in range(intensity):
                    side = random.choice([0, SCREEN_WIDTH])
                    y = random.randint(100, SCREEN_HEIGHT - 100)
                    self.arms.append({'side': side, 'y': y, 'life': 1000})
                    self.obstacles.append(Obstacle(side, y, 40, (1 if side == 0 else -1) * (10 + 5*level_progress), random.uniform(-3, 3), 'rect', 0))

        if sec > 60:
            count = max(1, 4 + intensity)
            for _ in range(count):
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), -50, 20, 0, 12 + 8*level_progress, 'rect', 0))
            
            if not self.finished and not pygame.mixer.music.get_busy():
                self.finished = True
                self.app.fade_alpha = 0

    def update(self, dt):
        super().update(dt)
        # Update arms
        for arm in self.arms[:]:
            arm['life'] -= dt
            if arm['life'] <= 0: self.arms.remove(arm)
        
        if self.finished:
            self.app.fade_alpha += 3
            if self.app.fade_alpha >= 255: self.app.state = GameState.COMPLETED

    def draw_extra(self, surface):
        # Draw the actual hands/arms
        for arm in self.arms:
            color = COLORS['enemy']
            w, h = 300, 60
            x = arm['side'] - (w if arm['side'] > 0 else 0)
            y = arm['y'] - h//2
            # Draw arm
            pygame.draw.rect(surface, color, (x, y, w, h))
            # Draw "hand"
            hx = arm['side'] - (60 if arm['side'] > 0 else -w)
            pygame.draw.rect(surface, color, (hx - 30, y - 20, 60, 100))

class FinalBossLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.boss_img_path = SONGS[name]["img"]
        if os.path.exists(self.boss_img_path):
            self.boss_img = pygame.image.load(self.boss_img_path).convert_alpha()
        else:
            self.boss_img = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.polygon(self.boss_img, COLORS['enemy'], [(100, 0), (200, 200), (0, 200)])
        self.boss_img = pygame.transform.smoothscale(self.boss_img, (300, 300))
        self.boss_x = SCREEN_WIDTH // 2
        self.boss_y = 200
        self.boss_target_x = self.boss_x
        self.boss_target_y = self.boss_y
        self.attack_mode = 0
        self.last_attack_change = 0

    def update(self, dt):
        super().update(dt)
        self.boss_x += (self.boss_target_x - self.boss_x) * 0.08
        self.boss_y += (self.boss_target_y - self.boss_y) * 0.08

    def on_beat(self, elapsed):
        sec = elapsed / 1000.0
        level_progress = min(1.0, elapsed / 240000.0)

        change_interval = max(1.0, 3.0 - level_progress * 2.0)
        if sec - self.last_attack_change > change_interval:
            self.attack_mode = random.randint(0, 3)
            self.last_attack_change = sec
            self.boss_target_x = random.randint(200, SCREEN_WIDTH - 200)
            self.boss_target_y = random.randint(150, SCREEN_HEIGHT // 2)
            self.app.shake_amount = 10 + int(20 * level_progress)

        intensity = 1 + int(level_progress * 2)

        if self.attack_mode == 0:
            count = 12 + int(12 * level_progress)
            for i in range(count):
                angle = i * (math.pi / (count/2.0)) + sec
                speed = 12 + 8 * level_progress
                self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 45, math.cos(angle)*speed, math.sin(angle)*speed, 'triangle', max(100, 400 - int(level_progress*200))))
        elif self.attack_mode == 1:
            for i in range(4 * intensity):
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), -50, 60, random.uniform(-4, 4), 15 + 10*level_progress, 'triangle', max(50, 200 - int(level_progress*100))))
        elif self.attack_mode == 2:
            for _ in range(intensity):
                y = random.randint(100, SCREEN_HEIGHT - 100)
                speed = 25 + 15 * level_progress
                self.obstacles.append(Obstacle(-50, y, 70, speed, 0, 'triangle', max(50, 100 - int(level_progress*50)), rot_speed=15))
                self.obstacles.append(Obstacle(SCREEN_WIDTH + 50, y + 100, 70, -speed, 0, 'triangle', max(50, 100 - int(level_progress*50)), rot_speed=-15))
        elif self.attack_mode == 3:
            if self.app.players:
                p = random.choice(self.app.players)
                dx = p.x - self.boss_x
                dy = p.y - self.boss_y
                mag = math.sqrt(dx*dx + dy*dy)
                if mag > 0:
                    for _ in range(intensity):
                        for i in range(-2, 3):
                            angle_offset = i * 0.2 + random.uniform(-0.1, 0.1)*level_progress
                            base_angle = math.atan2(dy, dx) + angle_offset
                            speed = 14 + 10 * level_progress
                            self.obstacles.append(Obstacle(self.boss_x, self.boss_y, 40, math.cos(base_angle)*speed, math.sin(base_angle)*speed, 'triangle', max(50, 200 - int(level_progress*100))))

    def draw_extra(self, surface):
        pulse = 1.0 + math.sin(self.elapsed_ms * 0.02) * 0.08
        w, h = int(300 * pulse), int(300 * pulse)
        scaled_img = pygame.transform.smoothscale(self.boss_img, (w, h))
        rect = scaled_img.get_rect(center=(int(self.boss_x), int(self.boss_y)))
        surface.blit(scaled_img, rect.topleft)

class NeverGonnaGiveYouUpLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.phase = 0
        self.last_spawn = 0

    def on_beat(self, elapsed):
        sec = elapsed / 1000.0
        
        # Determine phase and clear obstacles on transition
        phase = 0
        if sec < 18: phase = 0
        elif sec < 35: phase = 1
        elif sec < 42: phase = 2
        elif sec < 60: phase = 3
        elif sec < 77: phase = 4
        elif sec < 85: phase = 5
        elif sec < 119: phase = 6
        elif sec < 136: phase = 7
        elif sec < 152: phase = 8
        elif sec < 160: phase = 9
        elif sec < 194: phase = 10
        else: phase = 11

        if phase != self.phase:
            self.obstacles.clear()
            self.phase = phase

        # Dynamic Camera Shake based on phase intensity
        intensity_map = {0: 1, 1: 2, 2: 5, 3: 10, 4: 2, 5: 5, 6: 12, 7: 1, 8: 2, 9: 6, 10: 15, 11: 0}
        shake_power = intensity_map.get(phase, 0)
        
        # Trigger heavy shake on downbeats if intensity is high
        if shake_power > 5 and int(sec * 1000) % 2120 < 100:
            self.app.shake_amount = max(self.app.shake_amount, shake_power * 1.5)
        elif int(sec * 1000) % 530 < 50:
            self.app.shake_amount = max(self.app.shake_amount, shake_power * 0.5)
            self.phase = phase

        # 12-Phase Cinematic Mapping for "Never Gonna Give You Up"
        # 0:00 - 0:18 Intro
        if sec < 18:
            if elapsed - self.last_spawn > 1000:
                x = random.randint(100, SCREEN_WIDTH-100)
                self.obstacles.append(Obstacle(x, -50, 50, 0, 5, 'circle', 800))
                self.last_spawn = elapsed

        # 0:18 - 0:35 Verse 1: DVD Bouncing blocks
        elif 18 <= sec < 35:
            if len(self.obstacles) < 5:
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 80, random.uniform(-6, 6), random.uniform(-6, 6), 'rect', 500))

        # 0:35 - 0:42 Pre-Chorus 1: Rising Bubbles
        elif 35 <= sec < 42:
            for _ in range(3):
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT+50, random.randint(20, 50), 0, random.uniform(-8, -12), 'circle', 0))

        # 0:42 - 1:00 Chorus 1: Starbursts
        elif 42 <= sec < 60:
            count = 8
            for i in range(count):
                angle = i * (math.pi / (count/2.0))
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 40, math.cos(angle)*12, math.sin(angle)*12, 'triangle', 200))

        # 1:00 - 1:17 Verse 2: Laser Sweeps
        elif 60 <= sec < 77:
            if elapsed - self.last_spawn > 1500:
                is_horiz = random.random() < 0.5
                if is_horiz:
                    self.obstacles.append(Obstacle(-100, random.randint(100, SCREEN_HEIGHT-100), 200, 25, 0, 'rect', 400))
                else:
                    self.obstacles.append(Obstacle(random.randint(100, SCREEN_WIDTH-100), -100, 200, 0, 25, 'rect', 400))
                self.last_spawn = elapsed

        # 1:17 - 1:25 Pre-Chorus 2: Bubbles + Slow Homing
        elif 77 <= sec < 85:
            self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT+50, 30, 0, -10, 'circle', 0))
            if elapsed - self.last_spawn > 2000 and self.app.players:
                p = random.choice(self.app.players)
                dx, dy = p.x - SCREEN_WIDTH//2, p.y - (-50)
                mag = max(1, math.sqrt(dx*dx + dy*dy))
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, -50, 80, (dx/mag)*6, (dy/mag)*6, 'circle', 400))
                self.last_spawn = elapsed

        # 1:25 - 1:59 Chorus 2 & 3: Rotating Windmill
        elif 85 <= sec < 119:
            # Huge beam segments from center
            for i in range(4):
                angle = i * (math.pi / 2) + sec * 2
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2 + math.cos(angle)*150, SCREEN_HEIGHT//2 + math.sin(angle)*150, 100, math.cos(angle)*15, math.sin(angle)*15, 'rect', 100, rot_speed=5))

        # 1:59 - 2:16 Bridge: Giant Pulses
        elif 119 <= sec < 136:
            if elapsed - self.last_spawn > 1200:
                self.obstacles.append(Obstacle(random.randint(100, SCREEN_WIDTH-100), random.randint(100, SCREEN_HEIGHT-100), 250, 0, 0, 'circle', 800))
                self.last_spawn = elapsed

        # 2:16 - 2:32 Verse 3: Edges Closing In
        elif 136 <= sec < 152:
            if sec < 137 and len([o for o in self.obstacles if o.size > 500]) == 0:
                self.obstacles.append(Obstacle(-400, SCREEN_HEIGHT//2, 1000, 8, 0, 'rect', 100))
                self.obstacles.append(Obstacle(SCREEN_WIDTH + 400, SCREEN_HEIGHT//2, 1000, -8, 0, 'rect', 100))
            
            # Spawn bouncy threats in the middle
            if elapsed - self.last_spawn > 1000:
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, -50, 40, random.uniform(-4, 4), 10, 'triangle', 0))
                self.last_spawn = elapsed

        # 2:32 - 2:40 Pre-Chorus 3: Fast Bubbles
        elif 152 <= sec < 160:
            for _ in range(5):
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT+50, random.randint(15, 35), 0, random.uniform(-12, -20), 'circle', 0))

        # 2:40 - 3:14 Final Chorus: The Grand Finale (Starbursts + Lasers)
        elif 160 <= sec < 194:
            count = 10
            for i in range(count):
                angle = i * (math.pi / (count/2.0)) - sec
                self.obstacles.append(Obstacle(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 35, math.cos(angle)*15, math.sin(angle)*15, 'triangle', 150))
            
            if elapsed - self.last_spawn > 1000:
                is_horiz = random.random() < 0.5
                if is_horiz:
                    self.obstacles.append(Obstacle(-100, random.randint(100, SCREEN_HEIGHT-100), 150, 30, 0, 'rect', 300))
                else:
                    self.obstacles.append(Obstacle(random.randint(100, SCREEN_WIDTH-100), -100, 150, 0, 30, 'rect', 300))
                self.last_spawn = elapsed

        # 3:14 - 3:30 Outro: Rain
        else:
            if elapsed - self.last_spawn > 300:
                self.obstacles.append(Obstacle(random.randint(0, SCREEN_WIDTH), -50, 20, 0, 6, 'circle', 0, damage=0, alpha=150))
                self.last_spawn = elapsed

# --- Custom Level ---
class CustomLevel(Level):
    def __init__(self, name, app, json_path):
        super().__init__(name, app)
        self.json_path = json_path
        self.obs_data = []
        self.chroma_curve = []
        self.boss_enabled = True
        self.chroma_enabled = True
        self.difficulty = "Normal"
        try:
            import json
            with open(json_path, 'r') as f:
                data = json.load(f)
                self.obs_data = data.get("obstacles", [])
                self.obs_data.sort(key=lambda o: o.get("time", 0))
                self.rms_curve = data.get("rms_curve", [])
                self.chroma_curve = data.get("chroma_curve", [])
                self.boss_enabled = data.get("boss_entity", True)
                self.chroma_enabled = data.get("chroma_colors", True)
                self.difficulty = data.get("difficulty", "Normal")
        except Exception as e:
            print("Error loading custom level:", e)
        self.spawn_idx = 0
        self.diff_mult = 1.0 if self.difficulty == "Normal" else (0.6 if self.difficulty == "Easy" else 1.5)

    def draw_background(self, surface):
        orig_pink = COLORS['pink']
        if getattr(self, 'chroma_enabled', False) and hasattr(self, 'chroma_curve') and self.chroma_curve:
            c_idx = int((self.elapsed_ms + self.app.lyric_offsets.get(self.name, 0)) / 400)
            if c_idx >= 0 and c_idx < len(self.chroma_curve):
                pitch = self.chroma_curve[c_idx]["pitch"]
                import colorsys
                r, g, b = colorsys.hsv_to_rgb(pitch / 11.0, 0.7, 1.0)
                COLORS['pink'] = (int(r*255), int(g*255), int(b*255))
        super().draw_background(surface)
        COLORS['pink'] = orig_pink

    def draw_extra(self, surface):
        # Boss Entity Logic
        if getattr(self, 'boss_enabled', False) and hasattr(self, 'rms_curve') and self.rms_curve:
            idx = int((self.elapsed_ms + self.app.lyric_offsets.get(self.name, 0)) / 100)
            if idx >= 0 and idx < len(self.rms_curve):
                energy = self.rms_curve[idx]["energy"]
                if energy > 0.4:
                    bx, by = SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 150
                    pulse = math.sin(pygame.time.get_ticks() * 0.01) * 20 * energy
                    b_size = 100 + pulse
                    
                    color = COLORS['enemy']
                    if getattr(self, 'chroma_enabled', False) and hasattr(self, 'chroma_curve') and self.chroma_curve:
                        c_idx = int((self.elapsed_ms + self.app.lyric_offsets.get(self.name, 0)) / 400)
                        if c_idx >= 0 and c_idx < len(self.chroma_curve):
                            pitch = self.chroma_curve[c_idx]["pitch"]
                            import colorsys
                            r, g, b = colorsys.hsv_to_rgb(pitch / 11.0, 0.8, 1.0)
                            color = (int(r*255), int(g*255), int(b*255))
                            
                    pts = [(bx, by - b_size), (bx + b_size, by), (bx, by + b_size), (bx - b_size, by)]
                    pygame.draw.polygon(surface, color, pts)
                    pygame.draw.polygon(surface, COLORS['white'], pts, 3)
                    
                    pygame.draw.circle(surface, COLORS['white'], (int(bx - 20), int(by - 10)), 8)
                    pygame.draw.circle(surface, COLORS['white'], (int(bx + 20), int(by - 10)), 8)
                    if energy > 0.6:
                        pygame.draw.line(surface, COLORS['white'], (bx - 30, by - 25), (bx - 10, by - 15), 3)
                        pygame.draw.line(surface, COLORS['white'], (bx + 30, by - 25), (bx + 10, by - 15), 3)

    def on_beat(self, elapsed):
        while self.spawn_idx < len(self.obs_data):
            obs = self.obs_data[self.spawn_idx]
            if elapsed >= obs.get("time", 0):
                size = int(obs.get("size", 50) * self.diff_mult)
                speed = obs.get("speed", 5) * self.diff_mult
                vx = obs.get("vx", 0) * self.diff_mult
                
                ox = obs.get("x", SCREEN_WIDTH//2)
                if ox == "PLAYER_X":
                    if self.app.players: ox = self.app.players[0].x
                    else: ox = SCREEN_WIDTH//2
                
                self.obstacles.append(Obstacle(
                    ox,
                    obs.get("y", -50),
                    size,
                    vx,
                    speed,
                    obs.get("shape", "rect"),
                    obs.get("warning_time", 800),
                    alpha=obs.get("alpha", 255),
                    lifespan=obs.get("lifespan", None)
                ))
                self.spawn_idx += 1
            else:
                break

# --- Screens ---
class UI:
    @staticmethod
    def draw_warning(app):
        if not hasattr(app, 'warning_start_time'):
            app.warning_start_time = pygame.time.get_ticks()
            
        elapsed = pygame.time.get_ticks() - app.warning_start_time
        
        # 1s fade in, 5s stay, 1s fade out = 7000ms total
        if elapsed > 7000:
            app.state = GameState.MENU
            return
            
        alpha = 255
        if elapsed < 1000:
            alpha = int((elapsed / 1000.0) * 255)
        elif elapsed > 6000:
            alpha = int(((7000 - elapsed) / 1000.0) * 255)
            
        screen.fill((0, 0, 0))
        warn_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        warn_surf.fill((0, 0, 0))
        
        font_huge = get_font(120, bold=True)
        title_surf = font_huge.render("DISCLAIMER !", True, (255, 0, 0))
        warn_surf.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 250)))
        
        font_text = get_font(40, bold=False)
        body_lines = [
            "This game contains flashing lights, rapidly moving patterns,",
            "and high contrast imagery which may trigger seizures for",
            "people with photosensitive epilepsy.",
            "",
            "Viewer discretion is advised."
        ]
        
        y_offset = SCREEN_HEIGHT//2 - 100
        for line in body_lines:
            line_surf = font_text.render(line, True, (255, 255, 255))
            warn_surf.blit(line_surf, line_surf.get_rect(center=(SCREEN_WIDTH//2, y_offset)))
            y_offset += 55
            
        warn_surf.set_alpha(alpha)
        screen.blit(warn_surf, (0, 0))

    @staticmethod
    def draw_menu(app):
        # Background and Particles
        if BG_IMG: 
            screen.blit(BG_IMG, (0,0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(100)
            screen.blit(overlay, (0, 0))
        else: 
            screen.fill(COLORS['bg'])

        # Update and draw particles
        for p in app.particles:
            p['y'] -= p['speed']
            if p['y'] < -20: p['y'] = SCREEN_HEIGHT + 20; p['x'] = random.randint(0, SCREEN_WIDTH)
            alpha = 100 + math.sin(pygame.time.get_ticks() * 0.002 + p['x']) * 50
            p_surf = pygame.Surface((p['size'], p['size']), pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (*p['color'], alpha), (0, 0, p['size'], p['size']))
            screen.blit(p_surf, (p['x'], p['y']))

        # Floating Title Animation
        time = pygame.time.get_ticks() * 0.002
        float_y = math.sin(time) * 15
        title_y = 180 + float_y
        
        if LOGO_IMG:
            # Logo Pulse
            logo_pulse = 1.0 + math.sin(time * 2) * 0.05
            logo_scaled = pygame.transform.smoothscale(LOGO_IMG, (int(130 * logo_pulse), int(130 * logo_pulse)))
            
            t1 = font_large.render("JUST", True, COLORS['white'])
            t_sh = font_large.render("SH", True, COLORS['pink'])
            t_pes = font_large.render("PES", True, COLORS['pink'])
            t2 = font_large.render("& BEATS", True, COLORS['blue'])
            
            total_w = t1.get_width() + 40 + t_sh.get_width() + 130 + t_pes.get_width()
            start_x = SCREEN_WIDTH // 2 - total_w // 2
            
            screen.blit(t1, (start_x, title_y))
            screen.blit(t_sh, (start_x + t1.get_width() + 40, title_y))
            
            logo_x = start_x + t1.get_width() + 40 + t_sh.get_width() + 10
            screen.blit(logo_scaled, (logo_x + (65 - logo_scaled.get_width()//2), title_y - 20 + (65 - logo_scaled.get_height()//2)))
            
            screen.blit(t_pes, (logo_x + 130, title_y))
            screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, title_y + 110))
        else:
            t = font_xl.render("JUST SHAPES & BEATS", True, COLORS['pink'])
            screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, title_y))

        # Polished Menu Buttons
        for i, opt in enumerate(app.menu_options):
            is_sel = (i == app.menu_idx)
            # Lerp for button scaling/offset
            target = 1.0 if is_sel else 0.0
            app.menu_sel_lerp[i] += (target - app.menu_sel_lerp[i]) * 0.15
            
            lerp = app.menu_sel_lerp[i]
            btn_w = 500 + (lerp * 50)
            btn_h = 70 + (lerp * 10)
            
            # Glow effect
            if lerp > 0.1:
                glow_surf = pygame.Surface((btn_w + 20, btn_h + 20), pygame.SRCALPHA)
                glow_alpha = int(lerp * 50 * (1 + math.sin(time * 3) * 0.3))
                pygame.draw.rect(glow_surf, (*COLORS['blue'], glow_alpha), (0, 0, btn_w + 20, btn_h + 20), border_radius=15)
                screen.blit(glow_surf, (SCREEN_WIDTH//2 - btn_w//2 - 10, 480 + i*90 - 10))

            bg_alpha = 100 + int(lerp * 100)
            btn_rect = pygame.Rect(SCREEN_WIDTH//2 - btn_w//2, 480 + i*90, btn_w, btn_h)
            pygame.draw.rect(screen, (30, 30, 40, bg_alpha), btn_rect, border_radius=12)
            
            if is_sel:
                pygame.draw.rect(screen, COLORS['white'], btn_rect, 3, border_radius=12)
            
            color = COLORS['white'] if is_sel else (180, 180, 190)
            f_size = int(40 + (lerp * 5))
            txt = get_font(f_size).render(opt, True, color)
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, btn_rect.centery - txt.get_height()//2))


    @staticmethod
    def draw_level_select(app):
        screen.fill((2, 2, 5))
        if BG_IMG:
            bg_copy = BG_IMG.copy()
            bg_copy.set_alpha(40)
            screen.blit(bg_copy, (0,0))

        # Vertical List on Left
        item_w, item_h = 450, 90
        spacing = 20
        
        # Smooth scrolling logic
        app.scroll_y += (app.target_scroll_y - app.scroll_y) * 0.1
        start_y = SCREEN_HEIGHT // 2 + app.scroll_y - item_h // 2
        
        for i, name in enumerate(app.levels):
            y = start_y + i * (item_h + spacing)
            if y < -200 or y > SCREEN_HEIGHT + 200: continue
            
            is_selected = (i == app.selected_level_idx)
            # Target offset animation: selected item moves right
            target_x = 100 if is_selected else 50
            app.item_offsets[i] += (target_x - app.item_offsets[i]) * 0.2
            
            rect = pygame.Rect(app.item_offsets[i], y, item_w, item_h)
            
            # Item Background
            # Secret level is 100% invisible in the list
            alpha = 255 if name != "Secret" else 0
            bg_color = (60, 60, 80) if is_selected else (30, 30, 40)
            
            item_surf = pygame.Surface((item_w, item_h), pygame.SRCALPHA)
            # Only draw if not secret
            if name != "Secret":
                pygame.draw.rect(item_surf, (*bg_color, alpha), (0, 0, item_w, item_h), border_radius=15)
                if is_selected:
                    pygame.draw.rect(item_surf, (0, 180, 255), (0, 0, item_w, item_h), 4, border_radius=15)
            
                song_data = SONGS[name]
                font_sz = 36
                title_txt = get_font(font_sz).render(name, True, COLORS['white'])
                while title_txt.get_width() > 380 and font_sz > 14:
                    font_sz -= 2
                    title_txt = get_font(font_sz).render(name, True, COLORS['white'])
                item_surf.blit(title_txt, (25, 10))
                
                artist_txt = get_font(20, False).render(song_data["artist"], True, (150, 150, 170))
                item_surf.blit(artist_txt, (25, 55))
                
                if getattr(app, 'delete_mode', False) and song_data.get("class") == CustomLevel:
                    trash_surf = get_font(40).render("[X]", True, COLORS['enemy'])
                    item_surf.blit(trash_surf, (item_w - 60, 25))
            
            screen.blit(item_surf, rect.topleft)

        # Right Side Details
        selected_name = app.levels[app.selected_level_idx]
        selected_song = SONGS[selected_name]
        detail_x = SCREEN_WIDTH - 650
        
        # Large Title and Artist
        font_sz = 80
        disp_name = selected_name.upper() if selected_name != "Secret" else "UNKNOWN"
        big_title = get_font(font_sz).render(disp_name, True, COLORS['white'])
        while big_title.get_width() > 600 and font_sz > 30:
            font_sz -= 5
            big_title = get_font(font_sz).render(disp_name, True, COLORS['white'])
        screen.blit(big_title, (detail_x, 100))
        
        big_artist = get_font(35, False).render(selected_song["artist"].upper(), True, (200, 200, 200))
        screen.blit(big_artist, (detail_x + 5, 190))
        
        # Frame and Album Art
        img_size = 500
        img_rect = pygame.Rect(detail_x, 300, img_size, img_size)
        pygame.draw.rect(screen, (40, 40, 50), img_rect, border_radius=10)
        
        if selected_song.get("surf"):
            # Animation: pulse image slightly
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 5
            s = img_size - 20 + pulse
            scaled_img = pygame.transform.scale(selected_song["surf"], (int(s), int(s)))
            screen.blit(scaled_img, (img_rect.centerx - s//2, img_rect.centery - s//2))
        else:
            q_txt = get_font(200).render("?", True, (80, 80, 90))
            screen.blit(q_txt, (img_rect.centerx - q_txt.get_width()//2, img_rect.centery - q_txt.get_height()//2))

        if getattr(app, 'delete_confirm', None) is not None:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            box_w, box_h = 500, 300
            pygame.draw.rect(overlay, (20, 20, 30, 250), (SCREEN_WIDTH//2 - box_w//2, SCREEN_HEIGHT//2 - box_h//2, box_w, box_h), border_radius=15)
            pygame.draw.rect(overlay, COLORS['enemy'], (SCREEN_WIDTH//2 - box_w//2, SCREEN_HEIGHT//2 - box_h//2, box_w, box_h), 3, border_radius=15)
            
            t = get_font(30).render(f"Delete '{app.delete_confirm}'?", True, COLORS['white'])
            overlay.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, SCREEN_HEIGHT//2 - 50))
            
            t2 = get_font(24).render("Y to Confirm / N to Cancel", True, (200, 200, 200))
            overlay.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, SCREEN_HEIGHT//2 + 20))
            screen.blit(overlay, (0, 0))

    @staticmethod
    def draw_skins(app):
        screen.fill(COLORS['bg'])
        if BG_IMG: screen.blit(BG_IMG, (0,0))
        title = font_large.render("CUSTOMIZE SHAPES", True, COLORS['white'])
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        p1_x, p2_x = SCREEN_WIDTH // 4, (SCREEN_WIDTH // 4) * 3
        draw_shape(screen, app.p1_shape, SHAPE_COLORS[app.p1_shape], (p1_x, 400), 150)
        t1 = font_medium.render("PLAYER 1", True, COLORS['white'])
        screen.blit(t1, (p1_x - t1.get_width()//2, 250))
        if app.is_p2_enabled:
            draw_shape(screen, app.p2_shape, SHAPE_COLORS[app.p2_shape], (p2_x, 400), 150)
            t2 = font_medium.render("PLAYER 2", True, COLORS['white'])
            screen.blit(t2, (p2_x - t2.get_width()//2, 250))
        else:
            t2 = font_medium.render("P2 DISABLED", True, (50, 50, 50))
            screen.blit(t2, (p2_x - t2.get_width()//2, 400))

    @staticmethod
    def draw_settings(app):
        screen.fill(COLORS['bg'])
        if BG_IMG: screen.blit(BG_IMG, (0,0))
        
        box_w, box_h = 700, 500
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (20, 20, 35, 200), (0, 0, box_w, box_h), border_radius=25)
        pygame.draw.rect(box_surf, COLORS['blue'], (0, 0, box_w, box_h), 5, border_radius=25)
        
        title_txt = font_large.render("SETTINGS", True, COLORS['pink'])
        box_surf.blit(title_txt, (box_w//2 - title_txt.get_width()//2, 50))
        
        for idx, opt in enumerate(app.settings_options):
            is_sel = (idx == app.settings_idx)
            color = COLORS['white'] if is_sel else (160, 160, 170)
            if is_sel:
                color = COLORS['blue'] if idx == 0 else COLORS['pink']
            opt_txt = font_medium.render(opt, True, color)
            box_surf.blit(opt_txt, (box_w//2 - opt_txt.get_width()//2, 180 + idx * 100))
            
            if is_sel:
                pygame.draw.polygon(box_surf, color, [
                    (box_w//2 - opt_txt.get_width()//2 - 40, 180 + idx * 100 + 15),
                    (box_w//2 - opt_txt.get_width()//2 - 20, 180 + idx * 100 + 25),
                    (box_w//2 - opt_txt.get_width()//2 - 40, 180 + idx * 100 + 35)
                ])
                
        rect = box_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(box_surf, rect.topleft)

    @staticmethod
    def draw_level_maker(app):
        screen.fill(COLORS['bg'])
        if BG_IMG: screen.blit(BG_IMG, (0,0))
        
        box_w, box_h = 800, 600
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (20, 20, 35, 200), (0, 0, box_w, box_h), border_radius=25)
        pygame.draw.rect(box_surf, COLORS['pink'], (0, 0, box_w, box_h), 5, border_radius=25)
        
        title_txt = font_large.render("LEVEL MAKER", True, COLORS['pink'])
        box_surf.blit(title_txt, (box_w//2 - title_txt.get_width()//2, 30))
        
        status_raw = getattr(app, 'lm_status', "")
        status_txt = font_medium.render(status_raw, True, COLORS['yellow'])
        if status_txt.get_width() > box_w - 40:
            sz = 40
            while status_txt.get_width() > box_w - 40 and sz > 14:
                sz -= 2
                status_txt = get_font(sz).render(status_raw, True, COLORS['yellow'])
        box_surf.blit(status_txt, (box_w//2 - status_txt.get_width()//2, 110))
        
        if getattr(app, 'lm_state', 0) == 0:
            pygame.draw.rect(box_surf, (10, 10, 10), (100, 250, 600, 80), border_radius=10)
            pygame.draw.rect(box_surf, COLORS['blue'], (100, 250, 600, 80), 3, border_radius=10)
            
            q = getattr(app, 'lm_query', "")
            cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            q_txt = font_medium.render(q + cursor, True, COLORS['white'])
            box_surf.blit(q_txt, (120, 290 - q_txt.get_height()//2))
            
            hint_txt = get_font(24).render("Enter song name/URL & press ENTER", True, (150, 150, 150))
            box_surf.blit(hint_txt, (box_w//2 - hint_txt.get_width()//2, 350))
            
        elif getattr(app, 'lm_state', 0) == 1:
            p_w, p_h = 600, 20
            pygame.draw.rect(box_surf, (50, 50, 50), (box_w//2 - p_w//2, 300, p_w, p_h), border_radius=10)
            progress = getattr(app, 'lm_progress', 0.0)
            if progress > 0:
                fill_w = int(p_w * progress)
                pygame.draw.rect(box_surf, COLORS['pink'], (box_w//2 - p_w//2, 300, fill_w, p_h), border_radius=10)
                
        elif getattr(app, 'lm_state', 0) >= 2:
            hint_txt = get_font(30).render("Press ESC to return to Menu", True, (200, 200, 200))
            box_surf.blit(hint_txt, (box_w//2 - hint_txt.get_width()//2, 400))
            
        rect = box_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(box_surf, rect.topleft)

    @staticmethod
    def draw_level_config(app):
        screen.fill(COLORS['bg'])
            
        # Left Side Preview
        preview_rect = pygame.Rect(50, 50, SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 100)
        pygame.draw.rect(screen, (20, 20, 30), preview_rect, border_radius=20)
        pygame.draw.rect(screen, COLORS['pink'], preview_rect, 4, border_radius=20)
        
        preview_title = get_font(40).render("Sync Preview", True, COLORS['pink'])
        screen.blit(preview_title, (preview_rect.centerx - preview_title.get_width()//2, 70))
        
        # Draw lyrics inside preview
        elapsed = getattr(app, 'config_start_pos', 0)
        if hasattr(app, 'config_start_time'):
            elapsed += pygame.time.get_ticks() - app.config_start_time
            
        song_name = getattr(app, 'config_level_name', "")
        if song_name in SONGS:
            song_data = SONGS[song_name]
            lrc_path = song_data.get("json_path", "").replace(".json", ".lrc")
            if os.path.exists(lrc_path):
                if not hasattr(app, 'config_lyrics'):
                    app.config_lyrics = parse_lrc(lrc_path)
                    
                current_text = ""
                delay = getattr(app, 'config_delay', 0)
                for l in app.config_lyrics:
                    if elapsed >= l['time'] + delay:
                        current_text = l['text']
                    else:
                        break
                        
                if current_text:
                    sz = 50
                    txt = get_font(sz).render(current_text, True, COLORS['white'])
                    while txt.get_width() > preview_rect.width - 40 and sz > 14:
                        sz -= 2
                        txt = get_font(sz).render(current_text, True, COLORS['white'])
                    screen.blit(txt, (preview_rect.centerx - txt.get_width()//2, preview_rect.centery))
                    
        # Right Side Options
        opt_x = SCREEN_WIDTH//2 + 50
        opt_y = SCREEN_HEIGHT//2 - 150
        
        t1 = get_font(60).render("Configuration", True, COLORS['white'])
        screen.blit(t1, (opt_x, opt_y - 100))
        
        opts = [
            f"Delay: {getattr(app, 'config_delay', 0)} ms",
            f"Difficulty: {getattr(app, 'config_diff', 'Normal')}",
            f"Boss Entity: {'ON' if getattr(app, 'config_boss', True) else 'OFF'}",
            f"Chroma Colors: {'ON' if getattr(app, 'config_chroma', True) else 'OFF'}",
            "Save & Continue"
        ]
        
        for idx, text in enumerate(opts):
            color = COLORS['yellow'] if getattr(app, 'config_idx', 0) == idx else (200, 200, 200)
            if text == "Save & Continue": color = COLORS['green'] if getattr(app, 'config_idx', 0) == idx else (200, 200, 200)
            
            t = get_font(40).render(text, True, color)
            screen.blit(t, (opt_x, opt_y + idx * 60))
            if getattr(app, 'config_idx', 0) == idx and idx < 4:
                screen.blit(get_font(30).render("<   >", True, COLORS['yellow']), (opt_x - 60, opt_y + idx * 60 + 5))

# --- Main App Logic ---
def main():
    import os, glob, json
    custom_dir = os.path.join(os.path.dirname(__file__), "CustomLevels")
    if os.path.exists(custom_dir):
        for f in glob.glob(os.path.join(custom_dir, "*.json")):
            try:
                with open(f, 'r') as fp:
                    data = json.load(fp)
                    name = data.get("name", os.path.basename(f))
                    SONGS[name] = {
                        "path": data.get("path", ""),
                        "artist": data.get("artist", "Custom Level"),
                        "surf": None,
                        "class": CustomLevel,
                        "json_path": f
                    }
            except: pass
            
    app = App()
    app.last_joy_x = 0
    app.last_joy_y = 0
    while app.running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: app.running = False
            elif event.type == pygame.JOYAXISMOTION:
                if event.axis == 1:
                    if event.value < -0.5 and getattr(app, 'last_joy_y', 0) >= -0.5:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_w}))
                    elif event.value > 0.5 and getattr(app, 'last_joy_y', 0) <= 0.5:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_s}))
                    app.last_joy_y = event.value
                elif event.axis == 0:
                    if event.value < -0.5 and getattr(app, 'last_joy_x', 0) >= -0.5:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_a}))
                    elif event.value > 0.5 and getattr(app, 'last_joy_x', 0) <= 0.5:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_d}))
                    app.last_joy_x = event.value
            elif event.type == pygame.JOYHATMOTION:
                if event.hat == 0:
                    hx, hy = event.value
                    if hy == 1 and getattr(app, 'last_hat_y', 0) != 1:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_w}))
                    elif hy == -1 and getattr(app, 'last_hat_y', 0) != -1:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_s}))
                    app.last_hat_y = hy
                    
                    if hx == -1 and getattr(app, 'last_hat_x', 0) != -1:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_a}))
                    elif hx == 1 and getattr(app, 'last_hat_x', 0) != 1:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_d}))
                    app.last_hat_x = hx
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in [0, 1, 9]:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
                elif event.button == 6:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE}))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z:
                    app.debug_menu = not app.debug_menu
                    
                    
                if app.debug_menu and app.state == GameState.PLAYING:
                    name = app.active_level.name if app.active_level else ""
                    if name:
                        if name not in app.lyric_offsets: app.lyric_offsets[name] = 0
                        if event.key == pygame.K_UP:
                            app.lyric_offsets[name] += 50
                        elif event.key == pygame.K_DOWN:
                            app.lyric_offsets[name] -= 50
                        elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                            save_lyric_offsets(app.lyric_offsets)
                            
                if event.key == pygame.K_ESCAPE:
                    if app.state == GameState.MENU: 
                        app.running = False
                    elif app.state in [GameState.PLAYING, GameState.VIDEO]:
                        # Pause!
                        app.state = GameState.PAUSED
                        app.pause_idx = 0
                        app.pause_scale = 0.0
                        app.pause_exiting = False
                        app.pause_hover_y = 160.0
                        app.pause_sel_lerp = [0.0] * len(app.pause_options)
                        app.pause_start_time = pygame.time.get_ticks()
                        pygame.mixer.music.pause()
                    elif app.state == GameState.PAUSED:
                        # Resume with shrink animation!
                        app.pause_exiting = True
                        app.pause_exit_action = 'resume'
                    elif app.state == GameState.LEVEL_SELECT:
                        app.state = GameState.MENU
                        pygame.mixer.music.stop()
                    else: 
                        app.state = GameState.MENU
                        pygame.mixer.music.stop()
                        if app.video_cap:
                            app.video_cap.release()
                            app.video_cap = None
                            app.video_fps = None
                elif app.state == GameState.WARNING:
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        app.state = GameState.MENU

                elif app.state == GameState.MENU:
                    if event.key in [pygame.K_w, pygame.K_UP]: app.menu_idx = (app.menu_idx - 1) % len(app.menu_options)
                    if event.key in [pygame.K_s, pygame.K_DOWN]: app.menu_idx = (app.menu_idx + 1) % len(app.menu_options)
                    
                    if event.key == pygame.K_z:
                        app.hq_processing = not getattr(app, 'hq_processing', False)
                        app.settings_options[2] = f"HQ Processing (Laptop): {'ON' if app.hq_processing else 'OFF'}"
                        if "Level Maker" not in app.menu_options:
                            app.menu_options.insert(1, "Level Maker")
                            app.menu_sel_lerp.insert(1, 0.0)
                            app.level_maker_anim = 1.0
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        opt = app.menu_options[app.menu_idx]
                        if opt == "Level Selection": 
                            app.state = GameState.LEVEL_SELECT
                            start_level_preview(app)
                        elif opt == "Level Maker":
                            app.state = GameState.LEVEL_MAKER
                            app.lm_state = 0
                            app.lm_query = ""
                            app.lm_status = "Type Song Name & Press Enter"
                        elif opt == "Skins": app.state = GameState.SKINS
                        elif opt == "Settings": app.state = GameState.SETTINGS
                        elif opt.startswith("Toggle Player 2"): app.toggle_p2()
                        elif opt == "Exit Game": app.running = False
                
                elif app.state == GameState.LEVEL_SELECT:
                    if getattr(app, 'delete_confirm', None) is not None:
                        if event.key == pygame.K_y:
                            name = app.delete_confirm
                            import shutil, os
                            base = os.path.splitext(SONGS[name]["json_path"])[0]
                            for ext in [".json", ".mp3", ".lrc", ".wav", ".m4a"]:
                                p = base + ext
                                if os.path.exists(p): os.remove(p)
                            del SONGS[name]
                            app.levels.remove(name)
                            app.selected_level_idx = max(0, min(app.selected_level_idx, len(app.levels)-1))
                            app.delete_confirm = None
                        elif event.key == pygame.K_n:
                            app.delete_confirm = None
                    else:
                        if event.key in [pygame.K_w, pygame.K_UP]: 
                            app.selected_level_idx = (app.selected_level_idx - 1) % len(app.levels)
                            app.target_scroll_y = -app.selected_level_idx * (90 + 20)
                            start_level_preview(app)
                        if event.key in [pygame.K_s, pygame.K_DOWN]: 
                            app.selected_level_idx = (app.selected_level_idx + 1) % len(app.levels)
                            app.target_scroll_y = -app.selected_level_idx * (90 + 20)
                            start_level_preview(app)
                        if event.key == pygame.K_z:
                            app.delete_mode = not getattr(app, 'delete_mode', False)
                        if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                            name = app.levels[app.selected_level_idx]
                            if getattr(app, 'delete_mode', False) and SONGS[name].get("class") == CustomLevel:
                                app.delete_confirm = name
                            else:
                                start_game(app)

                elif app.state == GameState.SKINS:
                    if event.key in [pygame.K_a, pygame.K_LEFT]: app.p1_shape = SHAPE_TYPES[(SHAPE_TYPES.index(app.p1_shape) - 1) % 4]
                    if event.key in [pygame.K_d, pygame.K_RIGHT]: app.p1_shape = SHAPE_TYPES[(SHAPE_TYPES.index(app.p1_shape) + 1) % 4]
                    if app.is_p2_enabled:
                        if event.key == pygame.K_q: app.p2_shape = SHAPE_TYPES[(SHAPE_TYPES.index(app.p2_shape) - 1) % 4]
                        if event.key == pygame.K_e: app.p2_shape = SHAPE_TYPES[(SHAPE_TYPES.index(app.p2_shape) + 1) % 4]
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]: app.state = GameState.MENU

                elif app.state == GameState.SETTINGS:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        app.settings_idx = (app.settings_idx - 1) % len(app.settings_options)
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        app.settings_idx = (app.settings_idx + 1) % len(app.settings_options)
                    
                    opt = app.settings_options[app.settings_idx]
                    if opt.startswith("Music Volume"):
                        if event.key in [pygame.K_a, pygame.K_LEFT]:
                            app.global_volume = max(0.0, app.global_volume - 0.1)
                            pygame.mixer.music.set_volume(app.global_volume)
                            app.settings_options[app.settings_idx] = f"Music Volume: {int(app.global_volume*100)}%"
                            app.pause_options[1] = f"Volume: {int(app.global_volume*100)}%"
                        if event.key in [pygame.K_d, pygame.K_RIGHT]:
                            app.global_volume = min(1.0, app.global_volume + 0.1)
                            pygame.mixer.music.set_volume(app.global_volume)
                            app.settings_options[app.settings_idx] = f"Music Volume: {int(app.global_volume*100)}%"
                            app.pause_options[1] = f"Volume: {int(app.global_volume*100)}%"
                            
                    elif opt.startswith("Text Glitches"):
                        if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT]:
                            app.text_glitches = not getattr(app, 'text_glitches', True)
                            app.settings_options[app.settings_idx] = f"Text Glitches: {'ON' if app.text_glitches else 'OFF'}"
                            
                    elif opt.startswith("HQ Processing"):
                        if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT]:
                            app.hq_processing = not getattr(app, 'hq_processing', False)
                            app.settings_options[app.settings_idx] = f"HQ Processing (Laptop): {'ON' if app.hq_processing else 'OFF'}"
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if opt == "Back":
                            app.state = GameState.MENU

                elif app.state == GameState.LEVEL_MAKER:
                    if app.lm_state == 0:
                        if event.key == pygame.K_ESCAPE:
                            app.state = GameState.MENU
                        elif event.key == pygame.K_BACKSPACE:
                            app.lm_query = app.lm_query[:-1]
                        elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER] and len(app.lm_query) > 0:
                            app.lm_state = 1
                            app.lm_status = f"Searching SpotDL for: {app.lm_query}..."
                            import threading
                            threading.Thread(target=run_level_maker, args=(app, app.lm_query), daemon=True).start()
                        elif event.unicode.isprintable():
                            app.lm_query += event.unicode

                elif app.state == GameState.LEVEL_CONFIG:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        app.config_idx = (getattr(app, 'config_idx', 0) - 1) % 5
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        app.config_idx = (getattr(app, 'config_idx', 0) + 1) % 5
                        
                    idx = getattr(app, 'config_idx', 0)
                    if event.key in [pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT]:
                        direction = -1 if event.key in [pygame.K_a, pygame.K_LEFT] else 1
                        if idx == 0: app.config_delay += 100 * direction
                        elif idx == 1:
                            diffs = ["Easy", "Normal", "Hard"]
                            app.config_diff = diffs[(diffs.index(getattr(app, 'config_diff', 'Normal')) + direction) % 3]
                        elif idx == 2:
                            app.config_boss = not getattr(app, 'config_boss', True)
                        elif idx == 3:
                            app.config_chroma = not getattr(app, 'config_chroma', True)
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if idx == 4:
                            app.lyric_offsets[app.config_level_name] = getattr(app, 'config_delay', 0)
                            save_lyric_offsets(app.lyric_offsets)
                            
                            song_data = SONGS.get(app.config_level_name, {})
                            if "json_path" in song_data and os.path.exists(song_data["json_path"]):
                                with open(song_data["json_path"], 'r') as f:
                                    data = json.load(f)
                                data["difficulty"] = getattr(app, 'config_diff', 'Normal')
                                data["boss_entity"] = getattr(app, 'config_boss', True)
                                data["chroma_colors"] = getattr(app, 'config_chroma', True)
                                with open(song_data["json_path"], 'w') as f:
                                    json.dump(data, f, indent=4)
                            
                            pygame.mixer.music.stop()
                            app.state = GameState.MENU
                            if hasattr(app, 'config_lyrics'): delattr(app, 'config_lyrics')

                elif app.state == GameState.PAUSED:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        app.pause_idx = (app.pause_idx - 1) % len(app.pause_options)
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        app.pause_idx = (app.pause_idx + 1) % len(app.pause_options)
                    
                    if app.pause_idx == 1:
                        if event.key in [pygame.K_a, pygame.K_LEFT]:
                            app.global_volume = max(0.0, app.global_volume - 0.1)
                            pygame.mixer.music.set_volume(app.global_volume)
                            app.settings_options[0] = f"Music Volume: {int(app.global_volume*100)}%"
                            app.pause_options[1] = f"Volume: {int(app.global_volume*100)}%"
                        if event.key in [pygame.K_d, pygame.K_RIGHT]:
                            app.global_volume = min(1.0, app.global_volume + 0.1)
                            pygame.mixer.music.set_volume(app.global_volume)
                            app.settings_options[0] = f"Music Volume: {int(app.global_volume*100)}%"
                            app.pause_options[1] = f"Volume: {int(app.global_volume*100)}%"
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if app.pause_idx == 0:
                            # Resume with shrink animation
                            app.pause_exiting = True
                            app.pause_exit_action = 'resume'
                        elif app.pause_idx == 2:
                            # Exit level with shrink animation
                            app.pause_exiting = True
                            app.pause_exit_action = 'exit'

                elif app.state in [GameState.GAMEOVER, GameState.COMPLETED]:
                    if event.key:
                        if pygame.time.get_ticks() - app.end_screen_timer > 3000:
                            app.state = GameState.MENU

        if app.state == GameState.PLAYING:
            app.active_level.update(dt)
            for p in app.players: p.update(dt, app)
            if app.health <= 0:
                app.state = GameState.GAMEOVER
                app.end_screen_timer = pygame.time.get_ticks()
                pygame.mixer.music.stop()
            elif not pygame.mixer.music.get_busy() and app.active_level.name != "CLOSE TO ME":
                app.state = GameState.COMPLETED
                app.end_screen_timer = pygame.time.get_ticks()

        elif app.state == GameState.VIDEO:
            if not app.video_fps:
                app.video_fps = app.video_cap.get(cv2.CAP_PROP_FPS)
                if not app.video_fps or math.isnan(app.video_fps): app.video_fps = 30.0
                app.video_start_time = pygame.time.get_ticks()
                app.current_frame = -1
                app.last_frame = None

            target_frame = int((pygame.time.get_ticks() - app.video_start_time) / 1000.0 * app.video_fps)
            ret = True
            while app.current_frame < target_frame and ret:
                ret, frame = app.video_cap.read()
                if ret:
                    app.current_frame += 1
                    app.last_frame = frame
            
            if not ret and app.current_frame < target_frame:
                app.state = GameState.MENU
                app.video_cap.release()
                app.video_cap = None
                app.video_fps = None
                pygame.mixer.music.stop()
            else:
                if app.last_frame is not None:
                    f = cv2.cvtColor(app.last_frame, cv2.COLOR_BGR2RGB)
                    f = np.rot90(f); f = np.flipud(f)
                    frame_surf = pygame.surfarray.make_surface(f)
                    frame_surf = pygame.transform.smoothscale(frame_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    screen.blit(frame_surf, (0, 0))
                pygame.display.flip()
                continue

        screen.fill(COLORS['bg'])
        offset_x = random.uniform(-app.shake_amount, app.shake_amount)
        offset_y = random.uniform(-app.shake_amount, app.shake_amount)
        app.shake_amount *= 0.9
        render_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        render_surf.fill(COLORS['bg'])

        if app.state == GameState.WARNING: UI.draw_warning(app)
        elif app.state == GameState.MENU: UI.draw_menu(app)
        elif app.state == GameState.LEVEL_SELECT: UI.draw_level_select(app)
        elif app.state == GameState.SKINS: UI.draw_skins(app)
        elif app.state == GameState.SETTINGS: UI.draw_settings(app)
        elif app.state == GameState.LEVEL_MAKER: UI.draw_level_maker(app)
        elif app.state == GameState.LEVEL_CONFIG: UI.draw_level_config(app)
        elif app.state == GameState.PLAYING:
            if hasattr(app.active_level, 'draw_background'):
                app.active_level.draw_background(render_surf)
            else:
                for x in range(0, SCREEN_WIDTH, 60): pygame.draw.line(render_surf, (20, 20, 20), (x, 0), (x, SCREEN_HEIGHT))
                for y in range(0, SCREEN_HEIGHT, 60): pygame.draw.line(render_surf, (20, 20, 20), (0, y), (SCREEN_WIDTH, y))
            
            if hasattr(app.active_level, 'draw_background_lyrics'):
                app.active_level.draw_background_lyrics(render_surf)
            for obs in app.active_level.obstacles: obs.draw(render_surf, app)
            app.active_level.draw_extra(render_surf)
            for p in app.players: p.draw(render_surf)
            pygame.draw.rect(render_surf, (50, 50, 50), (50, 50, 300, 20))
            pygame.draw.rect(render_surf, COLORS['pink'], (50, 50, (app.health/app.max_health)*300, 20))
            if app.players:
                p1 = app.players[0]
                pygame.draw.rect(render_surf, (30, 30, 50), (50, 75, 200, 10))
                pygame.draw.rect(render_surf, (0, 255, 200), (50, 75, (p1.dash_energy/p1.max_dash_energy)*200, 10))
            
            # Debug UI
            if app.debug_menu:
                name = app.active_level.name if app.active_level else ""
                offset = app.lyric_offsets.get(name, 0)
                dbg_surf = pygame.Surface((400, 150), pygame.SRCALPHA)
                pygame.draw.rect(dbg_surf, (10, 10, 10, 220), (0, 0, 400, 150), border_radius=10)
                pygame.draw.rect(dbg_surf, COLORS['blue'], (0, 0, 400, 150), 3, border_radius=10)
                f_sm = get_font(24)
                dbg_surf.blit(f_sm.render(f"DEBUG SYNC: {name}", True, COLORS['white']), (15, 15))
                dbg_surf.blit(f_sm.render(f"Offset: {offset} ms", True, COLORS['yellow']), (15, 50))
                dbg_surf.blit(f_sm.render("[UP/DOWN] Adjust Delay", True, (200, 200, 200)), (15, 85))
                dbg_surf.blit(f_sm.render("[ENTER] Save to Config", True, (200, 200, 200)), (15, 115))
                render_surf.blit(dbg_surf, (20, 80))
                
            screen.blit(render_surf, (offset_x, offset_y))
            if app.fade_alpha > 0:
                fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                fade.fill((0,0,0))
                fade.set_alpha(app.fade_alpha)
                screen.blit(fade, (0,0))
        
        elif app.state == GameState.PAUSED:
            if app.active_level:
                for x in range(0, SCREEN_WIDTH, 60): pygame.draw.line(render_surf, (20, 20, 20), (x, 0), (x, SCREEN_HEIGHT))
                for y in range(0, SCREEN_HEIGHT, 60): pygame.draw.line(render_surf, (20, 20, 20), (0, y), (SCREEN_WIDTH, y))
                if hasattr(app.active_level, 'draw_background_lyrics'):
                    app.active_level.draw_background_lyrics(render_surf)
                for obs in app.active_level.obstacles: obs.draw(render_surf, app)
                app.active_level.draw_extra(render_surf)
                for p in app.players: p.draw(render_surf)
                pygame.draw.rect(render_surf, (50, 50, 50), (50, 50, 300, 20))
                pygame.draw.rect(render_surf, COLORS['pink'], (50, 50, (app.health/app.max_health)*300, 20))
                screen.blit(render_surf, (0, 0))
            elif app.last_frame is not None:
                f = cv2.cvtColor(app.last_frame, cv2.COLOR_BGR2RGB)
                f = np.rot90(f); f = np.flipud(f)
                frame_surf = pygame.surfarray.make_surface(f)
                frame_surf = pygame.transform.smoothscale(frame_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                screen.blit(frame_surf, (0, 0))
            
            # Semi-transparent dark overlay fading
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay_alpha = int(180 * app.pause_scale)
            overlay.fill((0, 0, 0, overlay_alpha))
            screen.blit(overlay, (0, 0))
            
            # Scale animation logic
            if app.pause_exiting:
                app.pause_scale += (0.0 - app.pause_scale) * 0.22
                if app.pause_scale < 0.05:
                    if app.pause_exit_action == 'resume':
                        if not app.active_level and app.video_cap:
                            app.video_start_time += pygame.time.get_ticks() - app.pause_start_time
                        app.state = GameState.PLAYING if app.active_level else GameState.VIDEO
                        pygame.mixer.music.unpause()
                    elif app.pause_exit_action == 'exit':
                        app.state = GameState.MENU
                        pygame.mixer.music.stop()
                        if app.video_cap:
                            app.video_cap.release()
                            app.video_cap = None
                            app.video_fps = None
                    app.pause_exiting = False
            else:
                app.pause_scale += (1.0 - app.pause_scale) * 0.18

            w = int(600 * app.pause_scale)
            h = int(450 * app.pause_scale)
            if w > 10 and h > 10:
                box_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                # Glassmorphic base box
                pygame.draw.rect(box_surf, (12, 12, 22, 235), (0, 0, w, h), border_radius=20)
                # Neon glow pulse border
                glow_val = int(abs(math.sin(pygame.time.get_ticks() / 250)) * 60) + 195
                border_color = (0, glow_val, 255)
                pygame.draw.rect(box_surf, border_color, (0, 0, w, h), 4, border_radius=20)
                
                if app.pause_scale > 0.6:
                    # Floating/Pulsing Title
                    title_pulse = 1.0 + math.sin(pygame.time.get_ticks() * 0.005) * 0.05
                    title_f = get_font(50)
                    title_txt = title_f.render("PAUSED", True, COLORS['pink'])
                    float_title_y = 35 + math.sin(pygame.time.get_ticks() * 0.005) * 5
                    
                    title_w = int(title_txt.get_width() * title_pulse * app.pause_scale)
                    title_h = int(title_txt.get_height() * title_pulse * app.pause_scale)
                    if title_w > 0 and title_h > 0:
                        scaled_title = pygame.transform.smoothscale(title_txt, (title_w, title_h))
                        box_surf.blit(scaled_title, (w//2 - title_w//2, int(float_title_y)))
                    
                    # Smoothly update pointers
                    target_y = 160 + app.pause_idx * 90
                    app.pause_hover_y += (target_y - app.pause_hover_y) * 0.2
                    
                    for idx, opt in enumerate(app.pause_options):
                        is_sel = (idx == app.pause_idx)
                        target_lerp = 1.0 if is_sel else 0.0
                        app.pause_sel_lerp[idx] += (target_lerp - app.pause_sel_lerp[idx]) * 0.2
                        lerp = app.pause_sel_lerp[idx]
                        
                        # Smooth hover colors
                        sel_color = (0, 255, 150) if idx == 0 else (255, 235, 59) if idx == 1 else COLORS['enemy']
                        color = (
                            int(180 + (sel_color[0] - 180) * lerp),
                            int(180 + (sel_color[1] - 180) * lerp),
                            int(190 + (sel_color[2] - 190) * lerp)
                        )
                        
                        opt_f = get_font(35)
                        opt_txt = opt_f.render(opt, True, color)
                        y_pos = 160 + idx * 90
                        # Slide right when hovered
                        x_offset = int(lerp * 15)
                        box_surf.blit(opt_txt, (w//2 - opt_txt.get_width()//2 + x_offset, y_pos))
                        
                        if idx == 1:
                            # Draw volume slider track
                            track_y = y_pos + 45
                            track_w = 200
                            track_h = 6
                            pygame.draw.rect(box_surf, (40, 40, 50), (w//2 - track_w//2, track_y, track_w, track_h), border_radius=3)
                            
                            fill_w = int(track_w * app.global_volume)
                            pygame.draw.rect(box_surf, color, (w//2 - track_w//2, track_y, fill_w, track_h), border_radius=3)
                            pygame.draw.circle(box_surf, color, (w//2 - track_w//2 + fill_w, track_y + 3), 6)
                    
                    # Draw beautiful sliding neon dual arrow pointers
                    pulse_x = math.sin(pygame.time.get_ticks() * 0.015) * 5
                    pointer_color = (0, 255, 150) if app.pause_idx == 0 else (255, 235, 59) if app.pause_idx == 1 else COLORS['enemy']
                    
                    # Left pointer
                    pygame.draw.polygon(box_surf, pointer_color, [
                        (w//2 - 150 + int(pulse_x), int(app.pause_hover_y) + 10),
                        (w//2 - 135 + int(pulse_x), int(app.pause_hover_y) + 18),
                        (w//2 - 150 + int(pulse_x), int(app.pause_hover_y) + 26)
                    ])
                    # Right pointer
                    pygame.draw.polygon(box_surf, pointer_color, [
                        (w//2 + 150 - int(pulse_x), int(app.pause_hover_y) + 10),
                        (w//2 + 135 - int(pulse_x), int(app.pause_hover_y) + 18),
                        (w//2 + 150 - int(pulse_x), int(app.pause_hover_y) + 26)
                    ])
                
                rect = box_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
                screen.blit(box_surf, rect.topleft)

        elif app.state in [GameState.GAMEOVER, GameState.COMPLETED]:
            elapsed_end = pygame.time.get_ticks() - app.end_screen_timer
            if app.state == GameState.GAMEOVER:
                shake = max(0, 20 - elapsed_end // 50)
                ox = random.uniform(-shake, shake)
                oy = random.uniform(-shake, shake)
                scale = min(1.0, elapsed_end / 500)
                txt = font_xl.render("GAME OVER", True, COLORS['enemy'])
                if scale < 1.0 and scale > 0:
                    txt = pygame.transform.scale(txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2 + ox, SCREEN_HEIGHT//2 - 100 + oy))
            else:
                float_y = math.sin(elapsed_end * 0.003) * 20
                alpha = min(255, int((elapsed_end / 1000) * 255))
                txt = font_xl.render("LEVEL COMPLETED", True, COLORS['blue'])
                txt.set_alpha(alpha)
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2 - 100 + float_y))

            if elapsed_end > 3000:
                sub = font_medium.render("PRESS ANY KEY TO CONTINUE", True, COLORS['white'])
                if (elapsed_end // 500) % 2 == 0:
                    screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, SCREEN_HEIGHT//2 + 100))

        pygame.display.flip()

def start_level_preview(app):
    name = app.levels[app.selected_level_idx]
    if name == "Secret":
        pygame.mixer.music.stop()
        return
    load_music_safely(SONGS[name]["path"])
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)

def start_game(app):
    name = app.levels[app.selected_level_idx]
    if name == "Secret":
        app.state = GameState.VIDEO
        app.video_cap = cv2.VideoCapture(SONGS[name]["path"])
        app.video_fps = None
        if "audio_path" in SONGS[name]:
            load_music_safely(SONGS[name]["audio_path"])
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
        return
    app.state = GameState.PLAYING
    app.health = 100
    app.fade_alpha = 0
    app.players = [Player(1, app.p1_shape)]
    if app.is_p2_enabled: app.players.append(Player(2, app.p2_shape))
    level_classes = {"Cool Friends": CoolFriendsLevel, "Annihilate": AnnihilateLevel, "CLOSE TO ME": CloseToMeLevel, "Final Boss": FinalBossLevel, "Never Gonna Give You Up": NeverGonnaGiveYouUpLevel}
    if SONGS[name].get("class") == CustomLevel:
        app.active_level = CustomLevel(name, app, SONGS[name]["json_path"])
    else:
        app.active_level = level_classes[name](name, app)
    load_music_safely(SONGS[name]["path"])
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()

def run_level_maker(app, query):
    import subprocess, sys, os, glob, json, math, random, shutil
    custom_dir = os.path.join(os.path.dirname(__file__), "CustomLevels")
    os.makedirs(custom_dir, exist_ok=True)
    
    app.lm_progress = 0.1
    hq_on = getattr(app, 'hq_processing', False)
    try:
        pkgs = ["spotdl", "soundfile"]
        if hq_on: pkgs.extend(["librosa", "lazy_loader"])
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs + ["--upgrade", "--break-system-packages"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
        
    app.lm_status = "Downloading audio with SpotDL..."
    app.lm_progress = 0.2
    
    try:
        tmp_dir = os.path.join(custom_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        for f in glob.glob(os.path.join(tmp_dir, "*")): 
            if os.path.isfile(f): os.remove(f)
        
        cmd = [sys.executable, "-m", "spotdl", query, "--output", tmp_dir, "--generate-lrc"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        import re
        for line in process.stdout:
            if "Downloaded" in line: app.lm_progress = 0.6
        process.wait()
    except Exception as e:
        app.lm_status = f"Error downloading: {e}"
        app.lm_state = 2
        return

    audio_file = None
    lrc_file = None
    for f in glob.glob(os.path.join(tmp_dir, "*")):
        if f.endswith('.lrc'): lrc_file = f
        elif f.endswith('.mp3') or f.endswith('.m4a') or f.endswith('.wav'): audio_file = f
        
    if not audio_file:
        app.lm_status = "Error: SpotDL did not download an audio file."
        app.lm_state = 2
        return
        
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    base_name = "".join(c for c in base_name if c.isalnum() or c in " _-").strip()
    
    final_audio = os.path.join(custom_dir, f"{base_name}.mp3")
    final_lrc = os.path.join(custom_dir, f"{base_name}.lrc")
    cover_path = os.path.join(custom_dir, f"{base_name}.jpg")
    
    if os.path.exists(final_audio): os.remove(final_audio)
    if os.path.exists(final_lrc): os.remove(final_lrc)
    
    shutil.move(audio_file, final_audio)
    if lrc_file: shutil.move(lrc_file, final_lrc)

    # Fetch Album Cover
    app.lm_status = "Fetching Album Cover..."
    try:
        import urllib.request, urllib.parse
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(base_name)}&entity=song&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'JSAB-Arcade/1.0'})
        res = urllib.request.urlopen(req, timeout=5).read()
        data = json.loads(res)
        if data['resultCount'] > 0:
            artwork_url = data['results'][0].get('artworkUrl100', '')
            if artwork_url:
                artwork_url = artwork_url.replace("100x100bb", "600x600bb")
                urllib.request.urlretrieve(artwork_url, cover_path)
    except: pass

    import numpy as np
    
    def get_audio_array(audio_path):
        temp_wav = os.path.join(custom_dir, "temp_analysis.wav")
        try:
            subprocess.check_call(["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", "22050", temp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import wave
            with wave.open(temp_wav, 'rb') as wf:
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                arr = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            if os.path.exists(temp_wav): os.remove(temp_wav)
            return arr
        except Exception as e:
            print("Audio array extraction failed:", e)
            return np.zeros(100)

    def native_rms(audio_path):
        arr = get_audio_array(audio_path)
        sr = 22050
        chunk_size = int(sr * 0.1)
        rms_list = []
        max_r = 0.0001
        for i in range(0, len(arr), chunk_size):
            chunk = arr[i:i+chunk_size]
            if len(chunk) == 0: continue
            r = np.sqrt(np.mean(chunk**2))
            rms_list.append(r)
            if r > max_r: max_r = r
        return [float(r / max_r) for r in rms_list]

    def extract_peaks(rms_list, threshold=0.3):
        peaks = []
        for i in range(1, len(rms_list)-1):
            window = rms_list[max(0, i-5):min(len(rms_list), i+5)]
            local_avg = sum(window) / max(1, len(window))
            if rms_list[i] > max(threshold, local_avg * 1.5) and rms_list[i] > rms_list[i-1] and rms_list[i] > rms_list[i+1]:
                peaks.append(i * 100)
        return peaks

    app.lm_status = "Loading Audio Data..."
    app.lm_progress = 0.65
    
    bass_hits = []
    beat_times = []
    rms_curve = []
    chroma_curve = []
    song_bpm = 120

    if hq_on:
        app.lm_status = "HQ MODE: Librosa HD Analysis..."
        app.lm_progress = 0.70
        try:
            import librosa
            import numpy as np
            
            y, sr = librosa.load(final_audio, sr=22050)
            
            app.lm_status = "HQ MODE: Extracting Beats & Onsets..."
            app.lm_progress = 0.80
            
            D = librosa.stft(y)
            H, P = librosa.decompose.hpss(D)
            y_harm = librosa.istft(H)
            y_perc = librosa.istft(P)
            
            onset_env = librosa.onset.onset_strength(y=y_perc, sr=sr)
            onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units='time')
            beat_times = [int(t * 1000) for t in onsets]
            
            S = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            bass_idx = np.where((freqs >= 20) & (freqs <= 250))[0]
            bass_energy = np.mean(S[bass_idx, :], axis=0)
            bass_energy_norm = bass_energy / (np.max(bass_energy) + 1e-6)
            
            times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr)
            bass_hits = [int(times[i] * 1000) for i in range(len(times)) if bass_energy_norm[i] > 0.6]
            
            app.lm_status = "HQ MODE: Extracting Chroma & Energy..."
            app.lm_progress = 0.85
            
            rms_perc = librosa.feature.rms(y=y_perc)[0]
            rms_harm = librosa.feature.rms(y=y_harm)[0]
            rms_perc = rms_perc / (np.max(rms_perc) + 1e-6)
            rms_harm = rms_harm / (np.max(rms_harm) + 1e-6)
            
            chroma = librosa.feature.chroma_stft(y=y_harm, sr=sr)
            dom_pitch = np.argmax(chroma, axis=0)
            
            for i in range(len(rms_perc)):
                t = int(times[i] * 1000)
                d = float(rms_perc[i])
                o = float(rms_harm[i])
                b = float(bass_energy_norm[i]) if i < len(bass_energy_norm) else 0.0
                tot = (d + b + o) / 3.0
                rms_curve.append({"time": t, "energy": tot, "drums": d, "bass": b, "other": o})
                chroma_curve.append({"time": t, "pitch": int(dom_pitch[i])})
                
        except Exception as e:
            print("Librosa HQ failed:", e)
            hq_on = False
    if not hq_on:
        app.lm_status = "Native Mode: Fast Audio Analysis..."
        app.lm_progress = 0.75
        r_list = native_rms(final_audio)
        for i, r in enumerate(r_list):
            rms_curve.append({"time": i * 100, "energy": float(r)})
            
        app.lm_status = "Native Mode: Extracting Beats..."
        app.lm_progress = 0.85
        beat_times = extract_peaks(r_list, 0.3)
        bass_hits = [t for t in beat_times if r_list[int(t/100)] > 0.6]

    app.lm_status = "Generating Obstacles via Audio Maps..."
    app.lm_progress = 0.90

    timestamps = []
    if os.path.exists(final_lrc):
        lyrics_data = parse_lrc(final_lrc)
        timestamps = [item['time'] for item in lyrics_data]
    
    random.seed(base_name)
    level_data = {
        "name": base_name,
        "path": final_audio,
        "artist": "Custom Generator",
        "bpm": float(song_bpm),
        "rms_curve": rms_curve,
        "chroma_curve": chroma_curve,
        "obstacles": []
    }
    
    all_hits = sorted(list(set(timestamps + bass_hits + beat_times)))
    
    def get_rms(t):
        if not rms_curve: return 0.5
        idx = int(t / 100)
        if idx >= len(rms_curve): return rms_curve[-1]["energy"]
        return rms_curve[idx]["energy"]
        
    # 1. Beat Clustering Algorithm
    clusters = []
    current_cluster = []
    for t in all_hits:
        if not current_cluster:
            current_cluster.append(t)
        else:
            if t - current_cluster[-1] < 450: # Sequence threshold
                current_cluster.append(t)
            else:
                clusters.append(current_cluster)
                current_cluster = [t]
    if current_cluster:
        clusters.append(current_cluster)

    # 0. Song Structure Analysis
    window_size = 100
    section_map = []
    if rms_curve:
        for i in range(len(rms_curve)):
            start = max(0, i - window_size//2)
            end = min(len(rms_curve), i + window_size//2)
            avg = sum(x["energy"] for x in rms_curve[start:end]) / max(1, end-start)
            if avg < 0.3:
                sec_type = "intro"
            elif avg < 0.6:
                sec_type = "verse"
            else:
                sec_type = "chorus"
            section_map.append({"time": rms_curve[i]["time"], "section": sec_type})
        
    def get_section(t):
        idx = int(t / 100)
        if not section_map: return "verse"
        if idx >= len(section_map): return section_map[-1]["section"]
        return section_map[idx]["section"]

    # 2. Sequence Generation
    last_spawn_time = -5000
    last_heavy_pattern_time = -5000

    for cluster in clusters:
        seq_len = len(cluster)
        avg_energy = sum(get_rms(t) for t in cluster) / seq_len
        is_bass = any(t in bass_hits for t in cluster)
        
        d_energy = 0
        b_energy = 0
        o_energy = 0
        
        for t in cluster:
            idx = int(t / 100)
            if hq_on and rms_curve and idx < len(rms_curve) and "drums" in rms_curve[idx]:
                d_energy = max(d_energy, rms_curve[idx]["drums"])
                b_energy = max(b_energy, rms_curve[idx]["bass"])
                o_energy = max(o_energy, rms_curve[idx]["other"])
                
        # Determine Sequence Pattern
        sec = get_section(cluster[0])
        
        if not hq_on:
            if avg_energy < 0.15 and random.random() > 0.2:
                continue
            if sec == "intro": patterns = ["barrage", "spiral", "flower_burst"]
            elif sec == "verse": patterns = ["pincer", "homing_lasers", "double_helix"]
            else: patterns = ["crossfire", "pulse_ring", "wall_gap", "grid_lock", "border_crush", "sine_wave"]
            pattern_type = random.choice(patterns)
        else:
            if avg_energy < 0.05: continue
            if sec == "intro":
                pattern_type = random.choice(["spiral", "flower_burst", "double_helix", "snake"])
                avg_energy = max(d_energy, b_energy, o_energy)
            else:
                if b_energy > 0.5:
                    pattern_type = random.choice(["wall_gap", "laser_sweep", "crossfire", "grid_lock", "border_crush", "laser_grid"])
                    avg_energy = b_energy
                    is_bass = True
                elif d_energy > 0.4:
                    pattern_type = random.choice(["starburst", "barrage", "spiral", "pulse_ring", "flower_burst", "matrix_rain"])
                    avg_energy = d_energy
                    is_bass = False
                elif o_energy > 0.5:
                    pattern_type = random.choice(["sine_wave", "pincer", "homing_lasers", "double_helix", "chaser", "snake"])
                    avg_energy = o_energy
                    is_bass = False
                else:
                    if random.random() > 0.2: continue
                    pattern_type = "pincer"
                
        # 10X IMPROVEMENT: Combo Attacks!
        secondary_pattern = None
        super_pattern = None
        if avg_energy > 0.85 and len(cluster) > 2 and random.random() > 0.5:
            super_pattern = random.choice(["laser_cage", "core_explosion", "vortex"])
        elif avg_energy > 0.75 and random.random() > 0.3:
            if pattern_type in ["laser_sweep", "wall_gap", "grid_lock", "border_crush", "laser_grid"]:
                secondary_pattern = "matrix_rain"
            elif pattern_type in ["starburst", "spiral", "pulse_ring", "flower_burst", "vortex"]:
                secondary_pattern = "chaser"
            else:
                secondary_pattern = "pincer"
                
        # Throttle heavy patterns
        if pattern_type in ["wall_gap", "sine_wave", "crossfire", "laser_sweep", "grid_lock", "border_crush", "laser_grid", "vortex"]:
            if cluster[0] - last_heavy_pattern_time < 3000:
                pattern_type = random.choice(["pincer", "barrage", "spiral", "homing_lasers", "snake", "matrix_rain"])
                secondary_pattern = None
                super_pattern = None
            else:
                last_heavy_pattern_time = cluster[0]
                
        # Execute Pattern identically across the Cluster (Sequence)
        def spawn_pattern(ptype, t, i, energy):
            def add_obs(obs):
                # EXACT SYNC: Attack hits exactly at 't' by spawning early
                w_time = obs.get("warning_time", 500)
                obs["time"] = max(0, t - w_time)
                level_data["obstacles"].append(obs)

            def get_pitch(time_ms):
                if not chroma_curve: return random.randint(0, 11)
                idx = int(time_ms / 100)
                if idx >= len(chroma_curve): return chroma_curve[-1]["pitch"]
                return chroma_curve[idx]["pitch"]

            pitch = get_pitch(t)

            if ptype == "wall_gap":
                gap_x = random.randint(150, SCREEN_WIDTH - 150)
                for x in range(0, SCREEN_WIDTH, 120):
                    if abs(x - gap_x) > 150:
                        add_obs({
                            "type": "warning_line", "x": x, "y": -100,
                            "warning_time": 600, "speed": 10 + (energy * 8), "vx": 0, "shape": "rect", "size": 100
                        })
            elif ptype == "sine_wave":
                base_x = random.randint(200, SCREEN_WIDTH - 200)
                add_obs({
                    "type": "warning_line", "x": base_x + math.sin(i * 0.8) * 150, "y": -50,
                    "warning_time": 400, "speed": 10 + (energy * 4), "vx": 0, "shape": "circle", "size": 30
                })
            elif ptype == "crossfire":
                coords = [(SCREEN_WIDTH//2, -100, 0, 20), (SCREEN_WIDTH//2, SCREEN_HEIGHT+100, 0, -20), (-100, SCREEN_HEIGHT//2, 20, 0), (SCREEN_WIDTH+100, SCREEN_HEIGHT//2, -20, 0)]
                cx, cy, cvx, cvy = coords[i % 4]
                add_obs({
                    "type": "warning_line", "x": cx, "y": cy,
                    "warning_time": 800, "speed": abs(cvy) + abs(cvx), "vx": cvx, "shape": "rect", "size": 150
                })
            elif ptype == "starburst":
                count = max(6, int(12 * energy))
                for j in range(count):
                    angle = j * (math.pi / (count / 2.0))
                    speed = 12 * energy
                    vx = math.cos(angle) * max(6, speed)
                    vy = math.sin(angle) * max(6, speed)
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2,
                        "warning_time": 400, "speed": vy, "vx": vx, "shape": "triangle", "size": int(30 * energy)
                    })
            elif ptype == "laser_sweep":
                sweep_x = 100 + (SCREEN_WIDTH - 200) * (i / max(1, seq_len - 1)) if seq_len > 1 else SCREEN_WIDTH//2
                add_obs({
                    "type": "warning_line", "x": sweep_x, "y": -100,
                    "warning_time": 500, "speed": 35, "vx": 0, "shape": "rect", "size": 150
                })
            elif ptype == "barrage":
                count = max(3, int(6 * energy))
                for j in range(count):
                    add_obs({
                        "type": "warning_line", "x": random.randint(50, SCREEN_WIDTH-50), "y": -50,
                        "warning_time": 400, "speed": random.uniform(8, 15), "vx": random.uniform(-5, 5), "shape": "circle", "size": 40
                    })
            elif ptype == "spiral":
                count = max(4, int(8 * energy))
                offset = i * 0.5
                for j in range(count):
                    angle = j * (math.pi / (count / 2.0)) + offset
                    speed = 10 * energy
                    vx = math.cos(angle) * max(5, speed)
                    vy = math.sin(angle) * max(5, speed)
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2,
                        "warning_time": 500, "speed": vy, "vx": vx, "shape": "circle", "size": 30
                    })
            elif ptype == "pincer":
                speed = 10 + energy * 5
                add_obs({
                    "type": "warning_line", "x": -50, "y": random.randint(100, SCREEN_HEIGHT-100),
                    "warning_time": 600, "speed": 0, "vx": speed, "shape": "triangle", "size": 60
                })
                add_obs({
                    "type": "warning_line", "x": SCREEN_WIDTH+50, "y": random.randint(100, SCREEN_HEIGHT-100),
                    "warning_time": 600, "speed": 0, "vx": -speed, "shape": "triangle", "size": 60
                })
            elif ptype == "homing_lasers":
                add_obs({
                    "type": "warning_line", "x": "PLAYER_X", "y": -100,
                    "warning_time": 600, "speed": 25 + energy * 10, "vx": 0, "shape": "rect", "size": 80
                })
            elif ptype == "pulse_ring":
                count = max(8, int(16 * energy))
                for j in range(count):
                    angle = j * (2 * math.pi / count)
                    speed = 8 + energy * 4
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2,
                        "warning_time": 600, "speed": vy, "vx": vx, "shape": "circle", "size": 40
                    })
            elif ptype == "grid_lock":
                for x in [SCREEN_WIDTH//4, SCREEN_WIDTH*3//4]:
                    add_obs({
                        "type": "warning_line", "x": x, "y": -100,
                        "warning_time": 800, "speed": 20, "vx": 0, "shape": "rect", "size": 150
                    })
                for y in [SCREEN_HEIGHT//4, SCREEN_HEIGHT*3//4]:
                    add_obs({
                        "type": "warning_line", "x": -100, "y": y,
                        "warning_time": 800, "speed": 0, "vx": 20, "shape": "rect", "size": 150
                    })
            elif ptype == "laser_cage":
                for cx, cy, cvx, cvy in [(SCREEN_WIDTH//2, -50, 0, 10), (SCREEN_WIDTH//2, SCREEN_HEIGHT+50, 0, -10), (-50, SCREEN_HEIGHT//2, 10, 0), (SCREEN_WIDTH+50, SCREEN_HEIGHT//2, -10, 0)]:
                    add_obs({
                        "type": "warning_line", "x": cx, "y": cy,
                        "warning_time": 1000, "speed": abs(cvy)+abs(cvx), "vx": cvx, "shape": "rect", "size": 300,
                        "lifespan": 4000
                    })
            elif ptype == "core_explosion":
                add_obs({
                    "type": "warning_line", "x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2,
                    "warning_time": 1200, "speed": 0, "vx": 0, "shape": "circle", "size": 300,
                    "lifespan": 5000
                })
            elif ptype == "flower_burst":
                count = max(8, int(16 * energy))
                for j in range(count):
                    angle = j * (math.pi / (count / 2.0)) + (t/1000.0)
                    speed = 6 + 4 * energy
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2,
                        "warning_time": 500, "speed": math.sin(angle)*speed, "vx": math.cos(angle)*speed, "shape": "circle", "size": 40
                    })
            elif ptype == "double_helix":
                for j in range(2):
                    angle = (t / 500.0) + j * math.pi
                    speed = 12
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2, "y": -50,
                        "warning_time": 400, "speed": speed, "vx": math.cos(angle)*15, "shape": "circle", "size": 30
                    })
            elif ptype == "border_crush":
                add_obs({
                    "type": "warning_line", "x": 100, "y": -100,
                    "warning_time": 800, "speed": 15, "vx": 0, "shape": "rect", "size": 250
                })
                add_obs({
                    "type": "warning_line", "x": SCREEN_WIDTH-100, "y": -100,
                    "warning_time": 800, "speed": 15, "vx": 0, "shape": "rect", "size": 250
                })
            elif ptype == "matrix_rain":
                count = max(3, int(6 * energy))
                for j in range(count):
                    px = (pitch * 100 + random.randint(0, 200)) % SCREEN_WIDTH
                    add_obs({
                        "type": "warning_line", "x": px, "y": -50,
                        "warning_time": 400, "speed": 15 + energy * 10, "vx": 0, "shape": "rect", "size": int(20 + 20 * energy)
                    })
            elif ptype == "vortex":
                count = max(8, int(16 * energy))
                for j in range(count):
                    angle = j * (2 * math.pi / count) + (t / 500.0)
                    speed = 6 + energy * 4
                    add_obs({
                        "type": "warning_line", "x": SCREEN_WIDTH//2 + math.cos(angle)*400, "y": SCREEN_HEIGHT//2 + math.sin(angle)*400,
                        "warning_time": 800, "speed": -math.sin(angle)*speed, "vx": -math.cos(angle)*speed, "shape": "circle", "size": 50,
                        "lifespan": 4000
                    })
            elif ptype == "chaser":
                add_obs({
                    "type": "warning_line", "x": "PLAYER_X", "y": -100,
                    "warning_time": 600, "speed": 20 + energy * 10, "vx": 0, "shape": "triangle", "size": 60
                })
            elif ptype == "snake":
                base_x = 200 + (pitch * 100) % (SCREEN_WIDTH - 400)
                add_obs({
                    "type": "warning_line", "x": base_x + math.sin(i * 0.5) * 200, "y": -50,
                    "warning_time": 400, "speed": 12 + energy * 5, "vx": math.cos(i * 0.5) * 5, "shape": "circle", "size": 40
                })
            elif ptype == "laser_grid":
                add_obs({
                    "type": "warning_line", "x": (pitch * 150) % SCREEN_WIDTH, "y": -100,
                    "warning_time": 800, "speed": 25, "vx": 0, "shape": "rect", "size": 120
                })
                add_obs({
                    "type": "warning_line", "x": -100, "y": (pitch * 100) % SCREEN_HEIGHT,
                    "warning_time": 800, "speed": 0, "vx": 25, "shape": "rect", "size": 120
                })

        for i, t in enumerate(cluster):
            if t - last_spawn_time < 100: continue
            last_spawn_time = t
            energy = get_rms(t)
            spawn_pattern(pattern_type, t, i, energy)
            if secondary_pattern:
                spawn_pattern(secondary_pattern, t, i, energy * 0.7)
            if super_pattern and i == 0:
                spawn_pattern(super_pattern, t, i, energy)

    for _ in range(100):
        t = random.randint(0, max(timestamps + beat_times) if timestamps else 180000)
        energy = get_rms(t)
        if energy > 0.2:
            level_data["obstacles"].append({
                "time": t, "type": "warning_line", "x": random.randint(100, SCREEN_WIDTH-100), "y": -50,
                "warning_time": 1000, "speed": random.uniform(4, 9), "vx": random.uniform(-2, 2), "shape": random.choice(["circle", "rect"]), "size": random.randint(20, 50)
            })
        
    for obs in level_data["obstacles"]:
        obs["lifespan"] = 3000
        
    json_path = os.path.join(custom_dir, f"{base_name}.json")
    with open(json_path, 'w') as f:
        json.dump(level_data, f, indent=4)
        
    # Inject dynamically
    if base_name not in app.levels:
        app.levels.append(base_name)
        if hasattr(app, 'item_offsets'):
            app.item_offsets.append(0.0)
    SONGS[base_name] = {
        "path": final_audio,
        "artist": "Custom Generator",
        "surf": None,
        "class": CustomLevel,
        "json_path": json_path,
        "bpm": 120
    }
    if os.path.exists(cover_path):
        try:
            surf = pygame.image.load(cover_path).convert()
            SONGS[base_name]["surf"] = pygame.transform.scale(surf, (400, 400))
        except: pass
        
    app.lm_progress = 1.0
    app.config_level_name = base_name
    app.config_delay = 0
    app.config_idx = 0
    app.config_diff = "Normal"
    app.config_boss = True
    app.config_chroma = True
    app.state = GameState.LEVEL_CONFIG
    try:
        pygame.mixer.music.load(final_audio)
        start_pos = 0.0
        if timestamps:
            start_pos = max(0.0, (timestamps[0] - 2000) / 1000.0)
        pygame.mixer.music.play(start=start_pos)
        app.config_start_pos = int(start_pos * 1000)
        app.config_start_time = pygame.time.get_ticks()
    except: pass

if __name__ == "__main__":
    main()
    pygame.quit()
