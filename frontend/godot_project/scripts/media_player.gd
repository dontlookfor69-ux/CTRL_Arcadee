extends Control

onready var song_list = $WindowFrame/MainContent/ListPanel/SongList
onready var player = $AudioStreamPlayer
onready var title_label = $WindowFrame/MainContent/VisualizerPanel/Screen/TitleLabel
onready var progress = $WindowFrame/ControlsPanel/HBox/ProgressBar
onready var status_label = $WindowFrame/StatusBar/StatusLabel

var db = []
var current_index = -1

func _ready():
	# Run python scanner first
	var project_root = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir()
	var scanner = project_root.plus_file("utilities/music_scanner/scan.py")
	var music_dir = ProjectSettings.globalize_path("res://assets/music")
	var is_windows = OS.get_name() == "Windows"
	
	print("Scanning music...")
	if is_windows:
		OS.execute("python", [scanner, music_dir], true)
	else:
		OS.execute("bash", ["-c", "python3 '" + scanner + "' '" + music_dir + "'"], true)
	
	load_db()

func load_db():
	var f = File.new()
	if f.open("res://assets/music/db.json", File.READ) == OK:
		var result = JSON.parse(f.get_as_text())
		f.close()
		if result.error == OK and typeof(result.result) == TYPE_ARRAY:
			db = result.result
			populate_list()
	
	if db.size() == 0:
		title_label.text = "No MP3s found in assets/music"

func populate_list():
	song_list.clear()
	for song in db:
		var text = "%s - %s" % [song.get("artist", "Unknown"), song.get("title", "Unknown")]
		song_list.add_item(text)

func _process(delta):
	if player.playing and player.stream:
		progress.value = (player.get_playback_position() / player.stream.get_length()) * 100
		
	if Input.is_action_just_pressed("ui_cancel") or Input.is_action_just_pressed("debug_combo_p1"):
		get_tree().change_scene("res://scenes/main_desktop.tscn")

func _on_SongList_item_activated(index):
	play_song(index)

func play_song(index):
	if index < 0 or index >= db.size(): return
	current_index = index
	var song = db[index]
	var path = song["path"]
	
	title_label.text = "%s\n%s\n%s" % [song.get("title", ""), song.get("artist", ""), song.get("album", "")]
	status_label.text = "Playing: " + song.get("title", "")
	
	var file = File.new()
	if file.open(path, File.READ) == OK:
		var bytes = file.get_buffer(file.get_len())
		file.close()
		var stream = AudioStreamMP3.new()
		stream.data = bytes
		player.stream = stream
		player.play()

func _on_PlayPause_pressed():
	if player.playing:
		player.stream_paused = not player.stream_paused
	elif current_index >= 0:
		player.play()
	elif db.size() > 0:
		play_song(0)

func _on_Next_pressed():
	if db.size() > 0:
		play_song((current_index + 1) % db.size())

func _on_Prev_pressed():
	if db.size() > 0:
		var idx = current_index - 1
		if idx < 0: idx = db.size() - 1
		play_song(idx)

func _on_BackButton_pressed():
	get_tree().change_scene("res://scenes/main_desktop.tscn")
