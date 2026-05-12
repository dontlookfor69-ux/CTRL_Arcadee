extends Control

# ── Global State ─────────────────────────────────────────────────────────────
var is_launching   = false
var is_input_debugger_active = false
var root_path      = ""
var _joystick_held = false
var _attract_timer = 0.0
var _ATTRACT_DELAY = 1.5
var game_info      = {}

onready var games_grid          = $MainUI/GamesCenter/GamesGrid
onready var debug_menu          = $MainUI/DebugMenu
onready var main_ui             = $MainUI
onready var boot_screen         = $BootScreen
onready var clock_label         = $MainUI/Header/HBox/ClockLabel
onready var about_button        = get_node_or_null("MainUI/Header/HBox/AboutButton")
onready var input_debug_overlay = $MainUI/InputDebugOverlay
onready var attract_overlay     = $MainUI/AttractMode

var C_BG     = Color(0.05, 0, 0, 1)
var C_ACCENT = Color(0.0, 1.0, 1.0, 1)
var C_LIME   = Color(0.2, 1.0, 0.2, 1)

var game_paths = {
	"Pacman":             {"path": "games/pacman/launch_pacman.sh",                     "icon": "res://assets/icons/pacman.png"},
	"Tetris":             {"path": "games/tetris/main.py",                              "icon": "res://assets/icons/tetris.png"},
	"DOOM":               {"path": "games/doom/launch_doom.sh",                         "icon": "res://assets/icons/doom.png"},
	"Undertale":          {"path": "games/undertale/launch_undertale.sh",               "icon": "res://assets/icons/undertale.png"},
	"Just Shapes & Beats":{"path": "games/just_shapes_and_beats/game.py",               "icon": "res://assets/icons/Just_Shapes_And_Beats.png"},
	"Minecraft Pi":       {"path": "games/minecraft_pi/launch_mcpi.sh",                 "icon": "res://assets/icons/minecraft.png"},
	"Etch A Sketch AI":   {"path": "utilities/etch_a_sketch_ai/main.py",                "icon": "res://assets/icons/etch_a_sketch.png"},
	"Media Player":       {"scene": "res://scenes/media_player.tscn",                   "icon": "res://assets/icons/Media_Player.png"}
}

func _ready():
	_detect_root_path()
	_load_game_info()
	main_ui.hide(); boot_screen.show()
	_build_game_buttons()
	_build_loading_bar()
	_safe_connect_debug_buttons()
	
	if about_button:
		about_button.connect("pressed", self, "_on_AboutButton_pressed")
		
	call_deferred("play_boot_sequence")

func _load_game_info():
	var f = File.new()
	if f.open("res://assets/game_info.json", File.READ) == OK:
		var res = JSON.parse(f.get_as_text())
		if res.error == OK: game_info = res.result
		f.close()

func _detect_root_path():
	var p = ProjectSettings.globalize_path("res://")
	var dir = Directory.new()
	p = p.rstrip("/")
	var check_path = p
	for i in range(5):
		if dir.dir_exists(check_path.plus_file("games")) and dir.dir_exists(check_path.plus_file("utilities")):
			root_path = check_path
			return
		check_path = check_path.get_base_dir()
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
		var tw = Tween.new(); tw.name = "HoverTween"; btn.add_child(tw)
		btn.connect("pressed", self, "launch_game", [game_name, i])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn, game_name])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		games_grid.add_child(btn)
		i += 1

func _build_loading_bar():
	var lo = $MainUI/LoadingOverlay
	if not lo: return
	for child in lo.get_children(): child.queue_free()
	var pb = ProgressBar.new(); pb.name = "FakeLoadingBar"
	pb.anchor_left = 0.5; pb.anchor_top = 0.5; pb.anchor_right = 0.5; pb.anchor_bottom = 0.5
	pb.margin_left = -500; pb.margin_right = 500; pb.margin_top = -20; pb.margin_bottom = 20
	lo.add_child(pb)
	var lbl = Label.new(); lbl.name = "LoadingLabel"
	lbl.anchor_left = 0.0; lbl.anchor_right = 1.0; lbl.anchor_top = 0.5; lbl.anchor_bottom = 0.5
	lbl.margin_top = 40; lbl.margin_bottom = 80; lbl.align = Label.ALIGN_CENTER
	lo.add_child(lbl)

func _safe_connect_debug_buttons():
	var cb = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("CloseButton")
	if cb: cb.connect("pressed", self, "toggle_debug_menu")
	var sib = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("SystemInfoButton")
	if sib: sib.connect("pressed", self, "_on_SystemInfoButton_pressed")

