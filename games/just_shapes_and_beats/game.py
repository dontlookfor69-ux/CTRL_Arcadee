import pygame
import random
import os
import sys

# --- Fix path for shared utilities ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "utilities")
sys.path.insert(0, UTILS_DIR)

try:
    import crt_overlay
except ImportError:
    crt_overlay = None

# --- Configuration ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60

# Palette
COLOR_BG = (10, 10, 25)
COLOR_PLAYER = (0, 255, 255)
COLOR_OBSTACLE = (255, 0, 100)
COLOR_TEXT = (255, 255, 255)
COLOR_HINT = (255, 0, 100, 100)

HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.txt")

class Player:
    def __init__(self):
        self.size = 30
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.speed = 8
        self.invulnerable = False
        self.dash_timer = 0
        self.dash_cooldown = 0

    def move(self, keys):
        """Original Keyboard Handling"""
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        
        move_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        move_y = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        
        speed = self.speed
        if keys[pygame.K_LSHIFT] and self.dash_cooldown == 0:
            self.dash_timer = 10
            self.dash_cooldown = 40
            self.invulnerable = True
            speed *= 4
            
        if self.dash_timer > 0:
            self.dash_timer -= 1
            if self.dash_timer == 0: self.invulnerable = False
            
        self.x += move_x * speed
        self.y += move_y * speed
        
        # Clamp
        self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
        self.y = max(self.size, min(SCREEN_HEIGHT - self.size, self.y))

    def move_joystick(self, move_x, move_y, dash_pressed):
        """Additive Joystick Support"""
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        
        speed = self.speed
        if dash_pressed and self.dash_cooldown == 0:
            self.dash_timer = 10
            self.dash_cooldown = 40
            self.invulnerable = True
            speed *= 4
            
        if self.dash_timer > 0:
            self.dash_timer -= 1
            if self.dash_timer == 0: self.invulnerable = False
            
        self.x += move_x * speed
        self.y += move_y * speed
        
        # Clamp
        self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
        self.y = max(self.size, min(SCREEN_HEIGHT - self.size, self.y))

    def draw(self, screen):
        color = COLOR_PLAYER if not self.invulnerable else (255, 255, 255)
        pygame.draw.rect(screen, color, (self.x - self.size//2, self.y - self.size//2, self.size, self.size))

class Obstacle:
    def __init__(self, score):
        self.reset(score)

    def reset(self, score):
        self.size = random.randint(40, 120)
        side = random.randint(0, 3)
        if side == 0: # Left
            self.x, self.y = -self.size, random.randint(0, SCREEN_HEIGHT)
            self.vx, self.vy = random.randint(3, 7), random.randint(-2, 2)
        elif side == 1: # Right
            self.x, self.y = SCREEN_WIDTH + self.size, random.randint(0, SCREEN_HEIGHT)
            self.vx, self.vy = random.randint(-7, -3), random.randint(-2, 2)
        elif side == 2: # Top
            self.x, self.y = random.randint(0, SCREEN_WIDTH), -self.size
            self.vx, self.vy = random.randint(-2, 2), random.randint(3, 7)
        else: # Bottom
            self.x, self.y = random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + self.size
            self.vx, self.vy = random.randint(-2, 2), random.randint(-7, -3)
        
        speed_scale = 1.0 + min(score / 100.0, 2.0)
        self.vx *= speed_scale
        self.vy *= speed_scale
        self.warning = 60

    def update(self):
        if self.warning > 0:
            self.warning -= 1
            return True
        self.x += self.vx
        self.y += self.vy
        return -200 < self.x < SCREEN_WIDTH+200 and -200 < self.y < SCREEN_HEIGHT+200

    def draw(self, screen):
        if self.warning > 0:
            if (self.warning // 10) % 2 == 0:
                end_x = self.x + self.vx * 100
                end_y = self.y + self.vy * 100
                pygame.draw.line(screen, (50, 0, 20), (self.x, self.y), (end_x, end_y), 2)
            return
        pygame.draw.rect(screen, COLOR_OBSTACLE, (self.x - self.size//2, self.y - self.size//2, self.size, self.size))

    def check_collision(self, player):
        if self.warning > 0 or player.invulnerable: return False
        dx = player.x - self.x
        dy = player.y - self.y
        dist_sq = dx*dx + dy*dy
        combined_radius = (self.size * 0.7 + player.size * 0.7)
        return dist_sq < combined_radius * combined_radius

def load_highscore():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f: return int(f.read().strip())
        except: return 0
    return 0

def save_highscore(score):
    if score > load_highscore():
        with open(HIGHSCORE_FILE, "w") as f: f.write(str(score))

def main():
    pygame.init()
    
    # Joystick setup
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks: j.init()
    
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    font_large = pygame.font.SysFont("monospace", 72, bold=True)
    font_small = pygame.font.SysFont("monospace", 36)
    
    player = Player()
    obstacles = []
    score = 0
    highscore = load_highscore()
    game_over = False
    
    running = True
    while running:
        screen.fill(COLOR_BG)
        keys = pygame.key.get_pressed()
        
        # 1. Original Movement
        player.move(keys)
        
        # 2. Additive Joystick Movement
        for j in joysticks:
            if j.get_numaxes() >= 2:
                jx = j.get_axis(0)
                jy = j.get_axis(1)
                if abs(jx) > 0.2 or abs(jy) > 0.2:
                    # Map buttons for dash
                    dash = any(j.get_button(b) for b in range(min(j.get_numbuttons(), 4)))
                    player.move_joystick(jx if abs(jx) > 0.2 else 0, jy if abs(jy) > 0.2 else 0, dash)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if game_over and event.key == pygame.K_r:
                    player = Player(); obstacles = []; score = 0; game_over = False; highscore = load_highscore()
            if event.type == pygame.JOYBUTTONDOWN and game_over:
                player = Player(); obstacles = []; score = 0; game_over = False; highscore = load_highscore()

        if not game_over:
            obstacles = [o for o in obstacles if -300 < o.x < SCREEN_WIDTH+300 and -300 < o.y < SCREEN_HEIGHT+300]
            if len(obstacles) < 25 and random.random() < 0.05:
                obstacles.append(Obstacle(score))
            for o in obstacles:
                o.update()
                if o.check_collision(player):
                    game_over = True
                    save_highscore(int(score))
            score += 1/60.0
            
        for o in obstacles: o.draw(screen)
        player.draw(screen)
        
        # CRT Overlay
        if crt_overlay:
            crt_overlay.apply_crt(screen, pygame.time.get_ticks())
        
        score_text = font_small.render(f"SCORE: {int(score)}", True, COLOR_TEXT)
        screen.blit(score_text, (20, 20))
        hs_text = font_small.render(f"BEST: {highscore}", True, (100, 100, 100))
        screen.blit(hs_text, (20, 60))
        
        if game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0,0))
            msg = font_large.render("GAME OVER", True, COLOR_OBSTACLE)
            screen.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, SCREEN_HEIGHT//2 - 100))
            retry = font_small.render("PRESS 'R' TO RESTART", True, COLOR_PLAYER)
            screen.blit(retry, (SCREEN_WIDTH//2 - retry.get_width()//2, SCREEN_HEIGHT//2 + 60))
            
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
