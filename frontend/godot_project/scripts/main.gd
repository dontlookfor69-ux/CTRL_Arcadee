extends Control

# ── Global State ─────────────────────────────────────────────────────────────
var is_launching   = false
var is_input_debugger_active = false
var root_path      = ""

onready var games_grid          = $MainUI/GamesCenter/GamesGrid
onready var debug_menu          = $MainUI/DebugMenu
onready var main_ui             = $MainUI
onready var boot_screen         = $BootScreen
onready var clock_label         = $MainUI/Header/HBox/ClockLabel
onready var about_button        = get_node_or_null("MainUI/Header/HBox/AboutButton")
onready var input_debug_overlay = $MainUI/InputDebugOverlay
onready var input_debug_log     = $MainUI/InputDebugOverlay/Scroll/LogLabel

var C_BG     = Color(0, 0, 0, 1)
var C_ACCENT = Color(0.0, 1.0, 1.0, 1)
var C_LIME   = Color(0.2, 1.0, 0.2, 1)

var game_paths = {
	"Pacman":             {"path": "games/pacman/Pacman for Arcade/main.py",            "icon": "res://assets/icons/pacman.png"},
	"Tetris":             {"path": "games/tetris/main.py",                              "icon": "res://assets/icons/tetris.png"},
	"DOOM":               {"path": "games/doom/launch_doom.sh",                         "icon": "res://assets/icons/doom.png"},
	"Undertale":          {"path": "games/undertale/undertale-clone-master/undertale-clone-master/main.py", "icon": "res://assets/icons/undertale.png"},
	"Just Shapes & Beats":{"path": "games/just_shapes_and_beats/game.py",               "icon": "res://assets/icons/Just_Shapes_And_Beats.png"},
	"Minecraft Pi":       {"path": "games/minecraft_pi/launch_mcpi.sh",                 "icon": "res://assets/icons/minecraft.png"},
	"Etch A Sketch AI":   {"path": "utilities/etch_a_sketch_ai/main.py",                "icon": "res://assets/icons/etch_a_sketch.png"},
	"Media Player":       {"scene": "res://scenes/media_player.tscn",                   "icon": "res://assets/icons/Media_Player.png"}
}

func _ready():
	_detect_root_path()
	print("[SYSTEM DEBUG] OS: ", OS.get_name())
	print("[SYSTEM DEBUG] Root Path: ", root_path)
	
	main_ui.hide(); boot_screen.show()
	_build_game_buttons()
	_build_loading_bar()
	_safe_connect_debug_buttons()
	call_deferred("play_boot_sequence")

func _detect_root_path():
	var p = ProjectSettings.globalize_path("res://")
	var dir = Directory.new()
	
	# Clean path (remove trailing slashes)
	p = p.rstrip("/")
	
	# Iterate up to 5 levels to find the "CTRL_Arcadee" folder or a folder containing 'games'
	var check_path = p
	for i in range(5):
		if dir.dir_exists(check_path.plus_file("games")) and dir.dir_exists(check_path.plus_file("utilities")):
			root_path = check_path
			return
		check_path = check_path.get_base_dir()
	
	# Fallback to absolute Pi path
	root_path = "/home/ctrl/Desktop/CTRL_Arcadee"

