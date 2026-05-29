#!/usr/bin/env python3
import evdev
from evdev import ecodes
import select
import time
import os
import signal
import subprocess

# Expected sequence: Down, Down, A, C, Up
# A button index: 1
# C button index: 7

class GlobalExitMonitor:
    def __init__(self):
        self.running = True
        self.sequence = ["DOWN", "DOWN", "A", "C", "UP"]
        self.seq_idx = 0
        self.last_event_time = 0
        self.timeout = 2.0  # Reset sequence if more than 2 seconds pass

    def on_input(self, action):
        now = time.time()
        if now - self.last_event_time > self.timeout:
            self.seq_idx = 0
        
        self.last_event_time = now

        if action == self.sequence[self.seq_idx]:
            self.seq_idx += 1
            if self.seq_idx == len(self.sequence):
                self.trigger_exit()
                self.seq_idx = 0
        else:
            # If failed, check if it starts a new sequence
            if action == self.sequence[0]:
                self.seq_idx = 1
            else:
                self.seq_idx = 0

    def trigger_exit(self):
        print("[GlobalExit] Sequence detected! Killing arcade...")
        # Kill all godot3 and python3 processes related to the arcade
        try:
            subprocess.run(["pkill", "-9", "-f", "godot3"])
            subprocess.run(["pkill", "-9", "-f", "python3.*wrapper"])
            subprocess.run(["pkill", "-9", "-f", "python3.*game"])
            subprocess.run(["pkill", "-9", "-f", "python3.*main.py"])
        except Exception as e:
            print("Failed to kill:", e)
        # Suicide
        os.kill(os.getpid(), signal.SIGKILL)

    def run(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        joy_devices = []
        code_maps = {}

        for dev in devices:
            caps = dev.capabilities()
            has_abs = ecodes.EV_ABS in caps
            has_btn = ecodes.EV_KEY in caps and any(c >= ecodes.BTN_JOYSTICK for c in caps.get(ecodes.EV_KEY, []))
            
            if has_abs or has_btn:
                joy_devices.append(dev)
                btn_codes = sorted(caps.get(ecodes.EV_KEY, []))
                code_a = btn_codes[1] if len(btn_codes) > 1 else -1
                code_c = btn_codes[7] if len(btn_codes) > 7 else -1
                code_maps[dev.fd] = {"A": code_a, "C": code_c}

        if not joy_devices:
            print("No joysticks found for global exit monitor.")
            return

        print(f"Monitoring {len(joy_devices)} joysticks for global exit sequence...")

        # Keep track of axis states so we only trigger on transitions
        axis_state = {}

        while self.running:
            r, _, _ = select.select(joy_devices, [], [], 0.1)
            for dev in r:
                for event in dev.read():
                    if event.type == ecodes.EV_KEY and event.value == 1:
                        if event.code == code_maps[dev.fd]["A"]:
                            self.on_input("A")
                        elif event.code == code_maps[dev.fd]["C"]:
                            self.on_input("C")
                            
                    elif event.type == ecodes.EV_ABS:
                        if dev.fd not in axis_state:
                            axis_state[dev.fd] = {"Y": 0, "HAT_Y": 0}
                            
                        if event.code == ecodes.ABS_Y:
                            if event.value > 200 and axis_state[dev.fd]["Y"] <= 200:
                                self.on_input("DOWN")
                            elif event.value < 55 and axis_state[dev.fd]["Y"] >= 55:
                                self.on_input("UP")
                            axis_state[dev.fd]["Y"] = event.value
                            
                        elif event.code == ecodes.ABS_HAT0Y:
                            if event.value == 1 and axis_state[dev.fd]["HAT_Y"] != 1:
                                self.on_input("DOWN")
                            elif event.value == -1 and axis_state[dev.fd]["HAT_Y"] != -1:
                                self.on_input("UP")
                            axis_state[dev.fd]["HAT_Y"] = event.value

if __name__ == "__main__":
    monitor = GlobalExitMonitor()
    monitor.run()
