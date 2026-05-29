extends Node

var has_booted = false
var media_player_running = false
var last_focused_game_index = 0
var root_path = ""

func _ready():
	var p = OS.get_executable_path().get_base_dir() if OS.has_feature("standalone") else ProjectSettings.globalize_path("res://")
	p = p.replace("\\", "/")
	p = p.rstrip("/")
	var dir = Directory.new()
	var check_path = p
	for i in range(5):
		if dir.dir_exists(check_path.plus_file("games")) and dir.dir_exists(check_path.plus_file("utilities")):
			root_path = check_path
			_start_global_monitor()
			return
		check_path = check_path.get_base_dir()
	# Fallback to looking two directories up from res://
	root_path = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir().replace("\\", "/")
	_start_global_monitor()

func _start_global_monitor():
	if OS.has_feature("standalone") or true:
		var monitor_script = root_path.plus_file("utilities/global_exit_monitor.py")
		OS.execute("python3", [monitor_script], false)