func _build_game_buttons():
	for child in games_grid.get_children(): child.queue_free()
	var i = 0
	for game_name in game_paths.keys():
		var btn = Button.new()
		btn.rect_min_size = Vector2(220, 260); btn.focus_mode = Control.FOCUS_ALL
		btn.rect_pivot_offset = Vector2(110, 130)
		
		var fs = StyleBoxFlat.new()
		fs.bg_color = Color(0,0,0,0.9); fs.border_color = C_ACCENT; fs.set_border_width_all(4)
		btn.set("custom_styles/normal", fs); btn.set("custom_styles/focus", fs); btn.set("custom_styles/hover", fs)

		var tex = load_external_texture(game_paths[game_name]["icon"])
		if tex:
			var ir = TextureRect.new()
			ir.texture = tex; ir.expand = true; ir.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			ir.anchor_left = 0.5; ir.anchor_top = 0.4; ir.anchor_right = 0.5; ir.anchor_bottom = 0.4
			ir.margin_left = -70; ir.margin_right = 70; ir.margin_top = -70; ir.margin_bottom = 70
			btn.add_child(ir)

		var lbl = Label.new()
		lbl.text = game_name.to_upper(); lbl.align = Label.ALIGN_CENTER; lbl.anchor_top = 0.8; lbl.anchor_bottom = 0.8; lbl.anchor_right = 1.0
		btn.add_child(lbl)

		var tw = Tween.new(); tw.name = "HoverTween"
		btn.add_child(tw) # Add child immediately in build
		
		btn.connect("pressed", self, "launch_game", [game_name, i])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		games_grid.add_child(btn)
		i += 1

func _build_loading_bar():
	var lo = $MainUI/LoadingOverlay; if not lo: return
	for child in lo.get_children(): child.queue_free()
	var pb = ProgressBar.new(); pb.name = "FakeLoadingBar"
	pb.anchor_left = 0.5; pb.anchor_top = 0.5; pb.anchor_right = 0.5; pb.anchor_bottom = 0.5
	pb.margin_left = -400; pb.margin_right = 400; pb.margin_top = 100; pb.margin_bottom = 140
	lo.add_child(pb)
	var lbl = Label.new(); lbl.name = "LoadingLabel"; lbl.add_color_override("font_color", C_LIME)
	lbl.anchor_left = 0.0; lbl.anchor_right = 1.0; lbl.anchor_top = 0.5; lbl.anchor_bottom = 0.5
	lbl.margin_top = 40; lbl.align = Label.ALIGN_CENTER
	lo.add_child(lbl)

func _safe_connect_debug_buttons():
	var cb = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("CloseButton")
	if cb: 
		for connection in cb.get_signal_connection_list("pressed"): cb.disconnect("pressed", self, connection.method)
		cb.connect("pressed", self, "toggle_debug_menu")
		
	var ib = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("InputDebugButton")
	if ib:
		for connection in ib.get_signal_connection_list("pressed"): ib.disconnect("pressed", self, connection.method)
		ib.connect("pressed", self, "_on_InputDebugButton_pressed")

func play_boot_sequence():
	if Global.has_booted:
		boot_screen.hide(); main_ui.show()
		if games_grid.get_child_count() > 0: games_grid.get_child(Global.last_focused_game_index).grab_focus()
		return
		
	var bios = $BootScreen/BiosText; boot_screen.color = Color(0,0,0,1); bios.bbcode_text = ""
	var log_lines = [
		">> [color=#00ff00]CTRL ARCADE BIOS v7.0[/color] <<",
		"CPU: RASPBERRY PI 4B @ 2.0GHz [color=#00ff00]OK[/color]",
		"MEM: 8192MB LPDDR4X [color=#00ff00]STABLE[/color]",
		"OS: DEBIAN 12 BOOKWORM [color=#00ff00]LOADED[/color]",
		"----------------------------------------"
	]
	for l in log_lines:
		bios.bbcode_text += l + "\n"
		yield(get_tree().create_timer(0.05), "timeout")

	bios.bbcode_text += "MAPPING DIRECTORIES:\n"
	bios.bbcode_text += "  - Root: " + root_path + " ... [color=#00ff00]FOUND[/color]\n"
	yield(get_tree().create_timer(0.1), "timeout")

	bios.bbcode_text += "\n[color=#00ffff]READY TO START.[/color]"
	yield(get_tree().create_timer(0.5), "timeout")
	Global.has_booted = true; boot_screen.hide(); main_ui.show()
	if games_grid.get_child_count() > 0: games_grid.get_child(0).grab_focus()

