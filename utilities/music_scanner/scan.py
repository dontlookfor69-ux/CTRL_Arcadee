import os
import json
import sys
try:
    from tinytag import TinyTag
except ImportError:
    print("tinytag not installed. Install via pip install tinytag")
    sys.exit(1)

def scan_music(music_dir):
    db = []
    if not os.path.exists(music_dir):
        print(f"Directory {music_dir} not found.")
        return
        
    for root, dirs, files in os.walk(music_dir):
        for f in files:
            if f.lower().endswith('.mp3'):
                filepath = os.path.join(root, f)
                try:
                    tag = TinyTag.get(filepath)
                    db.append({
                        "file": f,
                        "path": filepath,
                        "title": tag.title or f,
                        "artist": tag.artist or "Unknown Artist",
                        "album": tag.album or "Unknown Album",
                        "duration": tag.duration or 0.0
                    })
                except Exception as e:
                    print(f"Failed to read {f}: {e}")
                    
    db.sort(key=lambda x: (x["artist"], x["album"], x["title"]))
    
    out_path = os.path.join(music_dir, "db.json")
    with open(out_path, 'w') as f:
        json.dump(db, f, indent=4)
        
    print(f"Scanned {len(db)} MP3 files to {out_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        music_dir = sys.argv[1]
    else:
        music_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "godot_project", "assets", "music")
    scan_music(music_dir)