func play_boot_sequence():
	if Global.has_booted:
		boot_screen.hide(); main_ui.show()
		if games_grid.get_child_count() > 0: games_grid.get_child(Global.last_focused_game_index).grab_focus()
		return
	
	var bios = $BootScreen/BiosText; var tween = $BootScreen/BootTween; var crt = $BootScreen/CRTScreen; var logo = $BootScreen/BootLogo
	boot_screen.color = Color(0, 0, 0, 1); bios.modulate.a = 0; logo.modulate.a = 0; bios.bbcode_text = ""
	crt.rect_scale = Vector2(1, 0.02); crt.rect_pivot_offset = Vector2(960, 540)
	tween.interpolate_property(crt, "rect_scale", Vector2(1, 0.02), Vector2(1, 1), 0.4, Tween.TRANS_EXPO, Tween.EASE_OUT)
	tween.start(); yield(tween, "tween_all_completed")
	
	bios.modulate.a = 1
	var bios_lines = [
		"[color=#00ff41]██████╗ ██████╗ ██╗  ████████╗[/color]",
		"[color=#00ff41]██╔════╝╚══██╔╝ ██║  ╚══██╔══╝[/color]",
		"[color=#00ff41]██║       ██║  ██║     ██║[/color]",
		"[color=#00ff41]╚██████╗ ██████╔╝ ███████╗██║[/color]",
		"[color=#00ff41] ╚═════╝ ╚═════╝  ╚══════╝╚═╝   [color=#00ffff]ARCADE[/color][/color]",
		"",
		"[color=#aaaaaa]BIOS v7.0  |  2025 CTRL Systems[/color]",
		"",
	]
	for line in bios_lines:
		for c in line:
			bios.bbcode_text += c
			if c != " ": yield(get_tree().create_timer(0.005), "timeout")
		bios.bbcode_text += "\n"
	
	# Memory Count
	bios.bbcode_text += "MEMORY CHECK: "
	var mem = 0
	while mem < 8192:
		mem += 128
		var t = bios.bbcode_text.split("MEMORY CHECK: ")[0] + "MEMORY CHECK: " + str(mem) + "MB OK"
		bios.bbcode_text = t
		yield(get_tree().create_timer(0.01), "timeout")
	bios.bbcode_text += "\n"

	var checks = [
		["CPU", "RASPBERRY PI 4B @ 2.0GHz", "00ff41"],
		["GPU", "VIDEOCORE VI", "00ff41"],
		["OS", "DEBIAN 12 BOOKWORM", "00ff41"],
		["ROOT", root_path.substr(0, 30), "00ffff"],
	]
	for check in checks:
		var line = "[color=#888888]" + check[0] + "                ".substr(0, 12-check[0].length()) + "[/color]  [color=#" + check[2] + "]" + check[1] + "[/color]\n"
		for c in line:
			bios.bbcode_text += c
			yield(get_tree().create_timer(0.005), "timeout")
	
	bios.bbcode_text += "\n[color=#00ffff]ALL SYSTEMS NOMINAL.[/color]\n"
	yield(get_tree().create_timer(0.4), "timeout")
	
	logo.rect_scale = Vector2(0.1, 0.1); logo.modulate.a = 0
	tween.interpolate_property(bios, "modulate:a", 1.0, 0.0, 0.3); tween.start()
	yield(tween, "tween_all_completed")
	tween.interpolate_property(logo, "rect_scale", Vector2(0.1, 0.1), Vector2(1.0, 1.0), 0.5, Tween.TRANS_BACK, Tween.EASE_OUT)
	tween.interpolate_property(logo, "modulate:a", 0.0, 1.0, 0.3); tween.start()
	yield(tween, "tween_all_completed")
	yield(get_tree().create_timer(0.5), "timeout")
	
	tween.interpolate_property(boot_screen, "modulate:a", 1.0, 0.0, 0.5); tween.start()
	yield(tween, "tween_all_completed")
	Global.has_booted = true; boot_screen.hide(); main_ui.show()
	if games_grid.get_child_count() > 0: games_grid.get_child(0).grab_focus()

