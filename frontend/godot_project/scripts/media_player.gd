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

func _ready():
	_load_playlist()
	status_label.text = "Ready — enter a song to download"
	search_input.placeholder_text = "Search song..."
	
	# Wire up SearchBtn as it's not connected in .tscn
	var search_btn = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchBtn
	if search_btn:
		search_btn.connect("pressed", self, "_on_SearchBtn_pressed")

func _get_playlist_path() -> String:
	var root = ProjectSettings.globalize_path("res://").rstrip("/")
	# Go up two levels: godot_project → frontend → CTRL_Arcadee
	root = root.get_base_dir().get_base_dir()
	return root.plus_file(PLAYLIST_FILE)

func _load_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	if f.file_exists(path):
		f.open(path, File.READ)
		var text = f.get_as_text()
		f.close()
		var res = JSON.parse(text)
		if res.error == OK:
			playlist = res.result
			_update_playlist_ui()

func _save_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	f.open(path, File.WRITE)
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
	last_query = query
	status_label.text = "Searching..."
	var thread = Thread.new()
	thread.start(self, "_do_download", query)

func _do_download(query):
	var dir = Directory.new()
	if not dir.dir_exists("user://downloads"):
		dir.make_dir("user://downloads")
	
	var download_path = ProjectSettings.globalize_path("user://downloads")
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
	
	# Find the downloaded file
	var actual_file = ""
	dir.open(download_path)
	dir.list_dir_begin()
	var file_name = dir.get_next()
	var latest_time = 0
	while file_name != "":
		if not dir.current_is_dir() and file_name.ends_with(".mp3"):
			var full_p = download_path + "/" + file_name
			var f = File.new()
			var t = f.get_modified_time(full_p)
			if t > latest_time:
				latest_time = t
				actual_file = "user://downloads/" + file_name
		file_name = dir.get_next()
	
	if actual_file != "":
		call_deferred("_on_download_complete", actual_file)
	else:
		call_deferred("_on_download_failed")

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
	var idx = (_current_index + 1) % playlist.size()
	if playlist.size() > 0: _play_by_index(idx)

func _on_BackBtn_pressed():
	audio_player.stop()
	get_tree().change_scene("res://scenes/main_desktop.tscn")
