extends Control

onready var status_label = $WindowFrame/StatusBar/StatusLabel
onready var search_input = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchInput
onready var now_playing = $WindowFrame/MainContent/VideoPanel/SearchBox/NowPlayingLabel
onready var search_btn = $WindowFrame/MainContent/VideoPanel/SearchBox/HBox/SearchBtn
onready var video_panel = $WindowFrame/MainContent/VideoPanel

var _yt_dlp_path = "yt-dlp"
var _search_thread: Thread
var _mpv_pid = -1
var _is_searching = false

func _ready():
	_detect_dependencies()
	status_label.text = "SYSTEM_READY"
	search_input.placeholder_text = "ENTER_SEARCH_QUERY..."
	if search_btn:
		if not search_btn.is_connected("pressed", self, "_on_SearchBtn_pressed"):
			search_btn.connect("pressed", self, "_on_SearchBtn_pressed")
	
	var back_btn = get_node_or_null("WindowFrame/Header/BackBtn")
	if back_btn:
		if not back_btn.is_connected("pressed", self, "_on_BackBtn_pressed"):
			back_btn.connect("pressed", self, "_on_BackBtn_pressed")

func _process(_delta):
	if _is_searching:
		var t = OS.get_ticks_msec()
		status_label.text = ">>> SEARCHING_NETWORK_[" + str(t % 999) + "] <<<"
		if randf() > 0.95:
			now_playing.text = "SCANNING_RECORDS..."
		# UI Jitter
		if randf() > 0.97:
			rect_position = Vector2(rand_range(-3,3), rand_range(-3,3))
		else:
			rect_position = Vector2(0,0)

func _input(event):
	if event.is_action_pressed("ui_cancel") or (event is InputEventKey and event.pressed and event.scancode == KEY_ESCAPE):
		_on_BackBtn_pressed()

func _detect_dependencies():
	var out = []
	OS.execute("yt-dlp", ["--version"], true, out)
	OS.execute("mpv", ["--version"], true, out)

func _on_SearchBtn_pressed():
	if _is_searching:
		return
	var query = search_input.text
	if query == "":
		return
	
	_kill_mpv()
	_is_searching = true
	now_playing.text = "QUERY: " + query.to_upper()
	status_label.text = "INITIALIZING_SEARCH..."
	
	_search_thread = Thread.new()
	_search_thread.start(self, "_do_stream_search", query)

func _do_stream_search(query):
	# Improved yt-dlp arguments for robust YouTube searching
	var args = [
		"--get-url",
		"--format", "best[ext=mp4]/best",
		"--no-playlist",
		"--default-search", "ytsearch",
		"ytsearch1:" + query
	]
	var out = []
	var exit_code = OS.execute("yt-dlp", args, true, out)
	call_deferred("_finalize_search", exit_code, out)

func _finalize_search(exit_code, out):
	if _search_thread:
		_search_thread.wait_to_finish()
		_search_thread = null
	_is_searching = false
	
	if exit_code != 0 or out.size() == 0 or out[0].strip_edges() == "":
		status_label.text = "SEARCH_FAILED"
		now_playing.text = "ERROR: NO_RESULTS_FOUND"
		return
	
	var url = out[0].strip_edges()
	if not url.begins_with("http"):
		status_label.text = "LINK_BROKEN"
		now_playing.text = "ERROR: INVALID_URL_RETURNED"
		return
		
	_launch_mpv(url)

func _launch_mpv(url):
	var gr = video_panel.get_global_rect()
	# Position mpv to cover the search box area as requested
	var x = int(gr.position.x + 5)
	var y = int(gr.position.y + 55)
	var w = int(gr.size.x - 10)
	var h = int(gr.size.y - 110)
	
	var geom = str(w) + "x" + str(h) + "+" + str(x) + "+" + str(y)
	
	var args = [
		"--geometry=" + geom,
		"--ontop",
		"--no-border",
		"--no-osc",
		"--no-input-default-bindings",
		"--vo=xv", # Best for Pi 4
		url
	]
	
	_mpv_pid = OS.execute("mpv", args, false)
	status_label.text = "STREAM_CONNECTED"
	now_playing.text = "PLAYING_LIVE_DATA"

func _kill_mpv():
	OS.execute("pkill", ["-f", "mpv"], true)
	_mpv_pid = -1

func _on_BackBtn_pressed():
	_kill_mpv()
	get_tree().change_scene("res://scenes/main_desktop.tscn")

func _exit_tree():
	_kill_mpv()
