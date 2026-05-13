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
		status_label.text = ">>> SEARCHING_STREAMS_[" + str(t % 999) + "] <<<"
		if randf() > 0.95:
			now_playing.text = "SCANNING_YOUTUBE_DB..."
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
	status_label.text = "CONNECTING_TO_API..."
	
	_search_thread = Thread.new()
	_search_thread.start(self, "_do_stream_search", query)

func _do_stream_search(query):
	# [FINAL_FIX] Extremely robust search parameters
	var base_args = [
		"--get-url",
		"--format", "best",
		"--no-playlist",
		"--default-search", "ytsearch",
		"--socket-timeout", "20",
		"--no-check-certificate",
		"--no-warnings"
	]
	
	# Strategy 1: Targeted search
	var args1 = base_args.duplicate()
	args1.append("ytsearch1:" + query)
	var out = []
	var exit_code = OS.execute("yt-dlp", args1, true, out)
	
	# Strategy 2: Permissive search with 'video'
	if exit_code != 0 or out.size() == 0 or not _has_url(out):
		status_label.text = "RETRYING_STRATEGY_B..."
		var args2 = base_args.duplicate()
		args2.append("ytsearch1:" + query + " video")
		out = []
		exit_code = OS.execute("yt-dlp", args2, true, out)
	
	# Strategy 3: Multi-result search (take first)
	if exit_code != 0 or out.size() == 0 or not _has_url(out):
		status_label.text = "RETRYING_STRATEGY_C..."
		var args3 = base_args.duplicate()
		args3.append("ytsearch5:" + query)
		out = []
		exit_code = OS.execute("yt-dlp", args3, true, out)
		
	call_deferred("_finalize_search", exit_code, out)

func _has_url(out):
	for line in out:
		if line.strip_edges().begins_with("http"):
			return true
	return false

func _finalize_search(exit_code, out):
	if _search_thread:
		_search_thread.wait_to_finish()
		_search_thread = null
	_is_searching = false
	
	var url = ""
	for line in out:
		var s = line.strip_edges()
		if s.begins_with("http"):
			url = s
			break
	
	if url == "":
		status_label.text = "SEARCH_FAILED"
		now_playing.text = "ERROR: NO_STREAMS_FOUND"
		return
		
	_launch_mpv(url)

func _launch_mpv(url):
	var gr = video_panel.get_global_rect()
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
		"--vo=xv",
		url
	]
	
	_mpv_pid = OS.execute("mpv", args, false)
	status_label.text = "STREAM_READY"
	now_playing.text = "DATA_FLOWING_OK"

func _kill_mpv():
	OS.execute("pkill", ["-f", "mpv"], true)
	_mpv_pid = -1

func _on_BackBtn_pressed():
	_kill_mpv()
	get_tree().change_scene("res://scenes/main_desktop.tscn")

func _exit_tree():
	_kill_mpv()
