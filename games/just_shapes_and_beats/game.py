import pygame
import random
import math
import sys
import os

# --- Robust Pathing ---
_DIR = os.path.dirname(os.path.abspath(__file__))
def get_path(rel): return os.path.join(_DIR, rel)

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Game Constants
BPM = 128
BEAT_INTERVAL = (60 / BPM) * 1000
DASH_COOLDOWN = 600
DASH_DURATION = 150
DASH_DISTANCE = 120
INVULNERABILITY_TIME = 200
MAX_HEALTH = 100

# Screen Setup
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Just Shapes & Beats Arcade")
clock = pygame.time.Clock()

# Colors
BG_COLOR = (5, 5, 5)
PLAYER1_COLOR = (0, 255, 255)
PLAYER2_COLOR = (255, 255, 0)
ENEMY_COLOR = (255, 0, 102)
UI_TEXT_COLOR = (255, 255, 255)

# Fonts
try:
    font_large = pygame.font.SysFont('Arial', 80, bold=True)
    font_medium = pygame.font.SysFont('Arial', 40, bold=True)
    font_small = pygame.font.SysFont('Arial', 24)
except:
    font_large = pygame.font.Font(None, 120)
    font_medium = pygame.font.Font(None, 60)
    font_small = pygame.font.Font(None, 30)

# Audio Setup
bgm_path = get_path(os.path.join('Audio', 'CLOSE TO ME.mp3'))
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    print(f"[JSB] Loaded music: {bgm_path}")
else:
    print(f"[JSB] ERROR: Audio file not found at {bgm_path}")

# Game State
class GameState:
    START = 0
    PLAYING = 1
    GAMEOVER = 2

state = GameState.START
is_two_player = False
score = 0
health = MAX_HEALTH
last_beat_time = 0
shake_amount = 0
obstacles = []
particles = []