func launch_game(game_name, index):
	if is_launching: return
	is_launching = true; Global.last_focused_game_index = index
	var info = game_paths[game_name]
	if info.has("scene"):
		get_tree().change_scene(info["scene"]); is_launching = false; return
	
	var lo = $MainUI/LoadingOverlay; lo.show(); var pb = lo.get_node("FakeLoadingBar"); var lbl = lo.get_node("LoadingLabel")
	pb.value = 0; lbl.text = "INITIALIZING " + game_name.to_upper() + "..."
	_perform_actual_launch(game_name)
	
	var start_time = OS.get_ticks_msec()
	while true:
		var elapsed = OS.get_ticks_msec() - start_time
		pb.value = min(99.0, (elapsed / 3000.0) * 100.0)
		if File.new().file_exists("/tmp/arcade_ready"):
			pb.value = 100.0; lbl.text = "READY!"; break
		if elapsed >= 8000: break
		yield(get_tree(), "idle_frame")
	yield(get_tree().create_timer(0.5), "timeout"); lo.hide(); is_launching = false

func _perform_actual_launch(game_name):
	if File.new().file_exists("/tmp/arcade_ready"): Directory.new().remove("/tmp/arcade_ready")
	var info = game_paths[game_name]; var abs_path = root_path.plus_file(info["path"])
	var wrapper = root_path.plus_file("utilities/pause_wrapper/wrapper.py")
	var python = "python3"; var inner_cmd = ""
	if abs_path.ends_with(".py"): inner_cmd = python + " \"" + abs_path + "\""
	elif abs_path.ends_with(".sh"): inner_cmd = "bash \"" + abs_path + "\""
	else: inner_cmd = "\"" + abs_path + "\""
	OS.execute(python, [wrapper, inner_cmd], false)

func _process(delta):
	if clock_label:
		var t = OS.get_time(); clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]
	
	# Joystick deadzone
	var joy_x = Input.get_joy_axis(0, JOY_AXIS_0); var joy_y = Input.get_joy_axis(0, JOY_AXIS_1)
	var deadzone = 0.4
	if abs(joy_x) > deadzone or abs(joy_y) > deadzone:
		if not _joystick_held:
			_joystick_held = true
			if joy_x > deadzone: _move_focus(1, 0)
			elif joy_x < -deadzone: _move_focus(-1, 0)
			elif joy_y > deadzone: _move_focus(0, 1)
			elif joy_y < -deadzone: _move_focus(0, -1)
	else: _joystick_held = false

	# Attract timer
	if _attract_timer > 0:
		_attract_timer -= delta
		if _attract_timer <= 0: _show_attract_mode()

	# Border cycling for focused button
	var focus = get_focus_owner()
	if focus and focus is Button:
		var style = focus.get("custom_styles/focus")
		if style:
			var pulse = (sin(OS.get_ticks_msec() * 0.005) + 1.0) / 2.0
			style.border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)

func _move_focus(dx, dy):
	var focus = get_focus_owner()
	if not focus: return
	var idx = focus.get_index(); var total = games_grid.get_child_count(); var cols = games_grid.columns
	var row = idx / cols; var col = idx % cols
	var next_row = row + dy; var next_col = col + dx
	if next_row < 0 or next_row >= (total + cols - 1) / cols: return
	if next_col < 0 or next_col >= cols: return
	var next_idx = next_row * cols + next_col
	if next_idx < total: games_grid.get_child(next_idx).grab_focus()

func _on_btn_focus_entered(btn, game_name):
	attract_overlay.hide(); _attract_timer = _ATTRACT_DELAY
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.1,1.1), 0.1); tw.start()

func _on_btn_focus_exited(btn):
	_attract_timer = 0; attract_overlay.hide()
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1.1,1.1), Vector2(1,1), 0.1); tw.start()

func _show_attract_mode():
	var focus = get_focus_owner()
	if not focus: return
	var game_name = game_paths.keys()[focus.get_index()]
	if game_info.has(game_name):
		var info = game_info[game_name]
		attract_overlay.get_node("VBox/GameTitle").text = game_name.to_upper()
		attract_overlay.get_node("VBox/Desc").text = info.description
		attract_overlay.get_node("VBox/Controls").text = info.controls
		attract_overlay.show()

func _on_AboutButton_pressed(): OS.alert("CTRL ARCADE v7.0\nCreated by Antigravity", "About")
func _on_SystemInfoButton_pressed(): OS.alert("OS: " + OS.get_name() + "\nRoot: " + root_path, "System Info")
func toggle_debug_menu(): debug_menu.visible = !debug_menu.visible
func load_external_texture(path):
	var img = Image.new(); if img.load(ProjectSettings.globalize_path(path)) == OK:
		var tex = ImageTexture.new(); tex.create_from_image(img, 0); return tex
	return null
