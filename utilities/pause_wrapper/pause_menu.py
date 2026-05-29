import pygame
import sys
import os

# ── Button constants ────────────────────────────────────────────────────────
BTN_X     = 0
BTN_A     = 1
BTN_BACK  = 6
BTN_START = 9

HAT_UP    = (0,  1)
HAT_DOWN  = (0, -1)

CONFIRM_BTNS = {BTN_X, BTN_A, BTN_START}
RESUME_BTNS  = {BTN_BACK}

def main():
    pygame.init()
    pygame.joystick.init()
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        joysticks.append(j)

    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    W, H = screen.get_size()
    clock = pygame.time.Clock()

    # Colors (Main Menu Style: Black BG, Neon Green/Cyan)
    C_BG = (5, 0, 0)
    C_NEON_GREEN = (57, 255, 20)
    C_CYAN = (0, 255, 255)
    C_BLACK = (0, 0, 0)
    C_DIM = (0, 100, 10)

    try:
        font_title = pygame.font.SysFont("monospace", int(H * 0.1), bold=True)
        font_item = pygame.font.SysFont("monospace", int(H * 0.05), bold=True)
        font_legend = pygame.font.SysFont("monospace", int(H * 0.025))
    except:
        font_title = pygame.font.Font(None, 80)
        font_item = pygame.font.Font(None, 50)
        font_legend = pygame.font.Font(None, 28)

    options = ["RESUME", "EXIT TO ARCADE"]
    selected = 0
    hat_debounce_ms = 200
    last_hat_time = 0

    running = True
    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    sys.exit(0)
                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(options) - 1, selected + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_x, pygame.K_z):
                    sys.exit(0 if selected == 0 else 1)
            
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONFIRM_BTNS:
                    sys.exit(0 if selected == 0 else 1)
                elif event.button in RESUME_BTNS:
                    sys.exit(0)
            
            if event.type == pygame.JOYHATMOTION:
                if now - last_hat_time > hat_debounce_ms:
                    if event.value[1] == 1:
                        selected = max(0, selected - 1)
                        last_hat_time = now
                    elif event.value[1] == -1:
                        selected = min(len(options) - 1, selected + 1)
                        last_hat_time = now

            if event.type == pygame.JOYAXISMOTION:
                if event.axis == 1 and now - last_hat_time > hat_debounce_ms:
                    if event.value < -0.5:
                        selected = max(0, selected - 1)
                        last_hat_time = now
                    elif event.value > 0.5:
                        selected = min(len(options) - 1, selected + 1)
                        last_hat_time = now

        # Draw
        screen.fill(C_BG)

        # CRT Scanlines
        scan_surf = pygame.Surface((W, 1), pygame.SRCALPHA)
        scan_surf.fill((0, 0, 0, 100))
        for y in range(0, H, 3):
            screen.blit(scan_surf, (0, y))

        # Title
        title_text = "SYSTEM PAUSED"
        # Glitch / Shadow effect
        if (now // 100) % 5 == 0:
            glow = font_title.render(title_text, True, C_CYAN)
            screen.blit(glow, glow.get_rect(center=(W // 2 + 4, H // 4)))
            glow2 = font_title.render(title_text, True, (255, 0, 255))
            screen.blit(glow2, glow2.get_rect(center=(W // 2 - 4, H // 4)))

        title = font_title.render(title_text, True, C_NEON_GREEN)
        screen.blit(title, title.get_rect(center=(W // 2, H // 4)))

        # Border frame
        frame_rect = pygame.Rect(W // 4, H // 2 - 50, W // 2, H // 3)
        pygame.draw.rect(screen, C_NEON_GREEN, frame_rect, 4)

        # Options
        for i, opt in enumerate(options):
            is_sel = (i == selected)
            color = C_NEON_GREEN if is_sel else C_DIM
            cy = H // 2 + i * int(H * 0.12)
            
            if is_sel:
                # Blinking cursor block
                if (now // 250) % 2 == 0:
                    cursor = font_item.render(">", True, C_NEON_GREEN)
                    screen.blit(cursor, (W // 2 - 180, cy - cursor.get_height() // 2))

            surf = font_item.render(opt, True, color)
            screen.blit(surf, surf.get_rect(center=(W // 2, cy)))

        # Controls legend
        legend = "HAT UP/DOWN: Move   X/START: Confirm   ESC/BACK: Resume"
        leg_surf = font_legend.render(legend, True, C_NEON_GREEN)
        screen.blit(leg_surf, leg_surf.get_rect(center=(W // 2, H - 40)))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
