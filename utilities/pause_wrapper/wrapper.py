#!/usr/bin/python3
import subprocess
import sys
import os
import signal
import time
import threading
import pygame
import shlex

# Pure Retro Palette
C_BG = (5, 5, 10)
C_BORDER = (0, 255, 150)
C_LIME = (0, 255, 0)
C_WHITE = (255, 255, 255)

READY_FLAG = "/tmp/arcade_ready"

class ArcadeWrapper:
    def __init__(self, command):
        self.command = command
        self.process = None
        self.is_paused = False
        self.running = True
        
        pygame.init()
        self.font_lg = pygame.font.SysFont("monospace", 70, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 35, bold=True)
        
    def log(self, msg):
        print(f"[WRAPPER DEBUG] {msg}", flush=True)

    def launch(self):
        self.log(f"INITIATING: {self.command}")
        
        # CLEAR OLD FLAG
        if os.path.exists(READY_FLAG): os.remove(READY_FLAG)

        # RESOLVE WORKING DIR
        target_dir = os.getcwd()
        try:
            parts = shlex.split(self.command)
            for p in parts:
                if os.path.exists(p):
                    target_dir = os.path.dirname(os.path.abspath(p))
                    break
        except: pass
        self.log(f"CHDIR -> {target_dir}")
        os.chdir(target_dir)

        # LAUNCH PROCESS GROUP
        try:
            if os.name != 'nt':
                self.process = subprocess.Popen(self.command, shell=True, preexec_fn=os.setsid)
            else:
                self.process = subprocess.Popen(self.command, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        except Exception as e:
            self.log(f"FATAL: {e}"); return

        # WAIT FOR WINDOW INIT & SET READY FLAG
        # 1.5 seconds is enough for most Python/Pygame/Bash apps to spawn a window
        threading.Thread(target=self.signal_ready, daemon=True).start()
        
        # MONITOR EXIT
        threading.Thread(target=self.wait_for_exit, daemon=True).start()
        
        while self.running:
            if self.process.poll() is not None: break
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: self.toggle_pause()
            if self.is_paused: self.show_pause_menu()
            time.sleep(0.01)
        self.cleanup()

    def signal_ready(self):
        time.sleep(1.8) # Wait for window to stabilize
        with open(READY_FLAG, "w") as f: f.write("READY")
        self.log("READY HANDSHAKE SENT")

    def wait_for_exit(self):
        self.process.wait()
        self.running = False

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.log("SUSPENDING SESSION")
            if os.name != 'nt': os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.log("RESUMING SESSION")
            if os.name != 'nt': os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
            pygame.display.quit(); pygame.display.init()

    def show_pause_menu(self):
        self.screen.fill(C_BG)
        rect = self.screen.get_rect().inflate(-300, -300)
        pygame.draw.rect(self.screen, C_BORDER, rect, 15, border_radius=40)
        t1 = self.font_lg.render("ARCADE PAUSED", True, C_LIME)
        t2 = self.font_sm.render("ESC: CONTINUE", True, C_WHITE)
        t3 = self.font_sm.render("Q: TERMINATE", True, (255, 0, 0))
        self.screen.blit(t1, t1.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 100)))
        self.screen.blit(t2, t2.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20)))
        self.screen.blit(t3, t3.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 90)))
        pygame.display.flip()
        
        m_run = True
        while m_run and self.is_paused:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: self.toggle_pause(); m_run = False
                    if event.key == pygame.K_q: self.running = False; self.is_paused = False; m_run = False
            time.sleep(0.01)

    def cleanup(self):
        self.log("PURGING SESSION...")
        if os.path.exists(READY_FLAG): os.remove(READY_FLAG)
        try:
            if self.process and self.process.poll() is None:
                if os.name != 'nt': os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    import subprocess as sp
                    sp.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True)
        except: pass
        pygame.quit(); sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    cmd = " ".join(sys.argv[1:])
    ArcadeWrapper(cmd).launch()
