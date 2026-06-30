import pygame
import sys
import os
import random
import json
from PIL import Image, ImageSequence

# Pygame Initialization
pygame.init()
try:
    pygame.mixer.init()
except:
    pass
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
for joystick in joysticks:
    joystick.init()

# Constants
WIDTH, HEIGHT = 400, 600
FPS = 60
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_SPEED = 3
PIPE_SPAWN_TIME = 1500 # ms
PIPE_GAP = 150

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
BLUE = (135, 206, 235)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)

# Setup Display
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

# Fonts
font_large = pygame.font.SysFont("impact", 48)
font_medium = pygame.font.SysFont("impact", 32)
font_small = pygame.font.SysFont("impact", 24)

# Paths
MEDIA_DIR = "media"
HIGHSCORE_FILE = "highscores.json"

# Load Assets
def load_image(filename, scale=None):
    path = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(path):
        # Create a placeholder if not exists
        surf = pygame.Surface((40, 40))
        surf.fill(RED)
        return surf
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        return img
    except:
        surf = pygame.Surface((40, 40))
        surf.fill(RED)
        return surf

def load_sound(filename):
    path = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        return pygame.mixer.Sound(path)
    except:
        return None

# Load GIF frames
def load_gif_frames(filename, size=None):
    path = os.path.join(MEDIA_DIR, filename)
    frames = []
    if not os.path.exists(path):
        return frames
    try:
        pil_img = Image.open(path)
        for frame in ImageSequence.Iterator(pil_img):
            frame_rgba = frame.convert("RGBA")
            mode = frame_rgba.mode
            size_pil = frame_rgba.size
            data = frame_rgba.tobytes()
            pygame_surf = pygame.image.fromstring(data, size_pil, mode)
            if size:
                pygame_surf = pygame.transform.scale(pygame_surf, size)
            frames.append(pygame_surf)
    except Exception as e:
        print(f"Error loading GIF: {e}")
    return frames

# Assets
bg_img = load_image("new-york-city-panorama_10.jpg")
if bg_img.get_width() > 0:
    # Scale background height to screen height, maintain aspect ratio
    aspect = bg_img.get_width() / bg_img.get_height()
    bg_img = pygame.transform.scale(bg_img, (int(HEIGHT * aspect), HEIGHT))

skin_1 = load_image("flappybird.jpg", (40, 40))
skin_2 = load_image("its poco.png", (40, 40))
skin_3 = load_image("plane.png", (50, 30))
skins = [skin_1, skin_2, skin_3]
skin_names = ["Flappy Bird", "Poco", "Plane"]

rare_object_img = load_image("rare object.webp", (40, 40))
explosion_frames = load_gif_frames("explosion.gif", (WIDTH, HEIGHT))

dead_sound = load_sound("dead.mp3")
rare_dead_sound = load_sound("rare death sound.mp3")

# Global State
current_state = "MENU"
current_skin_idx = 0
score = 0
highscores = []

# Load Highscores
def load_highscores():
    global highscores
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                highscores = json.load(f)
        except:
            highscores = []
    else:
        highscores = []
    # Ensure it's sorted
    highscores.sort(key=lambda x: x['score'], reverse=True)
    highscores = highscores[:10]

def save_highscores():
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(highscores, f)

load_highscores()

class Bird:
    def __init__(self):
        self.x = 50
        self.y = HEIGHT // 2
        self.velocity = 0
        self.rect = pygame.Rect(self.x, self.y, skins[current_skin_idx].get_width(), skins[current_skin_idx].get_height())
    
    def flap(self):
        self.velocity = FLAP_STRENGTH
    
    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity
        img = skins[current_skin_idx]
        self.rect.width = img.get_width()
        self.rect.height = img.get_height()
        self.rect.y = int(self.y)
    
    def draw(self, surface):
        img = skins[current_skin_idx]
        # Rotate bird based on velocity
        angle = -self.velocity * 3
        angle = max(-90, min(angle, 45))
        rotated = pygame.transform.rotate(img, angle)
        # Center the rotation
        new_rect = rotated.get_rect(center=self.rect.center)
        surface.blit(rotated, new_rect.topleft)

