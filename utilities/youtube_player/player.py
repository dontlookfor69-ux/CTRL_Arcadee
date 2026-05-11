import json
import subprocess
import time
import os
import threading
import sys

CMD_FILE = "/tmp/arcade_player_cmd.json"
STATE_FILE = "/tmp/arcade_player_state.json"
PLAYLIST_FILE = os.path.join(os.path.dirname(__file__), "playlist.json")
# Configurable geometry for the mpv window. Users should adjust this to match their screen.
MPV_GEOMETRY = "1200x870+20+70"

# Load playlist
try:
    with open(PLAYLIST_FILE) as f:
        playlist = json.load(f)
except Exception as e:
    playlist = []
    print(f"Error loading playlist: {e}")

current_process = None
current_index = -1
is_playing = False
is_buffering = False

def write_state():
    state = {
        "playing": is_playing,
        "buffering": is_buffering,
        "current_index": current_index,
        "title": playlist[current_index]["title"] if current_index >= 0 and current_index < len(playlist) else "",
        "artist": playlist[current_index]["artist"] if current_index >= 0 and current_index < len(playlist) else "",
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        pass

def _resolve_and_play(index):
    global current_process, current_index, is_playing, is_buffering
    
    current_index = index % len(playlist) if len(playlist) > 0 else -1
    if current_index < 0:
        is_buffering = False
        write_state()
        return

    url = playlist[current_index]["youtube_url"]
    
    # Use webbrowser to reliably play the music video on Windows
    import webbrowser
    webbrowser.open(url)
    
    is_playing = True
    is_buffering = False
    write_state()

def play_index(index):
    global current_process, is_buffering, is_playing
    if current_process:
        current_process.terminate()
        current_process = None
    
    is_playing = False
    is_buffering = True
    write_state()
    
    threading.Thread(target=_resolve_and_play, args=(index,), daemon=True).start()

def poll_commands():
    while True:
        try:
            if os.path.exists(CMD_FILE):
                with open(CMD_FILE) as f:
                    cmd = json.load(f)
                os.remove(CMD_FILE)
                
                if cmd["action"] == "play_index":
                    play_index(int(cmd.get("index", 0)))
                elif cmd["action"] == "next":
                    play_index(current_index + 1)
                elif cmd["action"] == "prev":
                    play_index(current_index - 1)
                elif cmd["action"] == "stop" and current_process:
                    current_process.terminate()
                    current_process = None
                    is_playing = False
                    write_state()
                elif cmd["action"] == "pause" and current_process:
                    # mpv doesn't have an easy IPC pause without sockets
                    # For simplicity we just stop
                    current_process.terminate()
                    current_process = None
                    is_playing = False
                    write_state()
        except:
            pass
        time.sleep(0.5)

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Running in test mode. Attempting to play first playlist item...")
        if playlist:
            is_buffering = True
            _resolve_and_play(0)
            if current_process:
                current_process.wait()
        else:
            print("Playlist is empty!")
        sys.exit(0)

    # Clean up state files
    for f in [CMD_FILE, STATE_FILE]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
            
    threading.Thread(target=poll_commands, daemon=True).start()
    while True:
        if current_process and current_process.poll() is not None and not is_buffering:
            # Song ended naturally
            play_index(current_index + 1)
        time.sleep(1)
