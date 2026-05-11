#!/usr/bin/python3
"""
Arcade Wrapper — launches a game subprocess and intercepts ESC at the hardware 
level (evdev on Linux) to show a pause menu without conflicting with the game's
own pygame/SDL display system.
"""
import subprocess
import sys
import os
import signal
import time
import threading
import shlex

READY_FLAG = "/tmp/arcade_ready"
PAUSE_MENU_SCRIPT = os.path.join(os.path.dirname(__file__), "pause_menu.py")

class ArcadeWrapper:
    def __init__(self, command):
        self.command = command
        self.process = None
        self.running = True
        self.is_paused = False
        self._pause_lock = threading.Lock()

    def log(self, msg):
        print(f"[WRAPPER] {msg}", flush=True)

    # ── Input monitoring ───────────────────────────────────────────────────
    def _start_input_monitor(self):
        """Try evdev (Linux); fall back to keyboard library; fall back to polling."""
        if sys.platform.startswith("linux"):
            try:
                import evdev
                from evdev import ecodes
                threading.Thread(target=self._evdev_monitor, args=(ecodes,), daemon=True).start()
                self.log("Input monitor: evdev")
                return
            except ImportError:
                self.log("evdev not available, trying keyboard library")
        try:
            import keyboard
            keyboard.add_hotkey("esc", self._on_esc_pressed)
            self.log("Input monitor: keyboard library")
        except Exception as e:
            self.log(f"keyboard library failed ({e}) — ESC interception disabled")

    def _evdev_monitor(self, ecodes):
        import evdev
        # Find all keyboards
        devices = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps and ecodes.KEY_ESC in caps[ecodes.EV_KEY]:
                    devices.append(dev)
                    self.log(f"Monitoring: {dev.name}")
            except Exception:
                pass
        
        if not devices:
            self.log("No keyboard devices found for evdev monitoring")
            return

        import select
        while self.running:
            try:
                r, _, _ = select.select(devices, [], [], 0.1)
                for dev in r:
                    for event in dev.read():
                        if (event.type == ecodes.EV_KEY and 
                            event.code == ecodes.KEY_ESC and 
                            event.value == 1):  # value 1 = key down
                            self._on_esc_pressed()
            except Exception:
                pass

    def _on_esc_pressed(self):
        if not self.running:
            return
        with self._pause_lock:
            if self.is_paused:
                return  # already in pause menu
            self.is_paused = True
        self._show_pause_menu()

    # ── Pause menu ─────────────────────────────────────────────────────────
    def _show_pause_menu(self):
        """Suspend the game, show pause_menu.py as a subprocess, then resume or quit."""
        self._suspend_game()
        
        try:
            result = subprocess.run(
                ["python3", PAUSE_MENU_SCRIPT],
                timeout=300  # 5 minute safety timeout
            )
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            exit_code = 0  # resume on timeout
        except FileNotFoundError:
            self.log(f"pause_menu.py not found at {PAUSE_MENU_SCRIPT}")
            exit_code = 0
        except Exception as e:
            self.log(f"Pause menu error: {e}")
            exit_code = 0
        
        with self._pause_lock:
            self.is_paused = False

        if exit_code == 0:
            self._resume_game()
        else:
            self.log("User chose EXIT from pause menu")
            self.running = False
            self._kill_game()

    def _suspend_game(self):
        if self.process and self.process.poll() is None and os.name != 'nt':
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
                self.log("Game suspended (SIGSTOP)")
            except Exception as e:
                self.log(f"SIGSTOP failed: {e}")

    def _resume_game(self):
        if self.process and self.process.poll() is None and os.name != 'nt':
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
                self.log("Game resumed (SIGCONT)")
            except Exception as e:
                self.log(f"SIGCONT failed: {e}")

    def _kill_game(self):
        if self.process and self.process.poll() is None:
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                   capture_output=True)
            except Exception as e:
                self.log(f"Kill failed: {e}")

    # ── Ready signal ───────────────────────────────────────────────────────
    def _signal_ready(self):
        time.sleep(1.8)
        try:
            with open(READY_FLAG, "w") as f:
                f.write("READY")
            self.log("Ready handshake sent")
        except Exception as e:
            self.log(f"Could not write ready flag: {e}")

    # ── Main launch ────────────────────────────────────────────────────────
    def launch(self):
        # Clear old ready flag
        if os.path.exists(READY_FLAG):
            try:
                os.remove(READY_FLAG)
            except Exception:
                pass

        # Resolve working directory from command
        target_dir = os.getcwd()
        try:
            parts = shlex.split(self.command)
            for p in parts:
                if os.path.exists(p):
                    target_dir = os.path.dirname(os.path.abspath(p))
                    break
        except Exception:
            pass
        
        self.log(f"Working dir: {target_dir}")
        os.chdir(target_dir)

        # Launch the game process
        try:
            if os.name != 'nt':
                self.process = subprocess.Popen(
                    self.command, shell=True, preexec_fn=os.setsid
                )
            else:
                self.process = subprocess.Popen(
                    self.command, shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
        except Exception as e:
            self.log(f"FATAL: Could not launch process: {e}")
            return

        self.log(f"Launched PID {self.process.pid}: {self.command}")

        # Start threads
        threading.Thread(target=self._signal_ready, daemon=True).start()
        self._start_input_monitor()

        # Wait for game to exit
        self.process.wait()
        self.running = False
        self.log("Game process exited")
        
        # Cleanup
        if os.path.exists(READY_FLAG):
            try:
                os.remove(READY_FLAG)
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wrapper.py <command>")
        sys.exit(1)
    cmd = " ".join(sys.argv[1:])
    ArcadeWrapper(cmd).launch()