class Pipe:
    def __init__(self, x, is_rare=False):
        self.x = x
        self.is_rare = is_rare
        self.passed = False
        self.width = 60
        
        if self.is_rare:
            self.y = random.randint(100, HEIGHT - 100)
            self.rect = pygame.Rect(self.x, self.y, rare_object_img.get_width(), rare_object_img.get_height())
            self.top_rect = None
            self.bottom_rect = None
        else:
            self.gap_y = random.randint(100, HEIGHT - 100 - PIPE_GAP)
            self.top_rect = pygame.Rect(self.x, 0, self.width, self.gap_y)
            self.bottom_rect = pygame.Rect(self.x, self.gap_y + PIPE_GAP, self.width, HEIGHT - (self.gap_y + PIPE_GAP))
            self.rect = None
            
    def update(self):
        self.x -= PIPE_SPEED
        if self.is_rare:
            self.rect.x = self.x
        else:
            self.top_rect.x = self.x
            self.bottom_rect.x = self.x

    def draw(self, surface):
        if self.is_rare:
            surface.blit(rare_object_img, self.rect.topleft)
        else:
            pygame.draw.rect(surface, GREEN, self.top_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.top_rect, 3) # Border
            pygame.draw.rect(surface, GREEN, self.bottom_rect)
            pygame.draw.rect(surface, DARK_GREEN, self.bottom_rect, 3)

class Background:
    def __init__(self):
        self.x1 = 0
        self.x2 = bg_img.get_width()
    
    def update(self):
        self.x1 -= 1
        self.x2 -= 1
        if self.x1 <= -bg_img.get_width():
            self.x1 = self.x2 + bg_img.get_width()
        if self.x2 <= -bg_img.get_width():
            self.x2 = self.x1 + bg_img.get_width()
            
    def draw(self, surface):
        surface.blit(bg_img, (self.x1, 0))
        surface.blit(bg_img, (self.x2, 0))

def check_collision(bird, pipes):
    if bird.y < 0 or bird.y + bird.rect.height > HEIGHT:
        return True, False # Normal collision
    
    for pipe in pipes:
        if pipe.is_rare:
            if bird.rect.colliderect(pipe.rect):
                return True, True # Rare collision
        else:
            if bird.rect.colliderect(pipe.top_rect) or bird.rect.colliderect(pipe.bottom_rect):
                return True, False
    return False, False

