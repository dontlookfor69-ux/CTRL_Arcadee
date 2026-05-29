import wave
import struct
import math
import os

OUT_DIR = r"c:\Users\HP\Desktop\CTRL_Arcadee\frontend\godot_project\assets\sfx"

def make_wav(filename, samples, sample_rate=44100):
    path = os.path.join(OUT_DIR, filename)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for s in samples:
            f.writeframesraw(struct.pack('<h', int(s * 32767)))

def gen_move_sfx():
    samples = []
    # Quick short square wave blip
    freq = 400
    for i in range(int(44100 * 0.05)): # 50ms
        env = 1.0 - (i / (44100 * 0.05))
        val = 1.0 if math.sin(2 * math.pi * freq * (i / 44100)) > 0 else -1.0
        samples.append(val * env * 0.3)
    make_wav("move.wav", samples)

def gen_select_sfx():
    samples = []
    # Upward sweeping square wave
    for i in range(int(44100 * 0.15)):
        env = 1.0 - (i / (44100 * 0.15))
        freq = 600 + (i / (44100 * 0.15)) * 400
        val = 1.0 if math.sin(2 * math.pi * freq * (i / 44100)) > 0 else -1.0
        samples.append(val * env * 0.4)
    make_wav("select.wav", samples)

def gen_launch_sfx():
    samples = []
    # Power up sweep
    for i in range(int(44100 * 0.8)):
        env = math.sin((i / (44100 * 0.8)) * math.pi)
        freq = 200 + (i / (44100 * 0.8)) ** 2 * 1200
        val = 1.0 if math.sin(2 * math.pi * freq * (i / 44100)) > 0 else -1.0
        # Add some noise for crunch
        val += (hash(str(i)) % 100 / 100.0 - 0.5) * 0.5
        samples.append(max(-1.0, min(1.0, val)) * env * 0.5)
    make_wav("launch.wav", samples)

if __name__ == '__main__':
    gen_move_sfx()
    gen_select_sfx()
    gen_launch_sfx()
    print("SFX generated!")
