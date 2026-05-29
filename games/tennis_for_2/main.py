import os
import sys
import pygame
import random
import traceback

# Fix working directory so imports work
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "utilities")
sys.path.insert(0, UTILS_DIR)
os.chdir(SCRIPT_DIR)

try:
    import crt_overlay
except ImportError:
    crt_overlay = None

# Colors
C_BG = (10, 20, 10)
C_PADDLE = (50, 255, 50)
C_BALL = (200, 255, 200)
C_NET = (30, 100, 30)
C_TEXT = (50, 255, 50)

# Controls
_BTN_START = 9
_HAT_UP    = (0, 1)
_HAT_DOWN  = (0, -1)

class GameState:
    START = 0
    PLAYING = 1
    GAMEOVER = 2

class TennisGame:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.paddle_w = 20
        self.paddle_h = 100
        self.ball_size = 15
        self.reset_game()

    def reset_game(self):
        self.p1_y = self.h // 2 - self.paddle_h // 2
        self.p2_y = self.h // 2 - self.paddle_h // 2
        self.p1_score = 0
        self.p2_score = 0
        self.reset_ball()
        
    def reset_ball(self, p1_scored=True):
        self.ball_x = self.w // 2 - self.ball_size // 2
        self.ball_y = self.h // 2 - self.ball_size // 2
        direction = 1 if p1_scored else -1
        self.ball_vx = 6 * direction
        self.ball_vy = random.choice([-4, -3, 3, 4])

    def update(self, p1_up, p1_down, p2_up, p2_down):
        speed = 8
        if p1_up: self.p1_y -= speed
        if p1_down: self.p1_y += speed
        if p2_up: self.p2_y -= speed
        if p2_down: self.p2_y += speed

        # Constrain paddles
        self.p1_y = max(0, min(self.h - self.paddle_h, self.p1_y))
        self.p2_y = max(0, min(self.h - self.paddle_h, self.p2_y))

        # Update ball
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Bounce off top/bottom
        if self.ball_y <= 0 or self.ball_y >= self.h - self.ball_size:
            self.ball_vy = -self.ball_vy
            
        # Paddle rects
        r_p1 = pygame.Rect(40, self.p1_y, self.paddle_w, self.paddle_h)
        r_p2 = pygame.Rect(self.w - 40 - self.paddle_w, self.p2_y, self.paddle_w, self.paddle_h)
        r_ball = pygame.Rect(self.ball_x, self.ball_y, self.ball_size, self.ball_size)

        # Bounce off paddles
        if self.ball_vx < 0 and r_ball.colliderect(r_p1):
            self.ball_vx = -self.ball_vx + 0.5
            self.ball_vy += (self.ball_y - self.p1_y - self.paddle_h/2) * 0.05
        elif self.ball_vx > 0 and r_ball.colliderect(r_p2):
            self.ball_vx = -self.ball_vx - 0.5
            self.ball_vy += (self.ball_y - self.p2_y - self.paddle_h/2) * 0.05

        # Scoring
        if self.ball_x < 0:
            self.p2_score += 1
            self.reset_ball(False)
        elif self.ball_x > self.w:
            self.p1_score += 1
            self.reset_ball(True)

    def draw(self, surf, font):
        surf.fill(C_BG)
        # Draw net
        for y in range(0, self.h, 40):
            pygame.draw.rect(surf, C_NET, (self.w // 2 - 5, y, 10, 20))
            
        # Draw paddles
        pygame.draw.rect(surf, C_PADDLE, (40, self.p1_y, self.paddle_w, self.paddle_h))
        pygame.draw.rect(surf, C_PADDLE, (self.w - 40 - self.paddle_w, self.p2_y, self.paddle_w, self.paddle_h))
        
        # Draw ball
        pygame.draw.rect(surf, C_BALL, (self.ball_x, self.ball_y, self.ball_size, self.ball_size))
        
        # Draw scores
        s1 = font.render(str(self.p1_score), True, C_TEXT)
        s2 = font.render(str(self.p2_score), True, C_TEXT)
        surf.blit(s1, (self.w // 4 - s1.get_width() // 2, 40))
        surf.blit(s2, (self.w * 3 // 4 - s2.get_width() // 2, 40))

def main():
    pygame.init()
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    screen = pygame.display.set_mode((sw, sh), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    
    # Internal resolution
    gw, gh = 1280, 720
    game_surf = pygame.Surface((gw, gh))
    
    # Fonts
    try:
        font = pygame.font.SysFont("monospace", 72, bold=True)
        small_font = pygame.font.SysFont("monospace", 36)
    except:
        font = pygame.font.Font(None, 80)
        small_font = pygame.font.Font(None, 40)
        
    clock = pygame.time.Clock()
    
    pygame.joystick.init()
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        joysticks.append(j)
        
    game = TennisGame(gw, gh)
    state = GameState.START
    
    running = True
    while running:
        p1_up = p1_down = p2_up = p2_down = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if state in (GameState.START, GameState.GAMEOVER):
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        state = GameState.PLAYING
                        game.reset_game()
                        
            if event.type == pygame.JOYBUTTONDOWN:
                if state in (GameState.START, GameState.GAMEOVER) and event.button == _BTN_START:
                    state = GameState.PLAYING
                    game.reset_game()

        # Input handling for continuous movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: p1_up = True
        if keys[pygame.K_s]: p1_down = True
        if keys[pygame.K_UP]: p2_up = True
        if keys[pygame.K_DOWN]: p2_down = True
        
        for j in joysticks:
            if j.get_numaxes() > 1:
                axis = j.get_axis(1)
                if axis < -0.5: p1_up = True
                if axis > 0.5: p1_down = True
            if j.get_numhats() > 0:
                hat = j.get_hat(0)
                if hat[1] == 1: p1_up = True
                if hat[1] == -1: p1_down = True

        if state == GameState.PLAYING:
            # Basic AI for player 2 if no input
            if not p2_up and not p2_down:
                if game.ball_y < game.p2_y + game.paddle_h // 2 - 20: p2_up = True
                elif game.ball_y > game.p2_y + game.paddle_h // 2 + 20: p2_down = True
            
            game.update(p1_up, p1_down, p2_up, p2_down)
            game.draw(game_surf, font)
            
            if game.p1_score >= 10 or game.p2_score >= 10:
                state = GameState.GAMEOVER
        
        elif state == GameState.START:
            game_surf.fill(C_BG)
            title = font.render("TENNIS FOR 2", True, C_TEXT)
            game_surf.blit(title, title.get_rect(center=(gw//2, gh//2 - 60)))
            prompt = small_font.render("PRESS START / SPACE TO PLAY", True, C_TEXT)
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                game_surf.blit(prompt, prompt.get_rect(center=(gw//2, gh//2 + 40)))
                
        elif state == GameState.GAMEOVER:
            game.draw(game_surf, font)
            overlay = pygame.Surface((gw, gh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            game_surf.blit(overlay, (0, 0))
            msg = "PLAYER 1 WINS!" if game.p1_score >= 10 else "PLAYER 2 WINS!"
            text = font.render(msg, True, C_TEXT)
            game_surf.blit(text, text.get_rect(center=(gw//2, gh//2 - 40)))
            prompt = small_font.render("PRESS START TO RESTART", True, C_TEXT)
            game_surf.blit(prompt, prompt.get_rect(center=(gw//2, gh//2 + 60)))

        ticks = pygame.time.get_ticks()
        if crt_overlay:
            crt_overlay.apply_crt(game_surf, ticks)

        # Scale and blit
        scale = min(sw / gw, sh / gh)
        nw, nh = int(gw * scale), int(gh * scale)
        scaled = pygame.transform.scale(game_surf, (nw, nh))
        
        screen.fill((0, 0, 0))
        screen.blit(scaled, ((sw - nw) // 2, (sh - nh) // 2))
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
