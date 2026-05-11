extends Control

onready var song_list = $WindowFrame/MainContent/PlaylistPanel/ColorRect/SongList
onready var now_playing = $WindowFrame/MainContent/VideoPanel/SearchBox/NowPlayingLabel
onready var status_label = $WindowFrame/StatusBar/StatusLabel
onready var play_btn = $WindowFrame/ControlsBar/HBox/PlayPauseBtn
onready var progress_bar = $WindowFrame/ControlsBar/HBox/ProgressBar
onready var audio_player = $WindowFrame/MainContent/VideoPanel/AudioPlayer
onready var search_input = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchInput
onready var search_btn = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchBtn

const PLAYLIST_FILE = "utilities/youtube_player/playlist.json"
const DOWNLOAD_DIR = "user://downloads/"

var playlist = []
var current_index = -1
var download_thread = null
var last_query = ""

func _ready():
	var d = Directory.new()
	if not d.dir_exists(DOWNLOAD_DIR):
		d.make_dir(DOWNLOAD_DIR)
		
	# Apply Arcade Theme
	var desktop_bg = get_node_or_null("DesktopBg")
	if desktop_bg: desktop_bg.color = Color(0, 0, 0, 1)
	
	now_playing.add_color_override("font_color", Color(0, 1, 1, 1))
	status_label.add_color_override("font_color", Color(0, 1, 0, 1))

	_load_playlist()
	audio_player.connect("finished", self, "_on_NextBtn_pressed")
	search_btn.connect("pressed", self, "_on_SearchBtn_pressed")
	search_input.connect("text_entered", self, "_on_SearchInput_entered")

func _on_SearchInput_entered(text):
	_on_SearchBtn_pressed()

func get_safe_name(name: String) -> String:
	var out = ""
	var allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
	for i in range(name.length()):
		var c = name[i]
		if allowed.find(c) != -1:
			out += c
		else:
			out += "_"
	return out

func _on_SearchBtn_pressed():
	var query = search_input.text.strip_edges()
	if query == "": return
	
	audio_player.stop()
	last_query = query
	
	var safe_name = get_safe_name(query) + ".mp3"
	var local_path = DOWNLOAD_DIR + safe_name
	var f = File.new()
	if f.file_exists(local_path):
		_play_local_file(local_path)
		_maybe_save_to_playlist(query)
		return

	now_playing.text = "Fetching: " + query
	status_label.text = "Downloading..."
	
	if download_thread != null and download_thread.is_active():
		download_thread.wait_to_finish()
		
	download_thread = Thread.new()
	download_thread.start(self, "_download_and_play", [query, local_path])

func _load_playlist():
	var f = File.new()
	var p = ProjectSettings.globalize_path("res://")
	if p.ends_with("/") or p.ends_with("\\"): p = p.substr(0, p.length() - 1)
	var project_root = p.get_base_dir().get_base_dir()
	var path = project_root.plus_file(PLAYLIST_FILE)
	
	song_list.clear()
	if f.open(path, File.READ) == OK:
		var result = JSON.parse(f.get_as_text())
		f.close()
		if result.error == OK:
			playlist = result.result
			for song in playlist:
				song_list.add_item(song.get("title", "Unknown"))
		else:
			song_list.add_item("Error loading playlist")
	else:
		song_list.add_item("No playlist found")

func _play_index(index):
	if index < 0 or index >= playlist.size(): return
	current_index = index
	search_input.text = playlist[index].get("title", "")
	_on_SearchBtn_pressed()

func _download_and_play(args):
	var query = args[0]
	var local_path = ProjectSettings.globalize_path(args[1])
	var search_str = "ytsearch1:" + query
	var cmd_args = ["-x", "--audio-format", "mp3", "-o", local_path, search_str]
	var output = []
	OS.execute("yt-dlp", cmd_args, true, output)
	call_deferred("_on_download_finished", args[1])

func _on_download_finished(local_path):
	if download_thread:
		download_thread.wait_to_finish()
		download_thread = null
	_play_local_file(local_path)
	_maybe_save_to_playlist(last_query)

func _play_local_file(path):
	var f = File.new()
	if f.open(path, File.READ) == OK:
		var bytes = f.get_buffer(f.get_len())
		f.close()
		var stream = AudioStreamMP3.new()
		stream.data = bytes
		audio_player.stream = stream
		audio_player.play()
		now_playing.text = "Now Playing:\n" + last_query
		status_label.text = "Playing"
	else:
		now_playing.text = "Error playing file"
		status_label.text = "Error"

func _maybe_save_to_playlist(query):
	for song in playlist:
		if song.get("title", "").to_lower() == query.to_lower():
			return
	playlist.append({"title": query, "artist": "Downloaded"})
	_save_playlist()
	_load_playlist()

func _save_playlist():
	var f = File.new()
	var p = ProjectSettings.globalize_path("res://")
	if p.ends_with("/") or p.ends_with("\\"): p = p.substr(0, p.length() - 1)
	var project_root = p.get_base_dir().get_base_dir()
	var path = project_root.plus_file(PLAYLIST_FILE)
	if f.open(path, File.WRITE) == OK:
		f.store_string(JSON.print(playlist, "  "))
		f.close()

func _on_SongList_item_activated(index):
	_play_index(index)

func _on_PlayPauseBtn_pressed():
	if audio_player.playing:
		audio_player.stream_paused = !audio_player.stream_paused
		status_label.text = "Paused" if audio_player.stream_paused else "Playing"
	elif audio_player.stream:
		audio_player.play()

func _on_PrevBtn_pressed(): _play_index(current_index - 1)
func _on_NextBtn_pressed(): _play_index(current_index + 1)
func _on_BackBtn_pressed():
	audio_player.stop()
	get_tree().change_scene("res://scenes/main_desktop.tscn")

func _process(_delta):
	if audio_player.playing and not audio_player.stream_paused and audio_player.stream:
		if audio_player.stream.get_length() > 0:
			progress_bar.value = (audio_player.get_playback_position() / audio_player.stream.get_length()) * 100
	if Input.is_action_just_pressed("ui_cancel"):
		_on_BackBtn_pressed()
