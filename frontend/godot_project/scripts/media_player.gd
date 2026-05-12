extends Control

onready var audio_player  = $WindowFrame/MainContent/VideoPanel/AudioPlayer
onready var status_label  = $WindowFrame/StatusBar/StatusLabel
onready var play_btn      = $WindowFrame/ControlsBar/HBox/PlayPauseBtn
onready var song_list     = $WindowFrame/MainContent/PlaylistPanel/ColorRect/SongList
onready var search_input  = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchInput
onready var now_playing   = $WindowFrame/MainContent/VideoPanel/SearchBox/NowPlayingLabel

const PLAYLIST_FILE = "media_player_playlist.json"
var playlist = []
var last_query = ""
var _current_index = -1
var _download_thread: Thread

func _ready():
	_load_playlist()
	status_label.text = "Ready — enter a song to download"
	search_input.placeholder_text = "Search song..."
	
	# Wire up SearchBtn as it's not connected in .tscn
	var search_btn = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchBtn
	if search_btn:
		search_btn.connect("pressed", self, "_on_SearchBtn_pressed")

func _get_playlist_path() -> String:
	# Use the Global root path detected by main.gd
	if Global.root_path != "":
		return Global.root_path.plus_file(PLAYLIST_FILE)
	
	# Fallback if Global.root_path isn't set
	var root = ProjectSettings.globalize_path("res://").rstrip("/")
	root = root.get_base_dir().get_base_dir()
	return root.plus_file(PLAYLIST_FILE)

func _load_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	if f.file_exists(path):
		if f.open(path, File.READ) == OK:
			var text = f.get_as_text()
			f.close()
			var res = JSON.parse(text)
			if res.error == OK:
				playlist = res.result
				_update_playlist_ui()

func _save_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	if f.open(path, File.WRITE) == OK:
		f.store_string(JSON.print(playlist))
		f.close()

func _update_playlist_ui():
	song_list.clear()
	for song in playlist:
		song_list.add_item(song.name)

func _on_SongList_item_activated(index):
	_play_by_index(index)

func _on_SearchBtn_pressed():
	var query = search_input.text
	if query == "": return
	
	if _download_thread and _download_thread.is_active():
		status_label.text = "Already downloading..."
		return
		
	last_query = query
	status_label.text = "Searching..."
	
	_download_thread = Thread.new()
	_download_thread.start(self, "_do_download", query)

func _do_download(query):
	# Directory scanning is NOT thread-safe in Godot 3.
	# We perform only the OS.execute in the thread, and handle file discovery 
	# on the main thread via call_deferred.
	
	# First, ensure the download directory exists (on main thread if possible, 
	# but we'll do a quick check here or assume it was done in _ready)
	
	var download_path = ProjectSettings.globalize_path("user://downloads")
	
	# Record existing files to detect the new one accurately
	var existing_files = []
	var dir = Directory.new()
	if dir.open(download_path) == OK:
		dir.list_dir_begin()
		var file_name = dir.get_next()
		while file_name != "":
			if not dir.current_is_dir():
				existing_files.append(file_name)
			file_name = dir.get_next()
		dir.list_dir_end()
	else:
		dir.make_dir_recursive(download_path)
	
	var output_template = download_path + "/%(title)s.%(ext)s"
	var args = [
		"--extract-audio",
		"--audio-format", "mp3",
		"--noplaylist",
		"--default-search", "ytsearch",
		"-o", output_template,
		query
	]
	
	var output = []
	OS.execute("yt-dlp", args, true, output)
	
	# Discovery phase must happen on the main thread for reliability
	call_deferred("_finalize_download", download_path, existing_files)

func _finalize_download(download_path, existing_files):
	if _download_thread:
		_download_thread.wait_to_finish()
	
	var actual_file = ""
	var dir = Directory.new()
	if dir.open(download_path) == OK:
		dir.list_dir_begin()
		var file_name = dir.get_next()
		var latest_time = 0
		
		while file_name != "":
			if not dir.current_is_dir() and file_name.ends_with(".mp3"):
				# If it's a NEW file (didn't exist before), it's our target.
				# If multiple new files exist, we take the one with the latest mod time.
				if not file_name in existing_files:
					var full_p = download_path + "/" + file_name
					var f = File.new()
					var t = f.get_modified_time(full_p)
					if t >= latest_time:
						latest_time = t
						actual_file = "user://downloads/" + file_name
			file_name = dir.get_next()
		dir.list_dir_end()
	
	if actual_file != "":
		_on_download_complete(actual_file)
	else:
		_on_download_failed()

func _on_download_complete(path):
	var song_data = {"name": last_query, "path": path}
	playlist.append(song_data)
	_save_playlist()
	_update_playlist_ui()
	_play_by_index(playlist.size() - 1)

func _on_download_failed():
	status_label.text = "Download Failed"
	now_playing.text = "Error downloading song"

func _play_by_index(index):
	if index < 0 or index >= playlist.size(): return
	_current_index = index
	var song = playlist[index]
	last_query = song.name
	_play_local_file(song.path)

func _play_local_file(path):
	var abs_path = ProjectSettings.globalize_path(path)
	var f = File.new()
	if f.open(abs_path, File.READ) == OK:
		var bytes = f.get_buffer(f.get_len())
		f.close()
		var stream = AudioStreamMP3.new()
		stream.data = bytes
		audio_player.stream = stream
		audio_player.play()
		now_playing.text = "Now Playing:\n" + last_query
		status_label.text = "Playing"
		play_btn.text = "Pause"
	else:
		now_playing.text = "Error: Could not open audio file"
		status_label.text = "Playback Error"
		print("[MEDIA] Failed to open: ", abs_path)

func _on_PlayPauseBtn_pressed():
	if audio_player.playing:
		audio_player.stream_paused = !audio_player.stream_paused
		play_btn.text = "Resume" if audio_player.stream_paused else "Pause"
		status_label.text = "Paused" if audio_player.stream_paused else "Playing"
	elif audio_player.stream != null:
		audio_player.play()
		play_btn.text = "Pause"
		status_label.text = "Playing"

func _on_PrevBtn_pressed():
	var idx = max(0, _current_index - 1)
	if playlist.size() > 0: _play_by_index(idx)

func _on_NextBtn_pressed():
	if playlist.size() == 0: return
	var idx = (_current_index + 1) % playlist.size()
	_play_by_index(idx)

func _on_BackBtn_pressed():
	audio_player.stop()
	get_tree().change_scene("res://scenes/main_desktop.tscn")