class Player:
    def __init__(self, id, color, shape):
        self.id = id
        self.color = color
        self.shape = shape
        self.size = 25
        self.reset()

    def reset(self):
        if self.id == 1:
            self.x = SCREEN_WIDTH / 2 - (50 if is_two_player else 0)
        else:
            self.x = SCREEN_WIDTH / 2 + 50
        self.y = SCREEN_HEIGHT / 2
        self.speed = 8
        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.invulnerable = False
        self.invuln_timer = 0
        self.trail = []

    def update(self, dt):
        if self.dash_cooldown > 0: self.dash_cooldown -= dt
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
            if self.invuln_timer <= 0: self.invulnerable = False

        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0: self.is_dashing = False
            self.trail.append({'x': self.x, 'y': self.y, 'opacity': 1.0})
        else:
            dx, dy = 0, 0
            keys = pygame.key.get_pressed()
            dash_key = False
            if self.id == 1:
                if keys[pygame.K_w]: dy -= 1
                if keys[pygame.K_s]: dy += 1
                if keys[pygame.K_a]: dx -= 1
                if keys[pygame.K_d]: dx += 1
                dash_key = keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT]
            else:
                if keys[pygame.K_UP]: dy -= 1
                if keys[pygame.K_DOWN]: dy += 1
                if keys[pygame.K_LEFT]: dx -= 1
                if keys[pygame.K_RIGHT]: dx += 1
                dash_key = keys[pygame.K_RETURN] or keys[pygame.K_RSHIFT]
            if dx != 0 or dy != 0:
                mag = math.sqrt(dx*dx + dy*dy)
                self.x += (dx / mag) * self.speed
                self.y += (dy / mag) * self.speed
            if dash_key and self.dash_cooldown <= 0:
                self.dash(dx, dy)
        self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
        self.y = max(self.size, min(SCREEN_HEIGHT - self.size, self.y))
        for t in self.trail: t['opacity'] -= 0.05
        self.trail = [t for t in self.trail if t['opacity'] > 0]

    def dash(self, dx, dy):
        global shake_amount
        if dx == 0 and dy == 0: dx = -1 if self.id == 1 else 1
        mag = math.sqrt(dx*dx + dy*dy)
        self.x += (dx / mag) * DASH_DISTANCE
        self.y += (dy / mag) * DASH_DISTANCE
        self.is_dashing = True; self.invulnerable = True
        self.dash_timer = DASH_DURATION; self.dash_cooldown = DASH_COOLDOWN
        self.invuln_timer = INVULNERABILITY_TIME; shake_amount = 10

    def draw(self, surface):
        for t in self.trail:
            alpha = int(t['opacity'] * 128)
            ts = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            c = (*self.color, alpha)
            if self.shape == 'square': pygame.draw.rect(ts, c, (0, 0, self.size, self.size))
            else: pygame.draw.polygon(ts, c, [(self.size/2, 0), (self.size, self.size), (0, self.size)])
            surface.blit(ts, (t['x'] - self.size/2, t['y'] - self.size/2))
        if self.invulnerable and (pygame.time.get_ticks() // 50) % 2 == 0: return
        if self.shape == 'square': pygame.draw.rect(surface, self.color, (self.x - self.size/2, self.y - self.size/2, self.size, self.size))
        else: pygame.draw.polygon(surface, self.color, [(self.x, self.y - self.size/2), (self.x + self.size/2, self.y + self.size/2), (self.x - self.size/2, self.y + self.size/2)])

class Obstacle:
    def __init__(self): self.reset()
    def reset(self):
        side = random.randint(0, 3)
        if side == 0: self.x, self.y = -100, random.randint(0, SCREEN_HEIGHT); self.vx, self.vy = random.uniform(3, 8), 0
        elif side == 1: self.x, self.y = SCREEN_WIDTH + 100, random.randint(0, SCREEN_HEIGHT); self.vx, self.vy = -random.uniform(3, 8), 0
        elif side == 2: self.x, self.y = random.randint(0, SCREEN_WIDTH), -100; self.vx, self.vy = 0, random.uniform(3, 8)
        else: self.x, self.y = random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 100; self.vx, self.vy = 0, -random.uniform(3, 8)
        self.size = random.uniform(40, 80); self.angle = random.uniform(0, math.pi * 2)
        self.rotation_speed = random.uniform(-0.05, 0.05); self.warning = 800

    def update(self, dt):
        self.x += self.vx; self.y += self.vy; self.angle += self.rotation_speed
        if self.warning > 0: self.warning -= dt

    def draw(self, surface, current_time, last_beat):
        is_dangerous = self.warning <= 0
        color = ENEMY_COLOR if is_dangerous else (*ENEMY_COLOR, 50)
        pulse = math.sin((current_time - last_beat) / 100.0) * 8
        ds = self.size + (pulse if is_dangerous else 0)
        obs_surf = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
        pygame.draw.rect(obs_surf, color, (ds/2, ds/2, ds, ds))
        if is_dangerous: pygame.draw.rect(obs_surf, (255, 255, 255), (ds/2, ds/2, ds, ds), 2)
        rotated_surf = pygame.transform.rotate(obs_surf, math.degrees(self.angle))
        rect = rotated_surf.get_rect(center=(self.x, self.y))
        surface.blit(rotated_surf, rect.topleft)

    def check_collision(self, player):
        if self.warning > 0 or player.invulnerable: return False
        dx = abs(player.x - self.x); dy = abs(player.y - self.y)
        combined_size = (self.size + player.size) / 2
        return dx < combined_size and dy < combined_size

player1 = Player(1, PLAYER1_COLOR, 'square')
player2 = Player(2, PLAYER2_COLOR, 'triangle')
active_players = [player1]

def start_game():
    global state, health, score, obstacles, active_players, last_beat_time
    state = GameState.PLAYING; health = MAX_HEALTH; score = 0; obstacles = []
    player1.reset()
    active_players = [player1]
    if is_two_player: player2.reset(); active_players.append(player2)
    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
    try: pygame.mixer.music.play(-1)
    except: print("[JSB] Music Error")
    last_beat_time = pygame.time.get_ticks()

def game_over():
    global state
    state = GameState.GAMEOVER; pygame.mixer.music.stop()

def draw_ui(surface):
    bw, bh = 400, 20
    pygame.draw.rect(surface, (50, 50, 50), (40, 40, bw, bh))
    curr_bw = (max(0, health) / MAX_HEALTH) * bw
    if health > 0: pygame.draw.rect(surface, PLAYER1_COLOR, (40, 40, curr_bw, bh))
    pygame.draw.rect(surface, (255, 255, 255), (40, 40, bw, bh), 2)
    score_text = font_medium.render(f"SCORE: {int(score)}", True, UI_TEXT_COLOR)
    surface.blit(score_text, (40, 80))

    if state == GameState.START:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)); surface.blit(overlay, (0, 0))
        t1 = font_large.render("JUST SHAPES", True, PLAYER1_COLOR)
        t2 = font_large.render("& BEATS", True, PLAYER1_COLOR)
        surface.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2, SCREEN_HEIGHT//2 - 150))
        surface.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, SCREEN_HEIGHT//2 - 50))
        st = font_small.render("1 OR 2 PLAYER MODE | PRESS KEY TO START", True, UI_TEXT_COLOR)
        surface.blit(st, (SCREEN_WIDTH//2 - st.get_width()//2, SCREEN_HEIGHT//2 + 100))
    elif state == GameState.GAMEOVER:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)); surface.blit(overlay, (0, 0))
        go = font_large.render("GAME OVER", True, ENEMY_COLOR)
        surface.blit(go, (SCREEN_WIDTH//2 - go.get_width()//2, SCREEN_HEIGHT//2 - 50))
        st = font_medium.render(f"FINAL SCORE: {int(score)}", True, UI_TEXT_COLOR)
        surface.blit(st, (SCREEN_WIDTH//2 - st.get_width()//2, SCREEN_HEIGHT//2 + 50))

running = True
while running:
    current_time = pygame.time.get_ticks()
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if state in [GameState.START, GameState.GAMEOVER]:
                if event.key == pygame.K_1: is_two_player = False; start_game()
                elif event.key == pygame.K_2: is_two_player = True; start_game()
                else: start_game()
    if state == GameState.PLAYING:
        if current_time - last_beat_time > BEAT_INTERVAL:
            last_beat_time = current_time
            if len(obstacles) < 25: obstacles.append(Obstacle())
            shake_amount = 5
        for p in active_players: p.update(dt)
        score += dt / 1000.0
        for obs in obstacles[:]:
            obs.update(dt)
            for p in active_players:
                if obs.check_collision(p):
                    health -= 15; shake_amount = 20; p.invulnerable = True; p.invuln_timer = 1000
                    if obs in obstacles: obstacles.remove(obs)
                    if health <= 0: game_over()
            if obs.x < -300 or obs.x > SCREEN_WIDTH + 300 or obs.y < -300 or obs.y > SCREEN_HEIGHT + 300:
                if obs in obstacles: obstacles.remove(obs)
    bg_pulse = max(0, 1 - (current_time - last_beat_time) / (BEAT_INTERVAL / 2))
    bv = int(bg_pulse * 15); screen.fill((bv, bv//3, bv))
    ro = [0, 0]
    if shake_amount > 0:
        ro = [random.uniform(-shake_amount, shake_amount), random.uniform(-shake_amount, shake_amount)]
        shake_amount *= 0.9
    grid_size = 80
    for x in range(0, SCREEN_WIDTH, grid_size): pygame.draw.line(screen, (20, 20, 20), (x + ro[0], 0), (x + ro[0], SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, grid_size): pygame.draw.line(screen, (20, 20, 20), (0, y + ro[1]), (SCREEN_WIDTH, y + ro[1]))
    for obs in obstacles: obs.draw(screen, current_time, last_beat_time)
    for p in active_players: p.draw(screen)
    draw_ui(screen)
    pygame.display.flip()
pygame.quit()
sys.exit()