def draw_text(surface, text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# Variables for game state
bird = None
pipes = []
background = Background()
last_pipe_time = 0
explosion_frame_idx = 0
explosion_timer = 0
keyboard_grid = [
    ['A','B','C','D','E','F','G'],
    ['H','I','J','K','L','M','N'],
    ['O','P','Q','R','S','T','U'],
    ['V','W','X','Y','Z','DEL','OK']
]
kbd_x, kbd_y = 0, 0
entered_name = ""

def reset_game():
    global bird, pipes, score, last_pipe_time, current_state
    bird = Bird()
    pipes = []
    score = 0
    last_pipe_time = pygame.time.get_ticks()
    current_state = "PLAYING"

def handle_game_over(is_rare):
    global current_state, explosion_frame_idx, explosion_timer, kbd_x, kbd_y, entered_name
    
    if is_rare:
        if rare_dead_sound:
            rare_dead_sound.play()
        current_state = "RARE_DEATH"
        explosion_frame_idx = 0
        explosion_timer = pygame.time.get_ticks()
    else:
        if dead_sound:
            dead_sound.play()
        current_state = "NORMAL_DEATH"
    
    # Check highscore
    is_highscore = False
    if len(highscores) < 10 or score > highscores[-1]['score']:
        is_highscore = True
        
    # We'll transition to KEYBOARD or MENU after a delay or click
    return is_highscore

is_new_highscore = False

# Main Loop
running = True
while running:
    dt = clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        is_action = False
        is_right = False
        is_left = False
        is_up = False
        is_down = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                is_action = True
            elif event.key == pygame.K_RIGHT:
                is_right = True
            elif event.key == pygame.K_LEFT:
                is_left = True
            elif event.key == pygame.K_UP:
                is_up = True
            elif event.key == pygame.K_DOWN:
                is_down = True
                
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 6: # BACK
                running = False
            elif event.button in (0, 1, 2, 3, 7, 9): # X, A, B, Y, C, START
                is_action = True
        
        if event.type == pygame.JOYHATMOTION:
            if event.value[0] == 1:
                is_right = True
            elif event.value[0] == -1:
                is_left = True
            if event.value[1] == 1:
                is_up = True
            elif event.value[1] == -1:
                is_down = True

        if is_action or is_right or is_left or is_up or is_down or (event.type == pygame.KEYDOWN and event.key == pygame.K_l):
            if current_state == "MENU":
                if is_action:
                    reset_game()
                    current_skin_idx = (current_skin_idx + 1) % len(skins)
                elif is_left:
                    current_skin_idx = (current_skin_idx - 1) % len(skins)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                    current_state = "LEADERBOARD"
                    
            elif current_state == "PLAYING":
                if is_action:
                    bird.flap()
                    
            elif current_state in ("NORMAL_DEATH", "RARE_DEATH"):
                if is_action:
                    if is_new_highscore:
                        current_state = "KEYBOARD"
                        entered_name = ""
                        kbd_x, kbd_y = 0, 0
                    else:
                        current_state = "MENU"
                        
            elif current_state == "LEADERBOARD":
                if is_action:
                    current_state = "MENU"
                    
            elif current_state == "KEYBOARD":
                if is_up:
                    kbd_y = max(0, kbd_y - 1)
                elif is_down:
                    kbd_y = min(len(keyboard_grid)-1, kbd_y + 1)
                elif is_left:
                    kbd_x = max(0, kbd_x - 1)
                elif is_right:
                    kbd_x = min(len(keyboard_grid[0])-1, kbd_x + 1)
                elif is_action:
                    char = keyboard_grid[kbd_y][kbd_x]
                    if char == 'DEL':
                        entered_name = entered_name[:-1]
                    elif char == 'OK':
                        # Submit
                        highscores.append({"name": entered_name if entered_name else "AAA", "score": score})
                        highscores.sort(key=lambda x: x['score'], reverse=True)
                        highscores = highscores[:10]
                        save_highscores()
                        current_state = "LEADERBOARD"
                        is_new_highscore = False
                    else:
                        if len(entered_name) < 10:
                            entered_name += char

    # Update Logic
    if current_state == "PLAYING":
        background.update()
        bird.update()
        
        # Spawn pipes
        now = pygame.time.get_ticks()
        if now - last_pipe_time > PIPE_SPAWN_TIME:
            is_rare = random.randint(1, 100) == 1
            pipes.append(Pipe(WIDTH, is_rare))
            last_pipe_time = now
            
        for pipe in pipes:
            pipe.update()
            if pipe.x + pipe.width < bird.x and not pipe.passed:
                pipe.passed = True
                score += 1
                
        pipes = [p for p in pipes if p.x + p.width > 0]
        
        collided, rare_collision = check_collision(bird, pipes)
        if collided:
            is_new_highscore = handle_game_over(rare_collision)

    # Draw
    screen.fill(BLACK)
    
    if current_state in ("MENU", "LEADERBOARD"):
        background.draw(screen)
        
        if current_state == "MENU":
            # Title
            draw_text(screen, "FLAPPY BIRD", font_large, YELLOW, WIDTH//2, HEIGHT//4, True)
            draw_text(screen, "Press SPACE to Start", font_medium, WHITE, WIDTH//2, HEIGHT//2, True)
            
            # Skin selection
            draw_text(screen, "Skin: " + skin_names[current_skin_idx], font_small, WHITE, WIDTH//2, HEIGHT//2 + 60, True)
            screen.blit(skins[current_skin_idx], (WIDTH//2 - skins[current_skin_idx].get_width()//2, HEIGHT//2 + 90))
            draw_text(screen, "< Left/Right > to change", font_small, WHITE, WIDTH//2, HEIGHT//2 + 150, True)
            
            draw_text(screen, "Press L for Leaderboard", font_small, WHITE, WIDTH//2, HEIGHT - 50, True)
            
        elif current_state == "LEADERBOARD":
            draw_text(screen, "TOP 10 SCORES", font_large, YELLOW, WIDTH//2, 50, True)
            for i, hs in enumerate(highscores):
                text = f"{i+1}. {hs['name']} - {hs['score']}"
                draw_text(screen, text, font_medium, WHITE, WIDTH//2, 120 + i*40, True)
            draw_text(screen, "Press SPACE to return", font_small, WHITE, WIDTH//2, HEIGHT - 50, True)

    elif current_state == "PLAYING":
        background.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, str(score), font_large, WHITE, WIDTH//2, 50, True)
        
    elif current_state == "NORMAL_DEATH":
        background.draw(screen)
        for pipe in pipes:
            pipe.draw(screen)
        bird.draw(screen)
        draw_text(screen, "GAME OVER", font_large, RED, WIDTH//2, HEIGHT//3, True)
        draw_text(screen, f"Score: {score}", font_medium, WHITE, WIDTH//2, HEIGHT//2, True)
        if is_new_highscore:
            draw_text(screen, "NEW HIGHSCORE!", font_medium, YELLOW, WIDTH//2, HEIGHT//2 + 40, True)
        draw_text(screen, "Press SPACE to continue", font_small, WHITE, WIDTH//2, HEIGHT//2 + 100, True)

    elif current_state == "RARE_DEATH":
        # Draw explosion gif
        if explosion_frames:
            now = pygame.time.get_ticks()
            if now - explosion_timer > 100: # 10fps
                explosion_frame_idx = (explosion_frame_idx + 1) % len(explosion_frames)
                explosion_timer = now
            screen.blit(explosion_frames[explosion_frame_idx], (0, 0))
        else:
            screen.fill(RED)
            draw_text(screen, "BOOM!", font_large, YELLOW, WIDTH//2, HEIGHT//2, True)
            
        draw_text(screen, "YOU HIT THE RARE OBJECT!", font_medium, WHITE, WIDTH//2, 50, True)
        if is_new_highscore:
            draw_text(screen, "NEW HIGHSCORE!", font_medium, YELLOW, WIDTH//2, HEIGHT - 100, True)
        draw_text(screen, "Press SPACE to continue", font_small, WHITE, WIDTH//2, HEIGHT - 50, True)

    elif current_state == "KEYBOARD":
        background.draw(screen)
        draw_text(screen, "NEW HIGHSCORE!", font_large, YELLOW, WIDTH//2, 50, True)
        draw_text(screen, f"Name: {entered_name}", font_medium, WHITE, WIDTH//2, 120, True)
        
        # Draw keyboard
        start_y = 350
        cell_w, cell_h = 70, 50
        start_x = WIDTH//2 - (len(keyboard_grid[0]) * cell_w) // 2
        
        for r, row in enumerate(keyboard_grid):
            for c, char in enumerate(row):
                x = start_x + c * cell_w
                y = start_y + r * cell_h
                color = YELLOW if r == kbd_y and c == kbd_x else WHITE
                draw_text(screen, char, font_medium, color, x + cell_w//2, y + cell_h//2, True)
                if r == kbd_y and c == kbd_x:
                    pygame.draw.rect(screen, YELLOW, (x, y, cell_w, cell_h), 2)

    pygame.display.flip()

pygame.quit()
sys.exit()