func launch_game(game_name, index):
	if is_launching: return
	is_launching = true; Global.last_focused_game_index = index
	var lo = $MainUI/LoadingOverlay; lo.show()
	var pb = lo.get_node("FakeLoadingBar"); var lbl = lo.get_node("LoadingLabel")
	
	pb.value = 0
	lbl.text = "INITIALIZING " + game_name.to_upper() + "..."
	
	# Start process
	_perform_actual_launch(game_name)
	
	# FAKE LOADING WITH SYNC CHECK
	var start_time = OS.get_ticks_msec()
	var is_ready = false
	
	# Wait for a minimum of 2 seconds, OR until the "ready" file exists
	while (OS.get_ticks_msec() - start_time < 3000) or (not is_ready):
		var elapsed = OS.get_ticks_msec() - start_time
		pb.value = min(99.0, (elapsed / 3000.0) * 100.0)
		
		# Check for "ready" flag from wrapper (handshake)
		# We'll use a file check for simplicity and robustness
		var f = File.new()
		if f.file_exists("/tmp/arcade_ready"):
			is_ready = true
			pb.value = 100.0
			lbl.text = "SYNC COMPLETE. STARTING!"
			break
		
		lbl.text = "SYNCING WITH GAME... " + str(int(pb.value)) + "%"
		yield(get_tree(), "idle_frame")
		
		# Absolute timeout to prevent infinite loop
		if elapsed > 8000: break 

	yield(get_tree().create_timer(0.5), "timeout")
	lo.hide(); is_launching = false

func _perform_actual_launch(game_name):
	# Clear the ready flag before launching
	var dir = Directory.new()
	if dir.file_exists("/tmp/arcade_ready"): dir.remove("/tmp/arcade_ready")

	var info = game_paths[game_name]
	if info.has("scene"):
		get_tree().change_scene(info["scene"]); return

	var abs_path = root_path.plus_file(info["path"])
	var wrapper  = root_path.plus_file("utilities/pause_wrapper/wrapper.py")
	var python   = "python" if OS.get_name() == "Windows" else "python3"
	
	var inner_cmd = ""
	if abs_path.ends_with(".py"): inner_cmd = python + " \"" + abs_path + "\""
	elif abs_path.ends_with(".sh"): inner_cmd = "bash \"" + abs_path + "\""
	else: inner_cmd = "\"" + abs_path + "\""
	
	print("[LAUNCH DEBUG] Wrapper: ", wrapper)
	print("[LAUNCH DEBUG] Target:  ", abs_path)
	print("[LAUNCH DEBUG] Command: ", python + " " + wrapper + " " + inner_cmd)
	
	OS.execute(python, [wrapper, inner_cmd], false)

func toggle_debug_menu():
	debug_menu.visible = !debug_menu.visible
	if debug_menu.visible:
		var cb = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("CloseButton")
		if cb: cb.grab_focus()

func load_external_texture(path):
	var img = Image.new(); var gp = ProjectSettings.globalize_path(path)
	if img.load(gp) == OK:
		var tex = ImageTexture.new(); tex.create_from_image(img, 0); return tex
	return null

func _on_btn_focus_entered(btn):
	var tw = btn.get_node_or_null("HoverTween")
	if tw and tw.is_inside_tree():
		tw.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.1,1.1), 0.1); tw.start()

func _on_btn_focus_exited(btn):
	var tw = btn.get_node_or_null("HoverTween")
	if tw and tw.is_inside_tree():
		tw.interpolate_property(btn, "rect_scale", Vector2(1.1,1.1), Vector2(1,1), 0.1); tw.start()

func _on_InputDebugButton_pressed():
	toggle_debug_menu(); input_debug_overlay.show(); is_input_debugger_active = true

func _on_CloseInputDebug_pressed():
	input_debug_overlay.hide(); is_input_debugger_active = false

func _on_AboutButton_pressed():
	OS.alert("CTRL ARCADE v7.0\nHigh Stability Build", "System Info")

func _process(_delta):
	if clock_label:
		var t = OS.get_time(); clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]
	if Input.is_action_just_pressed("debug_q"): toggle_debug_menu()
	if is_input_debugger_active and Input.is_action_just_pressed("ui_cancel"): _on_CloseInputDebug_pressed()
