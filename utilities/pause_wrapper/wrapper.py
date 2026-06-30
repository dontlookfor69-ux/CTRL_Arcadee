#!/usr/bin/python3
"""
Arcade Wrapper — launches a game subprocess and intercepts ESC (double-tap)
to show a pause menu.  Writes two flag files that the Godot frontend watches:

  /tmp/arcade_ready  — written 1.8 s after launch  (game process is up)
  /tmp/arcade_done   — written when the game exits  (Godot can restore itself)

Without arcade_done, Godot never knows the game has closed and stays minimised
forever — which was the "game running in background, menu never comes back" bug.

ARCADE BUTTON MAPPING (relevant to wrapper):
  BACK = Joystick 0 Button 6  →  acts as ESC (double-tap opens pause menu)
"""
import subprocess
import sys
import os
import signal
import time
import threading
import shlex
import re

READY_FLAG      = "/tmp/arcade_ready"
DONE_FLAG       = "/tmp/arcade_done"
PAUSE_MENU_SCRIPT = os.path.join(os.path.dirname(__file__), "pause_menu.py")

# Joystick button that acts as ESC
_BTN_BACK = 6


class ArcadeWrapper:
    def __init__(self, command: str):
        self.command        = command
        self.process        = None
        self.running        = True
        self.is_paused      = False
        self._pause_lock    = threading.Lock()
        self._last_esc_time = 0.0
        self._ESC_DOUBLE_TAP_WINDOW = 0.4
        self._window_found  = False

    def log(self, msg: str):
        print(f"[WRAPPER] {msg}", flush=True)

    # ── Flag file helpers ──────────────────────────────────────────────────────
    def _write_flag(self, path: str, content: str = "1"):
        try:
            with open(path, "w") as f:
                f.write(content)
        except Exception as e:
            self.log(f"Could not write flag {path}: {e}")

    def _remove_flag(self, path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # ── Input monitoring ───────────────────────────────────────────────────────
    def _start_input_monitor(self):
        if sys.platform.startswith("linux"):
            try:
                import evdev
                from evdev import ecodes
                if hasattr(evdev, "list_devices"):
                    threading.Thread(target=self._evdev_monitor, args=(ecodes,), daemon=True).start()
                    self.log("Input monitor: evdev")
                else:
                    self.log("evdev module is corrupt (missing list_devices) — falling back")
            except ImportError:
                self.log("evdev not available, trying keyboard library")
                try:
                    import keyboard
                    keyboard.add_hotkey("esc", self._on_esc_pressed)
                    self.log("Input monitor: keyboard library")
                except Exception as e:
                    self.log(f"keyboard library failed ({e}) — ESC interception disabled")

        # Always start the joystick BACK-button monitor
        if sys.platform.startswith("linux"):
            threading.Thread(target=self._joystick_back_monitor, daemon=True).start()
            self.log("Input monitor: joystick back-button (evdev)")
        else:
            self.log("Joystick BACK monitor: Linux only, skipped on this OS")

    def _evdev_monitor(self, ecodes):
        import evdev
        import select
        devices = []
        for path in evdev.list_devices():
            try:
                dev  = evdev.InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps and ecodes.KEY_ESC in caps[ecodes.EV_KEY]:
                    devices.append(dev)
                    self.log(f"Monitoring: {dev.name}")
            except Exception:
                pass

        if not devices:
            self.log("No keyboard devices found for evdev monitoring")
            return

        while self.running:
            try:
                if not devices:
                    break
                r, _, _ = select.select(devices, [], [], 0.1)
                for dev in r:
                    for event in dev.read():
                        if (event.type == ecodes.EV_KEY and
                                event.code == ecodes.KEY_ESC and
                                event.value == 1):
                            self._on_esc_pressed()
            except Exception as e:
                self.log(f"evdev monitor loop error: {e}")
                break

    def _joystick_back_monitor(self):
        """Read raw joystick EV_KEY events from /dev/input and treat
        button-6 (BACK) the same as a keyboard ESC press.

        Gamepad buttons are exposed as EV_KEY codes starting at BTN_TRIGGER_HAPPY
        (0x2c0 = 704) for some drivers, or as BTN_SOUTH/BTN_A etc. for others.
        We look at ALL EV_KEY events from joystick-like devices and check whether
        the nth button pressed (counting from 0) equals _BTN_BACK (6).

        A simpler approach: enumerate the EV_KEY capabilities of each device,
        sort them, and treat the 7th entry (index 6) as our BACK button.
        """
        try:
            import evdev
            from evdev import ecodes
            import select

            # Find all joystick-like devices (have EV_ABS or BTN_GAMEPAD etc.)
            joy_devices = []
            for path in evdev.list_devices():
                try:
                    dev = evdev.InputDevice(path)
                    caps = dev.capabilities()
                    # A gamepad has EV_ABS or BTN_SOUTH in its capabilities
                    has_abs = ecodes.EV_ABS in caps
                    has_btn = ecodes.EV_KEY in caps and any(
                        c >= ecodes.BTN_JOYSTICK for c in caps.get(ecodes.EV_KEY, [])
                    )
                    if has_abs or has_btn:
                        # Build sorted list of button codes to map index -> code
                        btn_codes = sorted(caps.get(ecodes.EV_KEY, []))
                        if len(btn_codes) > _BTN_BACK:
                            back_code = btn_codes[_BTN_BACK]
                            joy_devices.append((dev, back_code))
                            self.log(f"Joy BACK monitor: {dev.name!r}  "
                                     f"btn[{_BTN_BACK}] = code {back_code} "
                                     f"({ecodes.KEY.get(back_code, '?')})")
                except Exception:
                    pass

            if not joy_devices:
                self.log("Joy BACK monitor: no suitable devices found")
                return

            devs = [d for d, _ in joy_devices]
            code_map = {d.fd: code for d, code in joy_devices}

            while self.running:
                try:
                    r, _, _ = select.select(devs, [], [], 0.1)
                    for dev in r:
                        for event in dev.read():
                            if (event.type == ecodes.EV_KEY and
                                    event.value == 1 and        # key-down
                                    event.code == code_map.get(dev.fd)):
                                self.log("BACK button pressed — treating as ESC")
                                self._on_esc_pressed()
                except Exception as e:
                    self.log(f"Joy BACK monitor loop error: {e}")
                    break
        except Exception as e:
            self.log(f"Joy BACK monitor startup error: {e}")

    def _on_esc_pressed(self):
        # User requested immediate return to menu when hitting ESC
        self.log("ESC/BACK pressed — User wants to return to menu immediately")
        self.running = False
        self._kill_game()

    # ── Pause menu (DISABLED per user request) ─────────────────────────────────
    def _show_pause_menu(self):
        pass

    def _suspend_game(self):
        if self.process and self.process.poll() is None and os.name != "nt":
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
                self.log("Game suspended (SIGSTOP)")
            except Exception as e:
                self.log(f"SIGSTOP failed: {e}")

    def _resume_game(self):
        if self.process and self.process.poll() is None and os.name != "nt":
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
                self.log("Game resumed (SIGCONT)")
            except Exception as e:
                self.log(f"SIGCONT CONT failed: {e}")

    def _kill_game(self):
        if self.process and self.process.poll() is None:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True,
                    )
            except Exception as e:
                self.log(f"Kill failed: {e}")

    # ── Ready handshake ────────────────────────────────────────────────────────
    def _signal_ready(self):
        """
        Wait a moment for the game process to initialise, then write arcade_ready.
        Godot's loading bar is waiting for this file.
        1.8 s is a reasonable minimum; heavy games (Undertale/box64) may need more,
        but the Godot side now times out at 15 s instead of 8 s so it's fine.
        """
        time.sleep(1.8)
        
        # Try to strip window borders using xdotool if applicable
        if os.name != "nt":
            try:
                # Find the active window (which should be the game now) and remove borders
                # Wait for window
                subprocess.run("xdotool search --pid $(pgrep -P %d) windowactivate 2>/dev/null || true" % self.process.pid, shell=True)
                # Attempt to set it fullscreen and borderless
                subprocess.run("xprop -f _MOTIF_WM_HINTS 32c -set _MOTIF_WM_HINTS '2, 0, 0, 0, 0' -id $(xdotool getactivewindow) 2>/dev/null", shell=True)
            except Exception as e:
                self.log(f"Window override failed: {e}")

        self._write_flag(READY_FLAG, "READY")
        self.log("arcade_ready written")

    # ── Main launch ────────────────────────────────────────────────────────────
    def launch(self):
        # Clean up stale flags from a previous run
        self._remove_flag(READY_FLAG)
        self._remove_flag(DONE_FLAG)

        # Resolve working directory from the command path
        target_dir = os.getcwd()
        try:
            parts = shlex.split(self.command)
            for p in parts:
                abs_p = os.path.abspath(p)
                if os.path.isfile(abs_p):
                    target_dir = os.path.dirname(abs_p)
                    break
            else:
                matches = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', self.command)
                for groups in matches:
                    for token in groups:
                        if token and os.path.isfile(os.path.abspath(token)):
                            target_dir = os.path.dirname(os.path.abspath(token))
                            break
        except Exception:
            pass

        self.log(f"Working dir: {target_dir}")
        os.chdir(target_dir)

        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = "dummy"
        env["AUDIODEV"] = "null"

        try:
            if os.name != "nt":
                self.process = subprocess.Popen(
                    self.command, shell=True, env=env, preexec_fn=os.setsid
                )
            else:
                self.process = subprocess.Popen(
                    self.command, shell=True, env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
        except Exception as e:
            self.log(f"FATAL: Could not launch: {e}")
            # Write done so Godot doesn't stay minimised waiting forever
            self._write_flag(DONE_FLAG, "LAUNCH_FAILED")
            return

        self.log(f"Launched PID {self.process.pid}: {self.command}")
        threading.Thread(target=self._signal_ready, daemon=True).start()
        self._start_input_monitor()

        # Block until the game process exits (or is killed by the pause menu)
        self.process.wait()
        self.running = False
        self.log("Game process exited")

        # ── Signal Godot that it can restore itself ───────────────────────────
        # This is the key fix for "menu never comes back after closing a game".
        self._remove_flag(READY_FLAG)   # clean up in case it wasn't consumed
        self._write_flag(DONE_FLAG, "DONE")
        self.log("arcade_done written — Godot will restore the menu")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wrapper.py <command>")
        sys.exit(1)
    cmd = " ".join(sys.argv[1:])
    ArcadeWrapper(cmd).launch()
