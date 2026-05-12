import pygame
import sys

def main():
    pygame.init()
    
    # Initialize joystick if available
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
        
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = screen.get_size()
    
    clock = pygame.time.Clock()
    
    try:
        font_title = pygame.font.SysFont("arial", int(HEIGHT * 0.1), bold=True)
        font_item = pygame.font.SysFont("arial", int(HEIGHT * 0.05), bold=True)
    except:
        font_title = pygame.font.Font(None, 80)
        font_item = pygame.font.Font(None, 50)
        
    options = ["RESUME", "EXIT TO ARCADE"]
    selected = 0
    
    # Cohesive Arcade Theme Colors
    C_BG     = (10, 10, 30)   # Deep navy
    C_CYAN   = (0, 230, 255)  # Cyan
    C_MAG    = (255, 0, 255)  # Magenta
    C_WHITE  = (220, 220, 255)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
                
            # Keyboard navigation
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    sys.exit(0)
                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(options) - 1, selected + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_x, pygame.K_z):
                    if selected == 0: sys.exit(0)
                    else: sys.exit(1)
            
            # Joystick navigation (Arcade buttons/sticks)
            if event.type == pygame.JOYBUTTONDOWN:
                # Typically button 0 or 1 is select
                if event.button in (0, 1, 2):
                    if selected == 0: sys.exit(0)
                    else: sys.exit(1)
            
            if event.type == pygame.JOYAXISMOTION:
                # Handle d-pad or stick axis 1 (vertical)
                if event.axis == 1:
                    if event.value < -0.5: # Up
                        selected = max(0, selected - 1)
                    elif event.value > 0.5: # Down
                        selected = min(len(options) - 1, selected + 1)
            
            if event.type == pygame.JOYHATMOTION:
                # Handle d-pad (hat)
                if event.value[1] == 1: # Up
                    selected = max(0, selected - 1)
                elif event.value[1] == -1: # Down
                    selected = min(len(options) - 1, selected + 1)
                        
        screen.fill(C_BG)
        
        # Draw tech-grid background
        for x in range(0, WIDTH, 40):
            pygame.draw.line(screen, (20, 20, 60), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(screen, (20, 20, 60), (0, y), (WIDTH, y))
            
        # Subtle scanlines
        for y in range(0, HEIGHT, 4):
            s = pygame.Surface((WIDTH, 1))
            s.set_alpha(30)
            s.fill((0, 0, 0))
            screen.blit(s, (0, y))
            
        # Draw Title with Glow
        title_text = "SYSTEM PAUSED"
        for offset in range(3, 0, -1):
            glow = font_title.render(title_text, True, (60, 0, 60))
            screen.blit(glow, glow.get_rect(center=(WIDTH//2 + offset, HEIGHT//3 + offset)))
            
        title = font_title.render(title_text, True, C_MAG)
        screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//3)))
        
        # Draw border frame
        pygame.draw.rect(screen, C_CYAN, (WIDTH//4, HEIGHT//4, WIDTH//2, HEIGHT//2), 4, border_radius=10)
        
        for i, opt in enumerate(options):
            is_sel = (i == selected)
            color = C_CYAN if is_sel else C_WHITE
            
            if is_sel:
                bar_rect = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + i * 100 - 40, 500, 80)
                pygame.draw.rect(screen, (0, 40, 60), bar_rect, border_radius=5)
                pygame.draw.rect(screen, C_CYAN, bar_rect, 2, border_radius=5)
                
            text = f"▶ {opt} ◀" if is_sel else opt
            surface = font_item.render(text, True, color)
            screen.blit(surface, surface.get_rect(center=(WIDTH//2, HEIGHT//2 + i * 100)))
            
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
