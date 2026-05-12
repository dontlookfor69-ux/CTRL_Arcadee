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
var _yt_dlp_path = "yt-dlp"

func _ready():
	_detect_yt_dlp()
	_ensure_download_dir()
	_load_playlist()
	status_label.text = "Ready — enter a song to download"
	search_input.placeholder_text = "Search song..."
	
	var search_btn = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchBtn
	if search_btn:
		search_btn.connect("pressed", self, "_on_SearchBtn_pressed")

func _detect_yt_dlp():
	var paths = ["/usr/bin/yt-dlp", "/usr/local/bin/yt-dlp", OS.get_environment("HOME") + "/.local/bin/yt-dlp", "yt-dlp"]
	for p in paths:
		var out = []
		if OS.execute(p, ["--version"], true, out) == 0:
			_yt_dlp_path = p
			print("[MEDIA] Using yt-dlp at: ", p)
			return
	push_warning("[MEDIA] yt-dlp not found in standard paths!")

func _ensure_download_dir():
	var dir = Directory.new()
	var path = ProjectSettings.globalize_path("user://downloads")
	if not dir.dir_exists(path):
		dir.make_dir_recursive(path)

func _get_playlist_path() -> String:
	if Global.root_path != "":
		return Global.root_path.plus_file(PLAYLIST_FILE)
	return ProjectSettings.globalize_path("user://").plus_file(PLAYLIST_FILE)

func _load_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	if f.file_exists(path) and f.open(path, File.READ) == OK:
		var res = JSON.parse(f.get_as_text())
		if res.error == OK:
			playlist = res.result
			_update_playlist_ui()
		f.close()

func _save_playlist():
	var path = _get_playlist_path()
	var f = File.new()
	if f.open(path, File.WRITE) == OK:
		f.store_string(JSON.print(playlist))
		f.close()

func _update_playlist_ui():
	song_list.clear()
	for song in playlist: song_list.add_item(song.name)

func _on_SongList_item_activated(index):
	_play_by_index(index)

func _on_SearchBtn_pressed():
	var query = search_input.text
	if query == "" or (_download_thread and _download_thread.is_active()): return
	last_query = query
	status_label.text = "Searching..."
	_download_thread = Thread.new()
	_download_thread.start(self, "_do_download", query)

func _do_download(query):
	var download_path = ProjectSettings.globalize_path("user://downloads")
	var existing_files = []
	var dir = Directory.new()
	if dir.open(download_path) == OK:
		dir.list_dir_begin()
		var file_name = dir.get_next()
		while file_name != "":
			if not dir.current_is_dir(): existing_files.append(file_name)
			file_name = dir.get_next()
		dir.list_dir_end()

	var output_template = download_path + "/%(title)s.%(ext)s"
	var args = ["--extract-audio", "--audio-format", "mp3", "--noplaylist", "--default-search", "ytsearch", "-o", output_template, query]
	
	var output = []
	var exit_code = OS.execute(_yt_dlp_path, args, true, output)
	
	if exit_code != 0:
		var err_msg = output.join("\n")
		call_deferred("_show_error", err_msg)
	
	call_deferred("_finalize_download", download_path, existing_files)

func _show_error(msg):
	print("[MEDIA] yt-dlp Error: ", msg)
	status_label.text = "Download Failed (Check Logs)"
	now_playing.text = "yt-dlp Error:\n" + msg.substr(0, 100) + "..."

func _finalize_download(download_path, existing_files):
	if _download_thread: _download_thread.wait_to_finish()
	var actual_file = ""
	var dir = Directory.new()
	if dir.open(download_path) == OK:
		dir.list_dir_begin()
		var file_name = dir.get_next()
		var latest_time = 0
		while file_name != "":
			if not dir.current_is_dir() and file_name.ends_with(".mp3") and not file_name in existing_files:
				var t = File.new().get_modified_time(download_path + "/" + file_name)
				if t >= latest_time:
					latest_time = t; actual_file = "user://downloads/" + file_name
			file_name = dir.get_next()
		dir.list_dir_end()
	
	if actual_file != "": _on_download_complete(actual_file)
	else: _on_download_failed()

func _on_download_complete(path):
	playlist.append({"name": last_query, "path": path})
	_save_playlist(); _update_playlist_ui(); _play_by_index(playlist.size() - 1)

func _on_download_failed():
	if status_label.text != "Download Failed (Check Logs)":
		status_label.text = "No results found"

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
		var bytes = f.get_buffer(f.get_len()); f.close()
		var stream = AudioStreamMP3.new(); stream.data = bytes
		audio_player.stream = stream; audio_player.play()
		now_playing.text = "Now Playing:\n" + last_query; status_label.text = "Playing"; play_btn.text = "Pause"
	else:
		now_playing.text = "Error: Could not open audio file"; status_label.text = "Playback Error"

func _on_PlayPauseBtn_pressed():
	if audio_player.playing:
		audio_player.stream_paused = !audio_player.stream_paused
		play_btn.text = "Resume" if audio_player.stream_paused else "Pause"
		status_label.text = "Paused" if audio_player.stream_paused else "Playing"
	elif audio_player.stream != null:
		audio_player.play(); play_btn.text = "Pause"; status_label.text = "Playing"

func _on_PrevBtn_pressed():
	if playlist.size() > 0: _play_by_index(max(0, _current_index - 1))
func _on_NextBtn_pressed():
	if playlist.size() > 0: _play_by_index((_current_index + 1) % playlist.size())
func _on_BackBtn_pressed():
	audio_player.stop(); get_tree().change_scene("res://scenes/main_desktop.tscn")
