import pygame
import random
import math
import sys
import os
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import numpy as np
except ImportError:
    np = None
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
# (Removed low-latency buffer constraint as it silently breaks WSL audio backends)
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
try:
    pygame.mixer.init()
except:
    pass
pygame.mouse.set_visible(False)

# Set resolution to 1280x720 to perfectly match the arcade cabinet display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
# Force full screen
try:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
except:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Just Shapes & Beats Remake")
clock = pygame.time.Clock()

# --- Constants & Colors ---
COLORS = {
    'bg': (5, 5, 5),
    'blue': (0, 183, 255),
    'yellow': (255, 235, 59),
    'orange': (255, 152, 0),
    'pink': (255, 40, 105),
    'enemy': (255, 57, 112),
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
    "Annihilate": {"path": os.path.join(MEDIA_PATH, "Annihilate.ogg"), "img": os.path.join(MEDIA_PATH, "Annihilate.jpeg"), "bpm": 140, "artist": "Destroid", "diff": 14},
    "CLOSE TO ME": {"path": os.path.join(MEDIA_PATH, "CLOSE TO ME.ogg"), "img": os.path.join(MEDIA_PATH, "Close To Me.jpg"), "bpm": 130, "artist": "Sabrepulse", "diff": 11},
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
import functools

@functools.lru_cache(maxsize=32)
def get_font(size, bold=True):
    try:
        return pygame.font.SysFont('Arial', size, bold=bold)
    except:
        return pygame.font.Font(None, size)

font_xl = get_font(120)
font_large = get_font(80)
font_medium = get_font(40)
font_small = get_font(24, False)

@functools.lru_cache(maxsize=128)
def get_rendered_text(text, size, color, bold=True):
    f = get_font(size, bold)
    return f.render(text, True, color)

@functools.lru_cache(maxsize=256)
def get_shape_surf(shape, size, color, alpha):
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
    return surf

@functools.lru_cache(maxsize=256)
def get_obs_surf(type, size, color, alpha):
    s = max(1, int(size))
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    if type == 'rect':
        pygame.draw.rect(surf, (*color, alpha), (0, 0, s, s))
    elif type == 'circle':
        pygame.draw.circle(surf, (*color, alpha), (s/2, s/2), s/2)
    elif type == 'triangle':
        pygame.draw.polygon(surf, (*color, alpha), [(s/2, 0), (s, s), (0, s)])
    return surf
# --- Global State ---
class GameState:
    SHATTER_DEATH = 9
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
    DIFFICULTY_SELECT = "difficulty_select"

class App:
    def __init__(self):
        self.state = GameState.WARNING
        self.is_p2_enabled = False
        self.p1_shape = 'square'
        self.p2_shape = 'triangle'
        self.selected_level_idx = 0
        self.levels = list(SONGS.keys())
        self.shake_amount = 0
        self.lives = 3
        self.score = 0
        self.continues = 3
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
        self.custom_bpms = {}
        
        try:
            avg_file = os.path.join(os.path.dirname(__file__), "CustomLevels", "average_gen_time.txt")
            if os.path.exists(avg_file):
                with open(avg_file, "r") as f:
                    times = [float(x) for x in f.read().split() if x]
                    if times: self.avg_gen_time = sum(times) / len(times)
        except: pass

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
        self.menu_options = ["Level Selection", "Skins", "Settings", "Level Maker", "Exit Game"]
        self.players = []
        self.menu_sel_lerp = [0.0] * len(self.menu_options)
        
        # Onscreen Keyboard state
        self.kb_layout = [
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '<'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '_', 'OK']
        ]
        self.kb_x = 0
        self.kb_y = 0
        self.kb_cooldown = 0
        
        # Audio / Settings state
        self.global_volume = 0.8
        pygame.mixer.music.set_volume(self.global_volume)
        
        # Pause state variables
        self.pause_idx = 0
        self.pause_options = ["Resume", "Restart Level", "Exit to Menu"]
        self.pause_scale = 0.0
        self.pause_exiting = False
        self.pause_exit_action = 'resume'
        self.pause_hover_y = 160.0
        self.pause_sel_lerp = [0.0] * len(self.pause_options)
        
        # Settings state variables
        self.text_glitches = True
        self.hq_processing = True
        self.settings_idx = 0
        self.settings_options = [f"Music Volume: {int(self.global_volume * 100)}%", f"Text Glitches: {'ON' if self.text_glitches else 'OFF'}", "Back"]

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
        self.dash_dist = 180
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.invuln_timer = 0
        self.is_dashing = False
        self.dash_target_x = 0
        self.dash_target_y = 0
        self.dash_start_x = 0
        self.dash_start_y = 0
        self.trail = []
        self.dash_particles = []
        self.reset()

    def reset(self):
        self.x = SCREEN_WIDTH // 2 + (50 if self.id == 2 else -50)
        self.y = SCREEN_HEIGHT // 2
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.invuln_timer = 0
        self.is_dashing = False
        self.trail = []
        self.dash_particles = []

    def update(self, dt, app):
        if self.dash_cooldown > 0: self.dash_cooldown -= dt
        if self.invuln_timer > 0: self.invuln_timer -= dt

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        
        shield_key = False
        if self.id == 1:
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1
            dash_key = keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT]
            shield_key = keys[pygame.K_q] or keys[pygame.K_e]
            
            if hasattr(app, 'joysticks') and len(app.joysticks) > 0:
                j = app.joysticks[0]
                if j.get_numaxes() >= 2:
                    if j.get_axis(0) < -0.3: dx -= 1
                    elif j.get_axis(0) > 0.3: dx += 1
                    if j.get_axis(1) < -0.3: dy -= 1
                    elif j.get_axis(1) > 0.3: dy += 1
                if j.get_numhats() > 0:
                    hx, hy = j.get_hat(0)
                    if hx < -0.5: dx -= 1
                    elif hx > 0.5: dx += 1
                    if hy < -0.5: dy += 1
                    elif hy > 0.5: dy -= 1
                if j.get_button(0) or j.get_button(1) or j.get_button(9): dash_key = True
                if j.get_button(2) or j.get_button(3): shield_key = True
        else:
            if keys[pygame.K_UP]: dy -= 1
            if keys[pygame.K_DOWN]: dy += 1
            if keys[pygame.K_LEFT]: dx -= 1
            if keys[pygame.K_RIGHT]: dx += 1
            dash_key = keys[pygame.K_RETURN] or keys[pygame.K_RSHIFT]
            shield_key = keys[pygame.K_RCTRL] or keys[pygame.K_RALT]
            
            if hasattr(app, 'joysticks') and len(app.joysticks) > 1:
                j = app.joysticks[1]
                if j.get_numaxes() >= 2:
                    if j.get_axis(0) < -0.3: dx -= 1
                    elif j.get_axis(0) > 0.3: dx += 1
                    if j.get_axis(1) < -0.3: dy -= 1
                    elif j.get_axis(1) > 0.3: dy += 1
                if j.get_button(0) or j.get_button(1) or j.get_button(9): dash_key = True
                if j.get_button(2) or j.get_button(3): shield_key = True



        if self.is_dashing:
            self.dash_timer -= dt
            
            # Smooth cubic ease-out
            t = max(0, min(1, 1.0 - (self.dash_timer / 200.0)))
            ease = 1 - (1 - t) ** 3
            
            self.x = self.dash_start_x + (self.dash_target_x - self.dash_start_x) * ease
            self.y = self.dash_start_y + (self.dash_target_y - self.dash_start_y) * ease
            
            dx = self.dash_target_x - self.dash_start_x
            dy = self.dash_target_y - self.dash_start_y
            angle = math.degrees(math.atan2(-dy, dx))
            # Trail effect (shrinking comet tail instead of particles)
            self.trail.append({'x': self.x, 'y': self.y, 'alpha': 200, 'angle': angle, 'size': self.size})
            
            if self.dash_timer <= 0: 
                self.is_dashing = False
                self.x = self.dash_target_x
                self.y = self.dash_target_y
        else:
            if dx != 0 or dy != 0:
                mag = math.sqrt(dx*dx + dy*dy)
                self.x += (dx / mag) * self.speed
                self.y += (dy / mag) * self.speed
            
            if dash_key and self.dash_cooldown <= 0:
                self.start_dash(dx, dy, app)

        self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
        self.y = max(self.size, min(SCREEN_HEIGHT - self.size, self.y))

        for t in self.trail: t['alpha'] -= 15
        self.trail = [t for t in self.trail if t['alpha'] > 0]
        
        for p in self.dash_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 15
        self.dash_particles = [p for p in self.dash_particles if p['life'] > 0]

    def start_dash(self, dx, dy, app):
        if dx == 0 and dy == 0:
            dx = -1 if self.id == 1 else 1
        mag = math.sqrt(dx*dx + dy*dy)
        
        self.dash_start_x = self.x
        self.dash_start_y = self.y
        self.dash_target_x = self.x + (dx/mag) * self.dash_dist
        self.dash_target_y = self.y + (dy/mag) * self.dash_dist
        
        # Clamp target
        self.dash_target_x = max(self.size, min(SCREEN_WIDTH - self.size, self.dash_target_x))
        self.dash_target_y = max(self.size, min(SCREEN_HEIGHT - self.size, self.dash_target_y))
        
        self.is_dashing = True
        self.dash_timer = 150
        self.dash_cooldown = 220
        self.invuln_timer = 300
        # Remove dash burst particles
        app.shake_amount = 12

    def draw(self, surface):
        color = SHAPE_COLORS[self.shape]
        
        # Draw Dash Particles (Stretching Sparks)
        for p in self.dash_particles:
            alpha = max(0, min(255, int(p['life'])))
            c = p.get('color', color)
        for t in self.trail:
            sz = max(1, int(t.get('size', self.size) * (t['alpha']/200.0)))
            p_surf = get_shape_surf(self.shape, sz, SHAPE_COLORS[self.shape], int(t['alpha']))
            if t['angle'] != 0:
                p_surf = pygame.transform.rotate(p_surf, t['angle'])
            r = p_surf.get_rect(center=(t['x'], t['y']))
            surface.blit(p_surf, r.topleft)
            
        if self.invuln_timer > 0 and (pygame.time.get_ticks() // 50) % 2 == 0:
            pass
        else:
            if self.is_dashing:
                dx = self.dash_target_x - self.dash_start_x
                dy = self.dash_target_y - self.dash_start_y
                angle = math.degrees(math.atan2(-dy, dx))
                surf = get_shape_surf(self.shape, self.size, color, 255)
                surf = pygame.transform.scale(surf, (int(self.size*2), int(self.size*0.3)))
                surf = pygame.transform.rotate(surf, angle)
                surface.blit(surf, (self.x - surf.get_width()//2, self.y - surf.get_height()//2))
            else:
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
        
        # Offscreen culling
        s = int(self.size)
        if self.x < -s or self.x > SCREEN_WIDTH + s or self.y < -s or self.y > SCREEN_HEIGHT + s:
            return

        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
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
            beat_flash = max(0, 1.0 - (level_elapsed - last_beat) / 200.0)
            pulse = self.size * 0.08 * beat_flash
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

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        
        s = int(self.size)
        dist = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
        hit_radius = player.size * 0.4
        
        if self.type == 'circle':
            return dist < (s * 0.45) + hit_radius
        elif self.type in ['rect', 'square', 'octagon'] and self.rotation % 360 == 0:
            return (self.x - s/2 < player.x + hit_radius and 
                    self.x + s/2 > player.x - hit_radius and 
                    self.y - s/2 < player.y + hit_radius and 
                    self.y + s/2 > player.y - hit_radius)
        else:
            return dist < (s * 0.40) + hit_radius

class FullScreenLaser(Obstacle):
    def __init__(self, axis, position, warning_ms):
        super().__init__(0, 0, 0, 0, 0, 'laser', warning_ms, 1, 255, 0, 400 + warning_ms)
        self.axis = axis
        self.position = position
        self.active_duration = 400
        self.fade_duration = 200
        self.warning_ms = warning_ms
        if self.axis == 'h':
            self.rect_y = position * SCREEN_HEIGHT
        else:
            self.rect_x = position * SCREEN_WIDTH

    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning_ms:
            self.active = True
        if self.lifespan is not None:
            self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        color = COLORS['enemy']
        last_beat = app.active_level.last_beat_time if app.active_level else 0
        beat_flash = max(0, 1.0 - (level_elapsed - last_beat) / 200.0)
        pulse = 40 * 0.08 * beat_flash
        s = int(40 + pulse)
        
        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
            warn_color = (*color, alpha)
            if self.axis == 'h':
                pygame.draw.line(surface, warn_color, (0, self.rect_y), (SCREEN_WIDTH, self.rect_y), 2)
            else:
                pygame.draw.line(surface, warn_color, (self.rect_x, 0), (self.rect_x, SCREEN_HEIGHT), 2)
        else:
            time_active = self.timer - self.warning_ms
            if time_active > self.active_duration:
                fade_alpha = max(0, 255 - int(255 * (time_active - self.active_duration) / self.fade_duration))
                draw_color = (*color, fade_alpha)
                temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                if self.axis == 'h':
                    pygame.draw.rect(temp_surf, draw_color, (0, self.rect_y - s/2, SCREEN_WIDTH, s))
                else:
                    pygame.draw.rect(temp_surf, draw_color, (self.rect_x - s/2, 0, s, SCREEN_HEIGHT))
                surface.blit(temp_surf, (0, 0))
            else:
                if self.axis == 'h':
                    pygame.draw.rect(surface, color, (0, self.rect_y - s/2, SCREEN_WIDTH, s))
                else:
                    pygame.draw.rect(surface, color, (self.rect_x - s/2, 0, s, SCREEN_HEIGHT))

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        time_active = self.timer - self.warning_ms
        if time_active > self.active_duration: return False
        
        hit_radius = player.size * 0.4
        s = 40
        if self.axis == 'h':
            return abs(player.y - self.rect_y) < (s/2 + hit_radius)
        else:
            return abs(player.x - self.rect_x) < (s/2 + hit_radius)

class WallSlam(Obstacle):
    def __init__(self, side, thickness_frac, warning_ms):
        super().__init__(0, 0, 0, 0, 0, 'wall', warning_ms, 1, 255, 0, 600 + warning_ms)
        self.side = side
        self.thickness_frac = thickness_frac
        self.hold_ms = 400
        self.warning_ms = warning_ms
        if side == 'top': self.rect = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT * thickness_frac)
        elif side == 'bottom': self.rect = (0, SCREEN_HEIGHT*(1-thickness_frac), SCREEN_WIDTH, SCREEN_HEIGHT * thickness_frac)
        elif side == 'left': self.rect = (0, 0, SCREEN_WIDTH * thickness_frac, SCREEN_HEIGHT)
        elif side == 'right': self.rect = (SCREEN_WIDTH*(1-thickness_frac), 0, SCREEN_WIDTH * thickness_frac, SCREEN_HEIGHT)
        
    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning_ms:
            self.active = True
        if self.lifespan is not None:
            self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        color = COLORS['enemy']
        
        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
            warn_color = (*color, alpha)
            if self.side == 'top': pygame.draw.line(surface, warn_color, (0, self.rect[3]), (SCREEN_WIDTH, self.rect[3]), 2)
            elif self.side == 'bottom': pygame.draw.line(surface, warn_color, (0, self.rect[1]), (SCREEN_WIDTH, self.rect[1]), 2)
            elif self.side == 'left': pygame.draw.line(surface, warn_color, (self.rect[2], 0), (self.rect[2], SCREEN_HEIGHT), 2)
            elif self.side == 'right': pygame.draw.line(surface, warn_color, (self.rect[0], 0), (self.rect[0], SCREEN_HEIGHT), 2)
        else:
            time_active = self.timer - self.warning_ms
            slide_in = min(1.0, time_active / 150.0)
            slide_out = min(1.0, max(0.0, (time_active - self.hold_ms) / 200.0))
            if slide_out >= 1.0: return
            
            x, y, w, h = self.rect
            if self.side == 'top': h *= (slide_in - slide_out)
            elif self.side == 'bottom': 
                new_h = h * (slide_in - slide_out)
                y = SCREEN_HEIGHT - new_h
                h = new_h
            elif self.side == 'left': w *= (slide_in - slide_out)
            elif self.side == 'right':
                new_w = w * (slide_in - slide_out)
                x = SCREEN_WIDTH - new_w
                w = new_w
            
            pygame.draw.rect(surface, color, (x, y, w, h))

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        time_active = self.timer - self.warning_ms
        if time_active > self.hold_ms: return False
        
        x, y, w, h = self.rect
        hit_radius = player.size * 0.4
        return (x < player.x + hit_radius and 
                x + w > player.x - hit_radius and 
                y < player.y + hit_radius and 
                y + h > player.y - hit_radius)

class ParticleBurst(Obstacle):
    def __init__(self, cx, cy, count, speed, warning_ms):
        super().__init__(cx, cy, 0, 0, 0, 'burst', warning_ms, 1, 255, 0, 2000 + warning_ms)
        self.cx = cx
        self.cy = cy
        self.count = count
        self.speed = speed
        self.warning_ms = warning_ms
        self.particles = []
        for i in range(count):
            angle = (math.pi * 2 * i / count) + random.uniform(-0.1, 0.1)
            self.particles.append({'x': cx, 'y': cy, 'vx': math.cos(angle)*speed, 'vy': math.sin(angle)*speed})

    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning_ms:
            self.active = True
            for p in self.particles:
                p['x'] += p['vx'] * (dt / 16.0)
                p['y'] += p['vy'] * (dt / 16.0)
        if self.lifespan is not None:
            self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        color = COLORS['enemy']
        
        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
            warn_color = (*color, alpha)
            pulse_rad = 10 + int(abs(math.sin(level_elapsed / 100)) * 5)
            pygame.draw.circle(surface, warn_color, (self.cx, self.cy), pulse_rad, 2)
        else:
            last_beat = app.active_level.last_beat_time if app.active_level else 0
            beat_flash = max(0, 1.0 - (level_elapsed - last_beat) / 200.0)
            pulse = 16 * 0.08 * beat_flash
            r = int(8 + pulse)
            for p in self.particles:
                if 0 <= p['x'] <= SCREEN_WIDTH and 0 <= p['y'] <= SCREEN_HEIGHT:
                    pygame.draw.circle(surface, color, (int(p['x']), int(p['y'])), r)

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        hit_radius = player.size * 0.4
        for p in self.particles:
            dist = math.sqrt((p['x'] - player.x)**2 + (p['y'] - player.y)**2)
            if dist < 8 + hit_radius: return True
        return False

class PillarDrop(Obstacle):
    def __init__(self, x_positions, warning_ms):
        super().__init__(0, 0, 0, 0, 0, 'pillar', warning_ms, 1, 255, 0, 2000 + warning_ms)
        self.x_positions = x_positions
        self.warning_ms = warning_ms
        self.pillar_width = 30
        self.speed = 20

    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning_ms:
            self.active = True
        if self.lifespan is not None:
            self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        color = COLORS['enemy']
        last_beat = app.active_level.last_beat_time if app.active_level else 0
        beat_flash = max(0, 1.0 - (level_elapsed - last_beat) / 200.0)
        pulse = self.pillar_width * 0.08 * beat_flash
        w = int(self.pillar_width + pulse)

        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
            warn_color = (*color, alpha)
            for px in self.x_positions:
                pygame.draw.line(surface, warn_color, (px, 0), (px, SCREEN_HEIGHT), 2)
        else:
            time_active = self.timer - self.warning_ms
            y_head = time_active * self.speed * 0.06
            for px in self.x_positions:
                pygame.draw.rect(surface, color, (px - w/2, 0, w, y_head))

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        time_active = self.timer - self.warning_ms
        y_head = time_active * self.speed * 0.06
        hit_radius = player.size * 0.4
        
        for px in self.x_positions:
            if player.y - hit_radius < y_head:
                if abs(player.x - px) < (self.pillar_width/2 + hit_radius):
                    return True
        return False

class ShockwaveRing(Obstacle):
    def __init__(self, cx, cy, max_radius, speed, thickness, warning_ms):
        super().__init__(cx, cy, 0, 0, 0, 'shockwave', warning_ms, 1, 255, 0, 3000 + warning_ms)
        self.cx = cx
        self.cy = cy
        self.max_radius = max_radius
        self.speed = speed
        self.thickness = thickness
        self.warning_ms = warning_ms
        self.current_radius = 0

    def update(self, dt, app=None):
        self.timer += dt
        if self.timer >= self.warning_ms:
            self.active = True
            self.current_radius += self.speed * (dt / 16.0)
            if self.current_radius > self.max_radius:
                self.lifespan = 0
        if self.lifespan is not None:
            self.lifespan -= dt

    def draw(self, surface, app):
        level_elapsed = app.active_level.elapsed_ms if app.active_level else pygame.time.get_ticks()
        color = COLORS['enemy']
        if not self.active:
            alpha = int(abs(math.sin(level_elapsed / 100)) * 50) + 30
            warn_color = (*color, alpha)
            pulse_rad = 5 + int(abs(math.sin(level_elapsed / 100)) * 3)
            pygame.draw.circle(surface, warn_color, (self.cx, self.cy), pulse_rad)
        else:
            if self.current_radius > 0:
                pygame.draw.circle(surface, color, (self.cx, self.cy), int(self.current_radius), self.thickness)

    def check_collision(self, player, app):
        if not self.active or player.invuln_timer > 0 or self.damage == 0: return False
        dist = math.sqrt((self.cx - player.x)**2 + (self.cy - player.y)**2)
        hit_radius = player.size * 0.4
        return abs(dist - self.current_radius) < (self.thickness/2 + hit_radius)

# --- Levels ---
class Level:
    def __init__(self, name, app):
        self.name = name
        self.app = app
        self.obstacles = []
        self.parallax_stars = [{'x': random.randint(0, SCREEN_WIDTH), 'y': random.randint(0, SCREEN_HEIGHT), 'size': random.uniform(1, 4), 'speed': random.uniform(20, 80), 'color': (random.randint(150, 255), random.randint(150, 255), 255)} for _ in range(50)]
        self.parallax_grids = [y for y in range(0, SCREEN_HEIGHT, 100)]
        self.elapsed_ms = 0
        self.last_beat_time = 0
        self.checkpoints = []
        self.last_checkpoint_ms = 0
        self.checkpoint_lives = 3
        self.show_checkpoint_text_timer = 0
        if name in SONGS:
            self.config = SONGS[name]
        else:
            import sys
            main_mod = sys.modules.get('__main__')
            if main_mod and hasattr(main_mod, 'SONGS') and name in main_mod.SONGS:
                self.config = main_mod.SONGS[name]
            else:
                self.config = {}
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
        
        if self.show_checkpoint_text_timer > 0:
            self.show_checkpoint_text_timer -= dt

        for cp in self.checkpoints:
            if self.elapsed_ms >= cp and self.last_checkpoint_ms < cp:
                self.last_checkpoint_ms = cp
                self.checkpoint_lives = self.app.lives
                self.show_checkpoint_text_timer = 1500

        # Audio Sync Fix: Snap to actual music playback position to prevent drift
        if pygame.mixer.music.get_busy():
            pos = pygame.mixer.music.get_pos()
            if not hasattr(self, 'last_mixer_pos'): self.last_mixer_pos = -1
            if pos > 0 and pos != self.last_mixer_pos:
                if abs(self.elapsed_ms - pos) > 100:
                    self.elapsed_ms = pos
                self.last_mixer_pos = pos
                
        self.spawn_patterns(self.elapsed_ms)
        
        # Performance optimization for Raspberry Pi 400
        if len(self.obstacles) > 80:
            self.obstacles = self.obstacles[-80:]
            
        alive_obstacles = []
        for obs in self.obstacles:
            obs.update(dt, self.app)
            
            if obs.x < -1000 or obs.x > SCREEN_WIDTH + 1000 or obs.y < -1000 or obs.y > SCREEN_HEIGHT + 1000:
                continue
                
            if getattr(obs, 'lifespan', None) is not None and obs.lifespan <= 0:
                continue
                
            collided = False
            if self.app.players:
                for p in self.app.players:
                    if obs.check_collision(p, self.app):
                        self.app.lives -= 1
                        self.app.shake_amount = 15
                        p.invuln_timer = 1500
                        if self.app.lives <= 0:
                            if self.last_checkpoint_ms > 0 and self.app.continues > 0:
                                self.app.lives = self.checkpoint_lives
                                self.app.continues -= 1
                                self.elapsed_ms = self.last_checkpoint_ms
                                pygame.mixer.music.play(start=self.elapsed_ms / 1000.0)
                                self.obstacles.clear()
                                for pl in self.app.players: pl.reset()
                                return
                            else:
                                self.app.shatter_player = p
                                self.app.shatter_timer = 0
                                self.app.shatter_particles = []
                                for i in range(150):
                                    angle = random.uniform(0, math.pi*2)
                                    speed = random.uniform(5, 35)
                                    self.app.shatter_particles.append({
                                        'x': p.x, 'y': p.y,
                                        'vx': math.cos(angle)*speed,
                                        'vy': math.sin(angle)*speed,
                                        'size': random.uniform(5, 25),
                                        'rot': random.uniform(0, 360),
                                        'rot_speed': random.uniform(-30, 30),
                                        'color': SHAPE_COLORS[p.shape],
                                        'shape': p.shape
                                    })
                        collided = True
                        break
            
            if not collided:
                alive_obstacles.append(obs)
                
        self.obstacles = alive_obstacles

    def spawn_patterns(self, elapsed):
        sync_offset = self.app.lyric_offsets.get(self.name, 0)
        true_elapsed = self.elapsed_ms - sync_offset
        
        if hasattr(self, 'beat_times'):
            if not hasattr(self, 'beat_idx'): self.beat_idx = 0
            while self.beat_idx < len(self.beat_times) and true_elapsed >= self.beat_times[self.beat_idx]:
                self.app.shake_amount = 4
                self.beat_idx += 1
                self.app.score += 10
                self.on_beat(elapsed)
        else:
            if self.elapsed_ms - self.last_beat_time > self.app.beat_interval:
                self.last_beat_time = self.elapsed_ms
                self.app.shake_amount = 4
                self.app.score += 10
                self.on_beat(elapsed)

    def on_beat(self, elapsed): pass

    def draw_extra(self, surface): 
        if self.show_checkpoint_text_timer > 0:
            alpha = int(min(255, self.show_checkpoint_text_timer / 1500 * 255))
            txt = get_rendered_text("CHECKPOINT", 80, (255, 255, 255))
            txt.set_alpha(alpha)
            r = txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
            surface.blit(txt, r)

    def draw_background(self, surface):
        surface.fill((0, 0, 0))
        if not hasattr(self, '_bg_surface'):
            self._bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self._bg_surface.fill((0, 0, 0))
            for x in range(0, SCREEN_WIDTH, 80):
                pygame.draw.line(self._bg_surface, (20, 8, 35), (x, 0), (x, SCREEN_HEIGHT), 1)
            for y in range(0, SCREEN_HEIGHT, 80):
                pygame.draw.line(self._bg_surface, (20, 8, 35), (0, y), (SCREEN_WIDTH, y), 1)
            self._flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self._flash_surface.fill((0, 0, 0))
            self._flash_surface.set_colorkey((0, 0, 0))
            for x in range(0, SCREEN_WIDTH, 80):
                pygame.draw.line(self._flash_surface, (60, 20, 80), (x, 0), (x, SCREEN_HEIGHT), 1)
            for y in range(0, SCREEN_HEIGHT, 80):
                pygame.draw.line(self._flash_surface, (60, 20, 80), (0, y), (SCREEN_WIDTH, y), 1)
        
        beat_flash = max(0, 1.0 - (self.elapsed_ms - self.last_beat_time) / 200.0)
        surface.blit(self._bg_surface, (0, 0))
        if beat_flash > 0:
            self._flash_surface.set_alpha(int(255 * beat_flash))
            surface.blit(self._flash_surface, (0, 0))

    def draw_background_lyrics(self, surface):
        if not self.app.lyric_offsets.get(f"{self.name}_lyrics", True):
            return
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
                    
                # Use cached text rendering to avoid TTF lag
                font_size = 70
                tmp_surf = get_rendered_text(lyric_text, font_size, (255, 255, 255), bold=True)
                
                base_scale = 1.0
                if tmp_surf.get_width() > SCREEN_WIDTH - 100:
                    base_scale = (SCREEN_WIDTH - 100) / tmp_surf.get_width()
                
                base_x = SCREEN_WIDTH // 2
                base_y = SCREEN_HEIGHT // 2  # Moved to the middle of the screen
                
                anim_type = 0
                # Animate based on song energy
                if energy < 0.3: anim_type = 0
                elif energy < 0.6: anim_type = 1
                elif energy < 0.8: anim_type = 2
                else: anim_type = 3
                
                t = time_since_lyric / max(1, duration) # 0.0 to 1.0
                
                scale_x = base_scale * beat_pulse
                scale_y = base_scale * beat_pulse
                rot_angle = 0
                
                if anim_type == 0: # Calm Pulse
                    pulse_t = (time_since_lyric % 1000) / 1000.0
                    scale_x *= 1.0 + math.sin(pulse_t * math.pi) * 0.02
                    scale_y *= 1.0 + math.cos(pulse_t * math.pi) * 0.02
                elif anim_type == 1: # Verse Stretch
                    pulse_t = (time_since_lyric % 500) / 500.0
                    scale_x *= 1.0 + math.sin(pulse_t * math.pi) * 0.05
                    scale_y *= 1.0 + math.cos(pulse_t * math.pi) * 0.05
                elif anim_type == 2: # Pre-Chorus Tense (glitchy)
                    if time_since_lyric % 150 < 75:
                        glitch_active = True
                        base_x += random.randint(-5, 5)
                        base_y += random.randint(-5, 5)
                elif anim_type == 3: # Chorus Slam
                    if t < 0.05:
                        scale_x *= 1.5 - (t / 0.05) * 0.5
                        scale_y *= 1.5 - (t / 0.05) * 0.5
                    else:
                        pulse_t = (time_since_lyric % 250) / 250.0
                        scale_x *= 1.0 + math.sin(pulse_t * math.pi) * 0.1
                        scale_y *= 1.0 + math.cos(pulse_t * math.pi) * 0.1
                
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
        self.obstacles.append(ParticleBurst(center_x, center_y, count, 15 + 10*level_progress, 100))
        self.obstacles.append(ShockwaveRing(center_x, center_y, 2000, 20, 20, 100))

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
                        self.app.lives -= 1 # spikey damage
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
                self.obstacles.append(PillarDrop([random.randint(100, SCREEN_WIDTH//2), random.randint(SCREEN_WIDTH//2, SCREEN_WIDTH-100)], 300))
            elif mode == 1:
                self.obstacles.append(ShockwaveRing(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 1000, 15, 20, 250))
            elif mode == 2:
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//3, SCREEN_HEIGHT//2, 15, 11, 250))
                self.obstacles.append(ParticleBurst((2*SCREEN_WIDTH)//3, SCREEN_HEIGHT//2, 15, 11, 250))
        elif 186000 <= self.elapsed_ms < 199000:
            # Medium beat spawns during the heavy flicker sequence
            if self.attack_tick % 3 == 0:
                self.obstacles.append(WallSlam('left', 0.2, 150))
        elif 199000 <= self.elapsed_ms < 290000:
            cycle_sec = (sec - 199.0) % 15.0
            if cycle_sec >= 11.0:
                return # Silence rest period between events: let active obstacles play out!

            block = int((sec - 199.0) // 15)
            mode = block % 4
            if mode == 0:
                for _ in range(intensity_mult):
                    self.obstacles.append(FullScreenLaser('h', random.uniform(0.1, 0.9), 120))
            elif mode == 1:
                self.obstacles.append(ParticleBurst(random.randint(100, SCREEN_WIDTH-100), 0, 15 + int(10*level_progress), 14 + 10*level_progress, 100))
            elif mode == 2:
                pxs = []
                for _ in range(intensity_mult):
                    for p in self.app.players:
                        pxs.append(p.x + random.randint(-50, 50))
                if pxs: self.obstacles.append(PillarDrop(pxs, 90))
            elif mode == 3:
                for _ in range(intensity_mult):
                    self.obstacles.append(WallSlam('left', 0.2, 120))
                    self.obstacles.append(WallSlam('right', 0.2, 120))
        else:
            pass # No beat spawns in final explosion timeline

    def draw_background(self, surface):
        # Draw Parallax Background
        for star in self.parallax_stars:
            pygame.draw.circle(surface, star['color'], (int(star['x']), int(star['y'])), int(star['size']))
            
        for y in self.parallax_grids:
            pygame.draw.line(surface, (30, 10, 50), (0, int(y)), (SCREEN_WIDTH, int(y)), 2)
            
        for x in range(0, SCREEN_WIDTH, 100):
            pygame.draw.line(surface, (30, 10, 50), (x, 0), (x, SCREEN_HEIGHT), 2)

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
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, int(8 + intensity*2), 5 + level_progress*5, 800))
        
        if 25 <= sec < 26 and self.phase == 0:
            self.phase = 1
            self.obstacles.clear()
            self.app.shake_amount = 30
            # Massive WallSlams
            pass

        if 26 <= sec < 38:
            if self.phase == 1: 
                self.phase = 2
                self.obstacles.append(WallSlam('bottom', 0.5, 500))
            elif self.phase == 2 and sec > 31:
                self.phase = 3
                self.obstacles.append(WallSlam('top', 0.5, 500))

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
            count = max(1, 1 + int(intensity / 2))
            pxs = [random.randint(50, SCREEN_WIDTH-50) for _ in range(count)]
            self.obstacles.append(PillarDrop(pxs, 200))
            
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

    def draw_background(self, surface):
        # Draw Parallax Background
        for star in self.parallax_stars:
            pygame.draw.circle(surface, star['color'], (int(star['x']), int(star['y'])), int(star['size']))
            
        for y in self.parallax_grids:
            pygame.draw.line(surface, (30, 10, 50), (0, int(y)), (SCREEN_WIDTH, int(y)), 2)
            
        for x in range(0, SCREEN_WIDTH, 100):
            pygame.draw.line(surface, (30, 10, 50), (x, 0), (x, SCREEN_HEIGHT), 2)

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

class NeverGonnaGiveYouUpLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.phase = 0
        self.last_spawn = 0
        self.checkpoints = [77000, 136000]

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
                self.obstacles.append(WallSlam(random.choice(['left', 'right', 'top', 'bottom']), 0.2, 800))
                self.last_spawn = elapsed

        # 0:18 - 0:35 Verse 1: DVD Bouncing blocks
        elif 18 <= sec < 35:
            if len(self.obstacles) < 5:
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 10, 6, 500))

        # 0:35 - 0:42 Pre-Chorus 1: Rising Bubbles
        elif 35 <= sec < 42:
            pass # Replaced with shockwaves below if needed, or leave empty to build tension
            if elapsed - self.last_spawn > 800:
                self.obstacles.append(ShockwaveRing(random.randint(200, SCREEN_WIDTH-200), random.randint(200, SCREEN_HEIGHT-200), 1000, 10, 15, 300))
                self.last_spawn = elapsed

        # 0:42 - 1:00 Chorus 1: Starbursts
        elif 42 <= sec < 60:
            if elapsed - self.last_spawn > 500:
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 12, 12, 200))
                self.last_spawn = elapsed

        # 1:00 - 1:17 Verse 2: Laser Sweeps
        elif 60 <= sec < 77:
            if elapsed - self.last_spawn > 1500:
                is_horiz = random.random() < 0.5
                self.obstacles.append(FullScreenLaser('h' if is_horiz else 'v', random.uniform(0.1, 0.9), 400))
                self.last_spawn = elapsed

        # 1:17 - 1:25 Pre-Chorus 2: Bubbles + Slow Homing
        elif 77 <= sec < 85:
            if elapsed - self.last_spawn > 2000 and self.app.players:
                p = random.choice(self.app.players)
                self.obstacles.append(PillarDrop([p.x], 400))
                self.last_spawn = elapsed

        # 1:25 - 1:59 Chorus 2 & 3: Rotating Windmill
        elif 85 <= sec < 119:
            # Huge beam segments from center
            if elapsed - self.last_spawn > 200:
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 4, 15, 100))
                self.last_spawn = elapsed

        # 1:59 - 2:16 Bridge: Giant Pulses
        elif 119 <= sec < 136:
            if elapsed - self.last_spawn > 1200:
                self.obstacles.append(ShockwaveRing(random.randint(200, SCREEN_WIDTH-200), random.randint(200, SCREEN_HEIGHT-200), 2000, 25, 20, 800))
                self.last_spawn = elapsed

        # 2:16 - 2:32 Verse 3: Edges Closing In
        elif 136 <= sec < 152:
            if sec < 137 and len(self.obstacles) == 0:
                self.obstacles.append(WallSlam('left', 0.4, 100))
                self.obstacles.append(WallSlam('right', 0.4, 100))
            
            # Spawn bouncy threats in the middle
            if elapsed - self.last_spawn > 1000:
                self.obstacles.append(PillarDrop([SCREEN_WIDTH//2 + random.uniform(-100, 100)], 300))
                self.last_spawn = elapsed

        # 2:32 - 2:40 Pre-Chorus 3: Fast Bubbles
        elif 152 <= sec < 160:
            if elapsed - self.last_spawn > 300:
                self.obstacles.append(ParticleBurst(random.randint(100, SCREEN_WIDTH-100), SCREEN_HEIGHT, 10, 15, 0))
                self.last_spawn = elapsed

        # 2:40 - 3:14 Final Chorus: The Grand Finale (Starbursts + Lasers)
        elif 160 <= sec < 194:
            if elapsed - self.last_spawn > 1000:
                is_horiz = random.random() < 0.5
                self.obstacles.append(FullScreenLaser('h' if is_horiz else 'v', random.uniform(0.1, 0.9), 300))
                self.obstacles.append(ParticleBurst(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 20, 15, 150))
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

    def draw_background(self, surface):
        # Draw Parallax Background
        for star in self.parallax_stars:
            pygame.draw.circle(surface, star['color'], (int(star['x']), int(star['y'])), int(star['size']))
            
        for y in self.parallax_grids:
            pygame.draw.line(surface, (30, 10, 50), (0, int(y)), (SCREEN_WIDTH, int(y)), 2)
            
        for x in range(0, SCREEN_WIDTH, 100):
            pygame.draw.line(surface, (30, 10, 50), (x, 0), (x, SCREEN_HEIGHT), 2)

    def draw_extra(self, surface):
        pass

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

                oy = obs.get("y", -50)
                if oy == "PLAYER_Y":
                    if self.app.players: oy = self.app.players[0].y
                    else: oy = SCREEN_HEIGHT//2
                
                self.obstacles.append(Obstacle(
                    ox,
                    oy,
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
        
        font_sz = 80
        disp_name = selected_name.upper() if selected_name != "Secret" else "UNKNOWN"
        big_title = get_font(font_sz).render(disp_name, True, COLORS['white'])
        while big_title.get_width() > 600 and font_sz > 30:
            font_sz -= 5
            big_title = get_font(font_sz).render(disp_name, True, COLORS['white'])
        screen.blit(big_title, (detail_x, 100))
        
        big_artist = get_font(35, False).render(selected_song["artist"].upper(), True, (200, 200, 200))
        screen.blit(big_artist, (detail_x + 5, 190))
        
        if "duration" not in selected_song:
            try:
                selected_song["duration"] = pygame.mixer.Sound(selected_song["path"]).get_length()
            except:
                selected_song["duration"] = 0
                
        dur = selected_song["duration"]
        if dur > 0:
            m, s = int(dur // 60), int(dur % 60)
            dur_txt = get_font(30, False).render(f"Duration: {m}:{s:02d}", True, COLORS['blue'])
            screen.blit(dur_txt, (detail_x + 5, 240))
        
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
            box_surf.blit(opt_txt, (box_w//2 - opt_txt.get_width()//2, 120 + idx * 80))
            
            if is_sel:
                pygame.draw.polygon(box_surf, color, [
                    (box_w//2 - opt_txt.get_width()//2 - 40, 120 + idx * 80 + 15),
                    (box_w//2 - opt_txt.get_width()//2 - 20, 120 + idx * 80 + 25),
                    (box_w//2 - opt_txt.get_width()//2 - 40, 120 + idx * 80 + 35)
                ])
                
        rect = box_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(box_surf, rect.topleft)

    @staticmethod
    def draw_level_maker(app):
        if BG_IMG: 
            screen.blit(BG_IMG, (0,0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(150)
            screen.blit(overlay, (0, 0))
        else: 
            screen.fill(COLORS['bg'])

        for p in app.particles:
            p['y'] -= p['speed']
            if p['y'] < -20: p['y'] = SCREEN_HEIGHT + 20; p['x'] = random.randint(0, SCREEN_WIDTH)
            alpha = max(0, min(255, 100 + math.sin(pygame.time.get_ticks() * 0.002 + p['x']) * 50))
            p_surf = pygame.Surface((p['size'], p['size']), pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (*p['color'], int(alpha)), (0, 0, p['size'], p['size']))
            screen.blit(p_surf, (p['x'], p['y']))

        w = int(SCREEN_WIDTH * 0.8)
        h = int(SCREEN_HEIGHT * 0.8)
        box_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        time_ms = pygame.time.get_ticks()
        
        pygame.draw.rect(box_surf, (20, 20, 25, 220), (0, 0, w, h), border_radius=15)
        pygame.draw.rect(box_surf, COLORS['pink'], (0, 0, w, h), 3, border_radius=15)
        
        f_title = get_font(50)
        title = f_title.render("AUDIO ANALYZER", True, COLORS['pink'])
        box_surf.blit(title, (w//2 - title.get_width()//2, 30))
        
        if app.lm_state == 0:
            f_label = get_font(30)
            lbl = f_label.render("Enter Song Name / URL:", True, COLORS['white'])
            box_surf.blit(lbl, (w//2 - lbl.get_width()//2, 120))
            
            # Text box
            pygame.draw.rect(box_surf, (30, 30, 40), (w//2 - 300, 180, 600, 60), border_radius=10)
            pygame.draw.rect(box_surf, COLORS['pink'], (w//2 - 300, 180, 600, 60), 2, border_radius=10)
            
            f_input = get_font(35)
            # Text glitch effect occasionally
            q_color = COLORS['pink'] if random.random() < 0.05 and app.text_glitches else COLORS['white']
            q_surf = f_input.render(app.lm_query + ("_" if time_ms % 1000 < 500 else ""), True, q_color)
            box_surf.blit(q_surf, (w//2 - q_surf.get_width()//2, 192))
            
            # Draw Onscreen Keyboard
            key_size = 55
            padding = 10
            start_x = w//2 - (10 * (key_size + padding)) // 2
            start_y = 280
            for row_idx, row in enumerate(app.kb_layout):
                for col_idx, key in enumerate(row):
                    kx = start_x + col_idx * (key_size + padding)
                    ky = start_y + row_idx * (key_size + padding)
                    if key in ['<', '_', 'OK']:
                        kx += 20
                    is_selected = (app.kb_y == row_idx and app.kb_x == col_idx)
                    bg_color = (100, 100, 100) if is_selected else (30, 30, 40)
                    pygame.draw.rect(box_surf, bg_color, (kx, ky, key_size, key_size), border_radius=8)
                    pygame.draw.rect(box_surf, COLORS['pink'] if is_selected else (50, 50, 60), (kx, ky, key_size, key_size), 2, border_radius=8)
                    
                    lbl = key if key != '_' else 'SP'
                    k_surf = get_font(25).render(lbl, True, COLORS['white'])
                    box_surf.blit(k_surf, (kx + key_size//2 - k_surf.get_width()//2, ky + key_size//2 - k_surf.get_height()//2))
            
            # Helper text
            help_surf = get_font(20).render("Use Joystick to select, press X to type", True, (150, 150, 150))
            box_surf.blit(help_surf, (w//2 - help_surf.get_width()//2, h - 40))
            disp_query = app.lm_query
            if getattr(app, 'text_glitches', True) and random.random() < 0.05 and len(disp_query) > 0:
                glitch_idx = random.randint(0, len(disp_query)-1)
                disp_query = disp_query[:glitch_idx] + chr(random.randint(33, 126)) + disp_query[glitch_idx+1:]
                
            txt = f_input.render(disp_query + ("|" if time_ms % 1000 < 500 else ""), True, COLORS['pink'])
            box_surf.blit(txt, (w//2 - 280, 190))
            
            help_txt = get_font(20).render("Press ENTER to start analysis. ESC to cancel.", True, (150, 150, 150))
            box_surf.blit(help_txt, (w//2 - help_txt.get_width()//2, 260))
            
        elif app.lm_state == 1:
            # Analysis mode!
            f_stat = get_font(28)
            stat_txt = getattr(app, 'lm_status', 'Processing...')
            # Glitch text for hacker aesthetic
            if getattr(app, 'text_glitches', True) and random.random() < 0.1:
                stat_txt = "".join([chr(random.randint(33, 126)) if random.random() < 0.05 else c for c in stat_txt])
            stat_render = f_stat.render(stat_txt, True, (0, 255, 150))
            box_surf.blit(stat_render, (w//2 - stat_render.get_width()//2, 120))
            
            # Advanced Multi-band Visualizer
            waveforms = getattr(app, 'lm_waveforms', None)
            if waveforms and len(waveforms) == 8:
                vis_w = 600
                vis_h = 150
                vis_x = w//2 - vis_w//2
                vis_y = 200
                pygame.draw.rect(box_surf, (5, 5, 10, 200), (vis_x, vis_y, vis_w, vis_h))
                pygame.draw.rect(box_surf, (0, 100, 255), (vis_x, vis_y, vis_w, vis_h), 1)
                
                band_colors = [
                    (255, 0, 0), (255, 100, 0), (255, 255, 0), (0, 255, 0),
                    (0, 255, 255), (0, 100, 255), (100, 0, 255), (255, 0, 255)
                ]
                
                bar_w = vis_w // 8
                for i in range(8):
                    val = waveforms[i] * vis_h
                    # Animated visualizer bars
                    anim_val = val * (0.8 + 0.2 * math.sin(time_ms * 0.01 + i))
                    pygame.draw.rect(box_surf, band_colors[i], (vis_x + i*bar_w + 5, vis_y + vis_h - anim_val, bar_w - 10, anim_val))
            
            # Glowing Progress bar
            prog_y = 400
            prog_w = 600
            pygame.draw.rect(box_surf, (30, 30, 40), (w//2 - prog_w//2, prog_y, prog_w, 20), border_radius=10)
            
            # Smooth out progress variable if it exists
            target_prog = getattr(app, 'lm_progress', 0.0)
            if not hasattr(app, 'smooth_prog'): app.smooth_prog = target_prog
            app.smooth_prog += (target_prog - app.smooth_prog) * 0.1
            
            fill_w = int(prog_w * app.smooth_prog)
            if fill_w > 0:
                # Dynamic gradient/color pulse
                r = int(127 + 128 * math.sin(time_ms * 0.005))
                b = int(127 + 128 * math.cos(time_ms * 0.005))
                pygame.draw.rect(box_surf, (r, 100, b), (w//2 - prog_w//2, prog_y, fill_w, 20), border_radius=10)
                # Glowing tip
                pygame.draw.circle(box_surf, (255, 255, 255), (w//2 - prog_w//2 + fill_w, prog_y + 10), 12)
                
            # Rotating Loading Icon
            rot_angle = -(time_ms % 3600) / 10.0
            load_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.arc(load_surf, (0, 255, 200), (5, 5, 30, 30), 0, math.pi*1.5, 4)
            rot_surf = pygame.transform.rotate(load_surf, rot_angle)
            box_surf.blit(rot_surf, (w//2 - prog_w//2 - 50 - rot_surf.get_width()//2, prog_y - 10))
                
            pct_txt = get_font(20).render(f"{int(app.smooth_prog*100)}%", True, COLORS['white'])
            box_surf.blit(pct_txt, (w//2 - pct_txt.get_width()//2, prog_y + 30))
            
            if hasattr(app, 'avg_gen_time') and hasattr(app, 'lm_start_time'):
                import time
                rem = max(0, int(app.avg_gen_time - (time.time() - app.lm_start_time)))
                est_txt = get_font(20).render(f"Estimated Time Remaining: {rem}s", True, (150, 150, 150))
                box_surf.blit(est_txt, (w//2 - est_txt.get_width()//2, prog_y + 70))
            
        elif app.lm_state == 2:
            # Done / Error
            f_stat = get_font(30)
            stat_render = f_stat.render(getattr(app, 'lm_status', 'Done!'), True, COLORS['pink'])
            box_surf.blit(stat_render, (w//2 - stat_render.get_width()//2, int(h*0.4)))
            
            help_txt = get_font(25).render("Press ENTER to configure level & sync lyrics, or ESC for Menu", True, (150, 150, 150))
            box_surf.blit(help_txt, (w//2 - help_txt.get_width()//2, int(h*0.6)))
            
        screen.blit(box_surf, (SCREEN_WIDTH//2 - w//2, SCREEN_HEIGHT//2 - h//2))

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
            import re
            lrc_path = re.sub(r' \[(Easy|Normal|Hard)\]\.json$', '.lrc', song_data.get("json_path", ""))
            if song_data.get("class") == "DynamicLevel" and "py_path" in song_data:
                lrc_path = song_data["py_path"].replace(".py", ".lrc")
            elif "path" in song_data and song_data["path"]:
                lrc_path = song_data["path"].replace(".mp3", ".lrc").replace(".wav", ".lrc").replace(".m4a", ".lrc")
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
        
        t_help = get_font(20).render("Use [A]/[D] or [Left]/[Right] to adjust values", True, (150, 150, 150))
        screen.blit(t_help, (opt_x, opt_y - 30))
        
        bpm_val = getattr(app, 'config_bpm', 120.0)
        opts = [
            f"Delay: {getattr(app, 'config_delay', 0)} ms",
            f"Music Pos: {getattr(app, 'config_start_pos', 0) // 1000} s",
            f"Difficulty: {getattr(app, 'config_diff', 'Normal')}",
            f"Custom BPM: {int(bpm_val)}",
            f"Chroma Colors: {'ON' if getattr(app, 'config_chroma', True) else 'OFF'}",
            f"Lyrics: {'ON' if getattr(app, 'config_lyrics_enabled', True) else 'OFF'}",
            "Save & Continue"
        ]
        
        for idx, text in enumerate(opts):
            color = COLORS['yellow'] if getattr(app, 'config_idx', 0) == idx else (200, 200, 200)
            if text == "Save & Continue": color = COLORS['green'] if getattr(app, 'config_idx', 0) == idx else (200, 200, 200)
            
            t = get_font(40).render(text, True, color)
            screen.blit(t, (opt_x, opt_y + idx * 60))
            if getattr(app, 'config_idx', 0) == idx and idx < 6:
                screen.blit(get_font(30).render("<   >", True, COLORS['yellow']), (opt_x - 60, opt_y + idx * 60 + 5))

    @staticmethod
    def draw_difficulty_select(app):
        UI.draw_level_select(app)
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        s.set_alpha(150)
        s.fill((0, 0, 0))
        screen.blit(s, (0, 0))
        
        box_w, box_h = 400, 300
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        pygame.draw.rect(screen, (30, 30, 30), (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, COLORS['pink'], (box_x, box_y, box_w, box_h), 3)
        
        title = get_font(30).render("Select Difficulty", True, COLORS['white'])
        screen.blit(title, (box_x + box_w//2 - title.get_width()//2, box_y + 20))
        
        diffs = ["Easy", "Normal", "Hard"]
        colors = [COLORS['blue'], COLORS['yellow'], COLORS['pink']]
        for i, diff in enumerate(diffs):
            color = colors[i] if getattr(app, 'diff_sel_idx', 1) == i else (100, 100, 100)
            text = get_font(40).render(diff, True, color)
            tx = box_x + box_w//2 - text.get_width()//2
            ty = box_y + 100 + i * 60
            screen.blit(text, (tx, ty))
            if getattr(app, 'diff_sel_idx', 1) == i:
                screen.blit(get_font(40).render(">", True, color), (tx - 40, ty))
                screen.blit(get_font(40).render("<", True, color), (tx + text.get_width() + 10, ty))

# --- Main App Logic ---
def main():
    import os, glob, json
    custom_dir = os.path.join(os.path.dirname(__file__), "CustomLevels")
    if os.path.exists(custom_dir):
        for f in glob.glob(os.path.join(custom_dir, "**", "*.py"), recursive=True):
            if "__init__" in f: continue
            try:
                name = os.path.basename(f).replace(".py", "")
                audio_path = f.replace(".py", ".ogg")
                if not os.path.exists(audio_path): audio_path = f.replace(".py", ".mp3")
                if not os.path.exists(audio_path): audio_path = f.replace(".py", ".wav")
                if not os.path.exists(audio_path): audio_path = f.replace(".py", ".m4a")
                if not os.path.exists(audio_path): audio_path = f.replace(".py", ".webm")
                SONGS[name] = {
                    "path": audio_path,
                    "artist": "Dynamic Python Generator",
                    "surf": None,
                    "class": "DynamicLevel",
                    "py_path": f,
                    "bpm": 120.0
                }
                try:
                    with open(f, 'r', encoding='utf-8') as pf:
                        for line in pf:
                            if "self.bpm =" in line:
                                SONGS[name]["bpm"] = float(line.split("=")[1].strip())
                                break
                except: pass
                cover_path = f.replace(".py", ".jpg")
                if os.path.exists(cover_path):
                    try:
                        SONGS[name]["surf"] = pygame.transform.scale(pygame.image.load(cover_path).convert(), (400, 400))
                    except: pass
            except: pass

        for f in glob.glob(os.path.join(custom_dir, "**", "*.json"), recursive=True):
            if " [Easy]" in f or " [Hard]" in f: continue
            try:
                with open(f, 'r') as fp:
                    data = json.load(fp)
                    name = data.get("name", os.path.basename(f).replace(" [Normal].json", "").replace(".json", ""))
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
        dt = clock.tick(30)
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
                                if SONGS[name].get("class") in [CustomLevel, "DynamicLevel"]:
                                    app.state = GameState.DIFFICULTY_SELECT
                                    app.diff_sel_idx = 1
                                else:
                                    start_game(app)
                                    
                elif app.state == GameState.DIFFICULTY_SELECT:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        app.diff_sel_idx = max(0, getattr(app, 'diff_sel_idx', 1) - 1)
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        app.diff_sel_idx = min(2, getattr(app, 'diff_sel_idx', 1) + 1)
                    if event.key == pygame.K_ESCAPE:
                        app.state = GameState.LEVEL_SELECT
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        name = app.levels[app.selected_level_idx]
                        diffs = ["Easy", "Normal", "Hard"]
                        chosen_diff = diffs[getattr(app, 'diff_sel_idx', 1)]
                        
                        if SONGS[name].get("class") == "DynamicLevel":
                            app.config_level_name = name
                            app.config_diff = chosen_diff
                            app.config_delay = int(app.lyric_offsets.get(name, 0.0))
                            app.config_start_pos = 0
                            app.config_health = 100
                            
                            if event.key == pygame.K_SPACE:
                                app.state = GameState.LEVEL_CONFIG
                                if name in SONGS and "bpm" in SONGS[name]:
                                    app.config_bpm = float(SONGS[name]["bpm"])
                                elif hasattr(app, 'custom_bpms') and name in app.custom_bpms:
                                    app.config_bpm = app.custom_bpms[name]
                                else:
                                    app.config_bpm = 120.0
                                if "path" in SONGS[name] and os.path.exists(SONGS[name]["path"]):
                                    pygame.mixer.music.load(SONGS[name]["path"])
                                    pygame.mixer.music.play()
                            else:
                                start_game(app)
                        else:
                            base_json = SONGS[name]["json_path"].replace(" [Normal].json", "").replace(".json", "")
                            diff_json = f"{base_json} [{chosen_diff}].json"
                            if os.path.exists(diff_json):
                                SONGS[name]["json_path_current"] = diff_json
                            else:
                                SONGS[name]["json_path_current"] = SONGS[name]["json_path"]
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
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if opt == "Back":
                            app.state = GameState.MENU

                elif app.state == GameState.LEVEL_MAKER:
                    if app.lm_state == 0:
                        if event.type == pygame.JOYHATMOTION and event.value != (0,0):
                            hx, hy = event.value
                            if hx > 0.5: app.kb_x += 1
                            elif hx < -0.5: app.kb_x -= 1
                            if hy > 0.5: app.kb_y -= 1
                            elif hy < -0.5: app.kb_y += 1
                            app.kb_y = max(0, min(len(app.kb_layout)-1, app.kb_y))
                            app.kb_x = max(0, min(len(app.kb_layout[app.kb_y])-1, app.kb_x))
                        if event.type == pygame.JOYBUTTONDOWN and event.button in [0, 1, 9]:
                            key = app.kb_layout[app.kb_y][app.kb_x]
                            if key == '<': app.lm_query = app.lm_query[:-1]
                            elif key == '_': app.lm_query += ' '
                            elif key == 'OK' and len(app.lm_query) > 0:
                                app.lm_state = 1
                                app.lm_status = f"Searching SpotDL for: {app.lm_query}..."
                                import threading
                                threading.Thread(target=run_level_maker, args=(app, app.lm_query), daemon=True).start()
                            elif len(key) == 1:
                                app.lm_query += key
                        
                        if event.type == pygame.KEYDOWN:
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
                        app.config_idx = (getattr(app, 'config_idx', 0) - 1) % 7
                    if event.key in [pygame.K_s, pygame.K_DOWN]:
                        app.config_idx = (getattr(app, 'config_idx', 0) + 1) % 7
                        
                    idx = getattr(app, 'config_idx', 0)
                    if event.key in [pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT]:
                        direction = -1 if event.key in [pygame.K_a, pygame.K_LEFT] else 1
                        if idx == 0: app.config_delay += 100 * direction
                        elif idx == 1:
                            app.config_start_pos = max(0, getattr(app, 'config_start_pos', 0) + 5000 * direction)
                            try:
                                pygame.mixer.music.play(start=app.config_start_pos / 1000.0)
                            except: pass
                            app.config_start_time = pygame.time.get_ticks()
                        elif idx == 2:
                            diffs = ["Easy", "Normal", "Hard"]
                            app.config_diff = diffs[(diffs.index(getattr(app, 'config_diff', 'Normal')) + direction) % 3]
                        elif idx == 3:
                            shift = 10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
                            app.config_bpm = max(1, getattr(app, 'config_bpm', 120.0) + shift * direction)
                        elif idx == 4:
                            app.config_chroma = not getattr(app, 'config_chroma', True)
                        elif idx == 5:
                            app.config_lyrics_enabled = not getattr(app, 'config_lyrics_enabled', True)
                            
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if idx == 6:
                            if not hasattr(app, 'custom_bpms'): app.custom_bpms = {}
                            import re
                            base_name = re.sub(r' \[(Easy|Normal|Hard)\]$', '', app.config_level_name)
                            app.custom_bpms[base_name] = getattr(app, 'config_bpm', 120.0)
                            
                            for diff in ["Easy", "Normal", "Hard"]:
                                lvl_name = f"{base_name} [{diff}]"
                                app.lyric_offsets[lvl_name] = getattr(app, 'config_delay', 0)
                                app.lyric_offsets[f"{lvl_name}_lyrics"] = getattr(app, 'config_lyrics_enabled', True)
                            save_lyric_offsets(app.lyric_offsets)
                            
                            song_data = SONGS.get(app.config_level_name, {})
                            if "json_path" in song_data and os.path.exists(song_data["json_path"]):
                                base_json = re.sub(r' \[(Easy|Normal|Hard)\]\.json$', '', song_data["json_path"])
                                for diff in ["Easy", "Normal", "Hard"]:
                                    jp = f"{base_json} [{diff}].json"
                                    if os.path.exists(jp):
                                        with open(jp, 'r') as f:
                                            data = json.load(f)
                                        data["boss_entity"] = getattr(app, 'config_boss', True)
                                        data["chroma_colors"] = getattr(app, 'config_chroma', True)
                                        with open(jp, 'w') as f:
                                            json.dump(data, f, indent=4)
                            
                            if app.config_level_name in app.levels:
                                app.selected_level_idx = app.levels.index(app.config_level_name)
                            pygame.mixer.music.stop()
                            start_game(app)
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
            if getattr(app, 'level_start_countdown_timer', 0) > 0:
                app.level_start_countdown_timer -= dt
                if app.level_start_countdown_timer <= 0:
                    pygame.mixer.music.play()
            else:
                app.active_level.update(dt)
                for p in app.players: p.update(dt, app)
            if app.lives <= 0:
                app.state = GameState.SHATTER_DEATH
                app.shatter_timer = 0
                app.shatter_duration = 3000
                pygame.mixer.music.set_volume(0.15) # Slow down effect drop
                
                # Create massive particle explosion
                app.shatter_particles = []
                p_color = SHAPE_COLORS.get(app.players[0].shape, (0, 255, 255))
                for _ in range(400):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(5, 35)
                    app.shatter_particles.append({
                        'x': app.players[0].x,
                        'y': app.players[0].y,
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'life': random.uniform(1.0, 3.0),
                        'color': p_color if random.random() > 0.3 else (255, 255, 255)
                    })
                app.shatter_player = app.players[0]
            elif getattr(app, 'level_start_countdown_timer', 0) <= 0 and not pygame.mixer.music.get_busy() and app.active_level.name != "CLOSE TO ME":
                app.state = GameState.COMPLETED
                app.end_screen_timer = pygame.time.get_ticks()

        elif app.state == GameState.SHATTER_DEATH:
            # Slow motion explosion that speeds up!
            app.shatter_timer += dt
            t = min(1.0, app.shatter_timer / app.shatter_duration)
            
            # Start very slow, speed up dramatically (cubic ease-in)
            speed_mult = 0.05 + (t ** 3) * 2.0
            dt_slow = dt * speed_mult
            
            # Intense screen shake that decays
            app.shake_amount = int(20 * (1.0 - t))
            
            app.active_level.update(dt_slow)
            for p in app.players: 
                if getattr(app, 'shatter_player', None) != p:
                    p.update(dt_slow, app)
            
            if hasattr(app, 'shatter_particles'):
                for p in app.shatter_particles:
                    p['vy'] += 0.8 * (dt / 16.0) # Gravity
                    p['x'] += p['vx'] * (dt / 16.0) * speed_mult
                    p['y'] += p['vy'] * (dt / 16.0) * speed_mult
                    p['life'] -= (dt / 1000.0)
            
            if app.shatter_timer > app.shatter_duration:
                app.state = GameState.GAMEOVER
                app.end_screen_timer = pygame.time.get_ticks()
                pygame.mixer.music.stop()
                
        screen.fill(COLORS['bg'])
        offset_x = random.uniform(-app.shake_amount, app.shake_amount)
        offset_y = random.uniform(-app.shake_amount, app.shake_amount)
        app.shake_amount *= 0.9
        render_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        render_surf.fill(COLORS['bg'])

        if app.state == GameState.LEVEL_MAKER and getattr(app, 'lm_state', 0) == 2:
            app.state = GameState.LEVEL_CONFIG
            app.config_level_name = getattr(app, 'lm_last_generated_name', getattr(app, 'lm_query', ""))
            if app.config_level_name in SONGS and "bpm" in SONGS[app.config_level_name]:
                app.config_bpm = float(SONGS[app.config_level_name]["bpm"])
            elif hasattr(app, 'custom_bpms') and app.config_level_name in app.custom_bpms:
                app.config_bpm = app.custom_bpms[app.config_level_name]
            else:
                app.config_bpm = 120.0
            if app.config_level_name in SONGS:
                path = SONGS[app.config_level_name].get("path", "")
                if path and os.path.exists(path):
                    try:
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                    except: pass
            app.config_delay = 0
            app.config_start_pos = 0
            app.config_start_time = pygame.time.get_ticks()
            app.config_idx = 0
            app.lm_state = 0
            
        if app.state == GameState.WARNING: UI.draw_warning(app)
        elif app.state == GameState.MENU: UI.draw_menu(app)
        elif app.state == GameState.LEVEL_SELECT: UI.draw_level_select(app)
        elif app.state == GameState.SKINS: UI.draw_skins(app)
        elif app.state == GameState.SETTINGS: UI.draw_settings(app)
        elif app.state == GameState.LEVEL_MAKER: UI.draw_level_maker(app)
        elif app.state == GameState.LEVEL_CONFIG: UI.draw_level_config(app)
        elif app.state == GameState.DIFFICULTY_SELECT: UI.draw_difficulty_select(app)
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
            
            if hasattr(app.active_level, 'rms_curve') and app.active_level.rms_curve:
                idx = int((app.active_level.elapsed_ms + app.lyric_offsets.get(app.active_level.name, 0)) / 100)
                if idx >= 0 and idx < len(app.active_level.rms_curve):
                    sb = app.active_level.rms_curve[idx].get("sub_bass", 0)
                    b = app.active_level.rms_curve[idx].get("bass", 0)
                    if sb + b > 1.3:
                        flash_alpha = min(150, int((sb + b - 1.3) * 200))
                        app.shake_amount = max(app.shake_amount, int((sb + b - 1.3) * 12))
                        if flash_alpha > 0:
                            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                            flash.fill(COLORS['white'])
                            flash.set_alpha(flash_alpha)
                            render_surf.blit(flash, (0, 0))
            
            # Draw lives as shapes
            start_x = 50
            start_y = 50
            for i in range(3):
                color = SHAPE_COLORS.get(app.players[0].shape, COLORS['blue']) if i < app.lives else (50, 50, 50)
                draw_shape(render_surf, app.players[0].shape, color, (start_x + i * 40, start_y), 15)
            
            # Draw score & continues
            font_ui = get_font(24)
            score_txt = font_ui.render(f"SCORE: {app.score}", True, COLORS['white'])
            cont_txt = font_ui.render(f"CONTINUES: {app.continues}", True, COLORS['white'])
            render_surf.blit(score_txt, (50, 80))
            render_surf.blit(cont_txt, (50, 110))
            
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
                
            if getattr(app, 'level_start_countdown_timer', 0) > 0:
                dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                dim.fill((0, 0, 0))
                dim.set_alpha(150)
                render_surf.blit(dim, (0, 0))
                cd_val = math.ceil(app.level_start_countdown_timer / 1000)
                txt = get_font(250, bold=True).render(str(cd_val), True, COLORS['white'])
                ms_rem = app.level_start_countdown_timer % 1000
                if cd_val == 3 and ms_rem == 0: scale = 1.0
                else: scale = 1.0 + (ms_rem / 1000.0) * 0.5
                scaled_txt = pygame.transform.smoothscale(txt, (int(txt.get_width()*scale), int(txt.get_height()*scale)))
                render_surf.blit(scaled_txt, (SCREEN_WIDTH//2 - scaled_txt.get_width()//2, SCREEN_HEIGHT//2 - scaled_txt.get_height()//2))
                
            screen.blit(render_surf, (offset_x, offset_y))
            if app.fade_alpha > 0:
                fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                fade.fill((0,0,0))
                fade.set_alpha(app.fade_alpha)
                screen.blit(fade, (0,0))
        
        elif app.state == GameState.SHATTER_DEATH:
            # Draw everything same as playing, but with slow motion effect and particles
            if hasattr(app.active_level, 'draw_background'):
                app.active_level.draw_background(render_surf)
            else:
                for x in range(0, SCREEN_WIDTH, 60): pygame.draw.line(render_surf, (20, 20, 20), (x, 0), (x, SCREEN_HEIGHT))
                for y in range(0, SCREEN_HEIGHT, 60): pygame.draw.line(render_surf, (20, 20, 20), (0, y), (SCREEN_WIDTH, y))
            
            if hasattr(app.active_level, 'draw_background_lyrics'):
                app.active_level.draw_background_lyrics(render_surf)
            for obs in app.active_level.obstacles: obs.draw(render_surf, app)
            app.active_level.draw_extra(render_surf)
            
            for p in app.players: 
                if getattr(app, 'shatter_player', None) != p:
                    p.draw(render_surf)
                    
            if hasattr(app, 'shatter_particles'):
                for p in app.shatter_particles:
                    if p['life'] > 0:
                        alpha = min(255, max(0, int(p['life'] * 255)))
                        size = max(1, int(p['life'] * 3))
                        pygame.draw.circle(render_surf, (*p['color'], alpha), (int(p['x']), int(p['y'])), size)
                        
            # Draw white flash over the screen
            t = min(1.0, app.shatter_timer / app.shatter_duration)
            flash_alpha = max(0, int(255 * (1.0 - t*3))) # quick bright flash
            if flash_alpha > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash_surf.fill((255, 255, 255))
                flash_surf.set_alpha(flash_alpha)
                render_surf.blit(flash_surf, (0, 0))

            # Apply calculated shake amount
            offset_x = random.uniform(-app.shake_amount, app.shake_amount) if hasattr(app, 'shake_amount') else 0
            offset_y = random.uniform(-app.shake_amount, app.shake_amount) if hasattr(app, 'shake_amount') else 0
            # Grayscale / Chromatic filter over everything to look dramatic
            filter_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            filter_surf.fill((255, 0, 0))
            filter_surf.set_alpha(int(100 * (1 - app.shatter_timer / app.shatter_duration)))
            render_surf.blit(filter_surf, (0, 0))
            
            screen.blit(render_surf, (offset_x, offset_y))
        elif app.state == GameState.PAUSED:
            if app.active_level:
                for x in range(0, SCREEN_WIDTH, 60): pygame.draw.line(render_surf, (20, 20, 20), (x, 0), (x, SCREEN_HEIGHT))
                for y in range(0, SCREEN_HEIGHT, 60): pygame.draw.line(render_surf, (20, 20, 20), (0, y), (SCREEN_WIDTH, y))
                if hasattr(app.active_level, 'draw_background_lyrics'):
                    app.active_level.draw_background_lyrics(render_surf)
                for obs in app.active_level.obstacles: obs.draw(render_surf, app)
                app.active_level.draw_extra(render_surf)
                for p in app.players: p.draw(render_surf)
                # Draw lives as shapes
                start_x = 50
                start_y = 50
                for i in range(3):
                    color = SHAPE_COLORS.get(app.players[0].shape, COLORS['blue']) if i < app.lives else (50, 50, 50)
                    draw_shape(render_surf, app.players[0].shape, color, (start_x + i * 40, start_y), 15)
                
                screen.blit(render_surf, (0, 0))
            
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
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//2 - 150 + float_y))
                
                # Rank System
                if elapsed_end > 1000:
                    rank_alpha = min(255, int(((elapsed_end-1000) / 1000) * 255))
                    hp = app.lives
                    if hp >= 3: rank, r_col = "S", (255, 215, 0) # Gold
                    elif hp >= 2: rank, r_col = "A", (0, 255, 0)
                    elif hp >= 1: rank, r_col = "B", (0, 200, 255)
                    else: rank, r_col = "C", (255, 150, 0)
                    
                    r_txt = get_font(150, bold=True).render(rank, True, r_col)
                    r_txt.set_alpha(rank_alpha)
                    
                    # Pulse effect for S rank
                    if rank == "S":
                        r_scale = 1.0 + math.sin(elapsed_end * 0.01) * 0.1
                        r_txt = pygame.transform.smoothscale(r_txt, (int(r_txt.get_width()*r_scale), int(r_txt.get_height()*r_scale)))
                        
                    screen.blit(r_txt, (SCREEN_WIDTH//2 - r_txt.get_width()//2, SCREEN_HEIGHT//2 + 20 + float_y))
                    
                    hp_txt = font_medium.render(f"Health Remaining: {int(hp)}%", True, COLORS['white'])
                    hp_txt.set_alpha(rank_alpha)
                    screen.blit(hp_txt, (SCREEN_WIDTH//2 - hp_txt.get_width()//2, SCREEN_HEIGHT//2 + 180 + float_y))

            if elapsed_end > 4000:
                sub = font_medium.render("PRESS ANY KEY TO CONTINUE", True, COLORS['white'])
                if (elapsed_end // 500) % 2 == 0:
                    screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, SCREEN_HEIGHT//2 + 250))

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
        app.state = GameState.MENU
        return
    app.state = GameState.PLAYING
    app.lives = 3
    app.score = 0
    app.continues = 3
    app.fade_alpha = 0
    app.players = [Player(1, app.p1_shape)]
    if app.is_p2_enabled: app.players.append(Player(2, app.p2_shape))
    level_classes = {"Annihilate": AnnihilateLevel, "CLOSE TO ME": CloseToMeLevel, "Never Gonna Give You Up": NeverGonnaGiveYouUpLevel}
    
    song_cls = SONGS[name].get("class")
    if song_cls == CustomLevel:
        app.active_level = CustomLevel(name, app, SONGS[name].get("json_path_current", SONGS[name]["json_path"]))
    elif song_cls == "DynamicLevel":
        py_path = SONGS[name].get("py_path")
        import importlib.util
        spec = importlib.util.spec_from_file_location("DynamicLevelModule", py_path)
        dyn_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dyn_module)
        app.active_level = dyn_module.DynamicLevel(name, app)
        if hasattr(app, 'custom_bpms') and name in app.custom_bpms:
            app.active_level.bpm = app.custom_bpms[name]
    else:
        app.active_level = level_classes[name](name, app)
        
    load_music_safely(SONGS[name]["path"])
    pygame.mixer.music.set_volume(1.0)
    app.level_start_countdown_timer = 3000


def run_level_maker(app, query):
    import subprocess, sys, os, glob, json, math, random, shutil, time
    start_time = time.time()
    app.lm_start_time = start_time
    custom_dir = os.path.join(os.path.dirname(__file__), "CustomLevels")
    os.makedirs(custom_dir, exist_ok=True)
    
    app.lm_progress = 0.02
    app.lm_status = "Checking dependencies..."
    try:
        pkgs = ["spotdl", "soundfile", "librosa", "lazy_loader"]
        app.lm_status = "Installing SpotDL and audio libraries..."
        app.lm_progress = 0.06
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs + ["--upgrade", "--break-system-packages"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        app.lm_status = "Initializing audio converters (FFmpeg)..."
        subprocess.run([sys.executable, "-m", "spotdl", "--download-ffmpeg"], input=b"n\n", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
        
    app.lm_status = "SpotDL ready. Preparing search..."
    app.lm_progress = 0.10
    
    try:
        tmp_dir = os.path.join(custom_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        for f in glob.glob(os.path.join(tmp_dir, "*")): 
            if os.path.isfile(f): os.remove(f)
        
        app.lm_status = f"Searching for: {query}"
        app.lm_progress = 0.14
        
        cmd = [sys.executable, "-m", "spotdl", query, "--output", tmp_dir, "--generate-lrc", "--format", "ogg"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        import re
        
        app.lm_status = "Found song. Starting download..."
        app.lm_progress = 0.18
        
        for line in process.stdout:
            m = re.search(r'(\d+)%', line)
            if m:
                app.lm_status = f"Downloading audio track... {m.group(1)}%"
                pct = int(m.group(1))
                app.lm_progress = 0.24 + (pct / 100.0) * 0.18
        process.wait()
    except Exception as e:
        app.lm_status = f"Error downloading: {e}"
        app.lm_state = 2
        return

    app.lm_status = "Download complete. Verifying file..."
    app.lm_progress = 0.42

    audio_file = None
    for ext in ["*.ogg", "*.mp3", "*.m4a", "*.wav", "*.webm"]:
        files = glob.glob(os.path.join(tmp_dir, ext))
        if files:
            audio_file = files[0]
            break

    if audio_file and not audio_file.endswith(".ogg"):
        app.lm_status = "Converting audio to perfect-sync OGG..."
        app.lm_progress = 0.45
        ogg_file = os.path.splitext(audio_file)[0] + ".ogg"
        try:
            subprocess.check_call(["ffmpeg", "-y", "-i", audio_file, "-vn", "-acodec", "libvorbis", ogg_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(audio_file)
            audio_file = ogg_file
        except Exception as e:
            app.lm_status = f"Warning: Conversion to OGG failed: {e}"
            import time; time.sleep(2)
                
    if not audio_file:
        app.lm_status = "Error: SpotDL did not download an audio file."
        app.lm_state = 2
        return
        
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    base_name_clean = "".join(c for c in base_name if c.isalnum() or c in " _-").strip()
    
    for lvl in list(SONGS.keys()):
        if lvl == base_name_clean:
            if lvl in app.levels: app.levels.remove(lvl)
            if lvl in SONGS: del SONGS[lvl]
    
    song_dir = os.path.join(custom_dir, base_name_clean)
    os.makedirs(song_dir, exist_ok=True)
    
    ext = os.path.splitext(audio_file)[1]
    final_audio = os.path.join(song_dir, f"{base_name_clean}{ext}")
    cover_path = os.path.join(song_dir, f"{base_name_clean}.jpg")
    
    app.lm_status = "Moving files..."
    app.lm_progress = 0.50
    if os.path.exists(final_audio): os.remove(final_audio)
    shutil.move(audio_file, final_audio)
    
    lrc_files = glob.glob(os.path.join(tmp_dir, "*.lrc"))
    if lrc_files:
        final_lrc = os.path.join(song_dir, f"{base_name_clean}.lrc")
        if os.path.exists(final_lrc): os.remove(final_lrc)
        shutil.move(lrc_files[0], final_lrc)

    # Fetch Album Cover
    app.lm_status = "Fetching album artwork..."
    try:
        import urllib.request, urllib.parse
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(base_name)}&entity=song&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'JSAB-Arcade/1.0'})
        res = urllib.request.urlopen(req, timeout=5).read()
        data = json.loads(res)
        if data['resultCount'] > 0:
            artwork_url = data['results'][0].get('artworkUrl100', '')
            if artwork_url:
                urllib.request.urlretrieve(artwork_url.replace("100x100bb", "600x600bb"), cover_path)
    except: pass

    app.lm_status = "Audio Analysis (Heuristic Mode)..."
    app.lm_progress = 0.55

    # Completely removed NumPy dependency for Pi 400 compatibility.
    # Uses heuristic beat generation and intensity curve based on song length.
    import pygame
    try:
        snd = pygame.mixer.Sound(final_audio)
        length_sec = min(snd.get_length(), 240.0) # Cap at 240 seconds
    except:
        length_sec = 240.0

    song_bpm = 120.0
    beat_interval = 60000.0 / song_bpm
    beat_times = [int(i * beat_interval) for i in range(int(length_sec * 1000 / beat_interval))]
    beat_patterns = [random.randint(0, 4) for _ in beat_times]

    app.lm_progress = 0.85
    app.lm_status = "Compiling Neural Patterns to Python Script..."
    app.lm_progress = 0.90

    # Section-aware scheduling (energy curve)
    clusters = []
    current_cluster = []
    for t in beat_times:
        if not current_cluster:
            current_cluster.append(t)
        else:
            if t - current_cluster[-1] < 450:
                current_cluster.append(t)
            else:
                clusters.append(current_cluster)
                current_cluster = [t]
    if current_cluster: clusters.append(current_cluster)

    intensity_curve = []
    for ms in range(0, int(length_sec * 1000) + 100, 100):
        # Heuristic: slow build up, drops every 30 seconds
        sec = ms / 1000.0
        phase = (sec % 30) / 30.0
        energy = min(1.0, (phase * 1.5) if phase < 0.8 else (1.0 - (phase - 0.8) * 5))
        intensity_curve.append(round(energy, 3))

    # Generate unique theme based on song name
    import hashlib
    seed_val = int(hashlib.md5(base_name_clean.encode()).hexdigest(), 16)
    random.seed(seed_val)
    # JSAB Obstacle pattern vocabulary
    theme_patterns = [0, 1, 2, 3, 4]

    import pprint
    
    python_script = f"""# GENERATED LEVEL: {base_name_clean}
import random, math, pygame
from game import Level, Obstacle, FullScreenLaser, WallSlam, ParticleBurst, PillarDrop, ShockwaveRing, SCREEN_WIDTH, SCREEN_HEIGHT

class DynamicLevel(Level):
    def __init__(self, name, app):
        super().__init__(name, app)
        self.bpm = {song_bpm}
        self.clusters = {clusters}
        self.intensity_curve = {intensity_curve}
        self.theme_patterns = {theme_patterns}
        self.beat_times = {beat_times}
        self.beat_patterns = {beat_patterns}
        self.cluster_idx = 0
        self.beat_idx = 0
        
        # Calculate checkpoints at 1/3 and 2/3 of the song
        song_length = self.beat_times[-1] if self.beat_times else 0
        if song_length > 30000:
            self.checkpoints = [int(song_length * 0.33), int(song_length * 0.66)]
        
    def on_beat(self, elapsed):
        sync_offset = self.app.lyric_offsets.get(self.name, 0)
        true_elapsed = elapsed - sync_offset
        
        # Snap next pattern's warning_ms exactly to the beat
        time_until_next_beat = 0
        if self.beat_idx < len(self.beat_times):
            time_until_next_beat = self.beat_times[self.beat_idx] - true_elapsed
            
        # Guarantee beat synchronization
        warning_ms = max(400, min(1000, time_until_next_beat))
        
        idx = int(true_elapsed // 100)
        if idx < 0: idx = 0
        if idx >= len(self.intensity_curve): idx = len(self.intensity_curve) - 1
        
        global_intensity = self.intensity_curve[idx]
        
        # Fast-forward cluster index
        while self.cluster_idx < len(self.clusters) and self.clusters[self.cluster_idx][-1] < true_elapsed:
            self.cluster_idx += 1
            
        phrase_idx = self.beat_idx // 8
        ptype = self.theme_patterns[(self.cluster_idx + phrase_idx) % len(self.theme_patterns)]
        
        # Section-aware scheduling
        patterns_to_spawn = 1
        if global_intensity > 0.5: patterns_to_spawn = 2
        if global_intensity > 0.8: patterns_to_spawn = 3
        
        for _ in range(patterns_to_spawn):
            if ptype == 0:
                self.obstacles.append(FullScreenLaser(random.choice(['h', 'v']), random.uniform(0.1, 0.9), warning_ms))
            elif ptype == 1:
                self.obstacles.append(WallSlam(random.choice(['top', 'bottom', 'left', 'right']), 0.3, warning_ms))
            elif ptype == 2:
                self.obstacles.append(ParticleBurst(random.randint(100, SCREEN_WIDTH-100), random.randint(100, SCREEN_HEIGHT-100), int(12 + global_intensity * 10), 10, warning_ms))
            elif ptype == 3:
                num_pillars = int(1 + global_intensity * 3)
                pxs = [random.randint(100, SCREEN_WIDTH-100) for _ in range(num_pillars)]
                self.obstacles.append(PillarDrop(pxs, warning_ms))
            elif ptype == 4:
                self.obstacles.append(ShockwaveRing(random.randint(200, SCREEN_WIDTH-200), random.randint(200, SCREEN_HEIGHT-200), 1500, 15, 20, warning_ms))
"""
    
    script_path = os.path.join(song_dir, f"{base_name_clean}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(python_script)

    app.lm_status = "Registering executable Level Code..."
    app.lm_progress = 0.99
    
    if base_name_clean not in app.levels:
        app.levels.append(base_name_clean)
        if hasattr(app, 'item_offsets'): app.item_offsets.append(0.0)
    app.lm_last_song = base_name_clean
    SONGS[base_name_clean] = {
        "path": final_audio,
        "artist": "Dynamic Python Generator",
        "surf": None,
        "class": "DynamicLevel",
        "py_path": script_path,
        "bpm": float(song_bpm)
    }
    if os.path.exists(cover_path):
        try:
            surf = pygame.image.load(cover_path).convert()
            SONGS[base_name_clean]["surf"] = pygame.transform.scale(surf, (400, 400))
        except: pass
        
    app.lm_last_generated_name = base_name_clean
    
    gen_duration = time.time() - start_time
    try:
        avg_file = os.path.join(custom_dir, "average_gen_time.txt")
        times = []
        if os.path.exists(avg_file):
            with open(avg_file, "r") as f:
                times = [float(x) for x in f.read().split() if x]
        times.append(gen_duration)
        if len(times) > 10: times = times[-10:]
        with open(avg_file, "w") as f:
            f.write("\n".join(str(t) for t in times))
        app.avg_gen_time = sum(times) / len(times)
    except: pass

    app.lm_status = "Done! Level Compiled Successfully."
    app.lm_state = 2

if __name__ == "__main__":
    main()