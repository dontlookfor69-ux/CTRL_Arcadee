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

# Flag file paths written by wrapper.py
const FLAG_READY = "/tmp/arcade_ready"
const FLAG_DONE  = "/tmp/arcade_done"

func _ready():
	_detect_root_path()
	_load_game_info()
	main_ui.hide(); boot_screen.show()
	_build_game_buttons()
	_build_loading_bar()
	_safe_connect_debug_buttons()
	_connect_input_debug_button()

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
			Global.root_path = root_path
			return
		check_path = check_path.get_base_dir()
	root_path = "/home/ctrl/Desktop/CTRL_Arcadee"
	Global.root_path = root_path
	push_warning("[main] root_path fallback used — check project layout")

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
		var tex = _load_texture_safe(game_paths[game_name]["icon"])
		if tex:
			var ir = TextureRect.new()
			ir.texture = tex; ir.expand = true; ir.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			ir.anchor_left = 0.5; ir.anchor_top = 0.4; ir.anchor_right = 0.5; ir.anchor_bottom = 0.4
			ir.margin_left = -70; ir.margin_right = 70; ir.margin_top = -70; ir.margin_bottom = 70
			btn.add_child(ir)
		var lbl = Label.new()
		lbl.text = game_name.to_upper(); lbl.align = Label.ALIGN_CENTER
		lbl.anchor_top = 0.8; lbl.anchor_bottom = 0.8; lbl.anchor_right = 1.0
		btn.add_child(lbl)
		var tw = Tween.new(); tw.name = "HoverTween"; btn.add_child(tw)
		btn.connect("pressed", self, "launch_game", [game_name, i])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn, game_name])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		games_grid.add_child(btn)
		i += 1

func _load_texture_safe(path: String) -> Texture:
	# ResourceLoader works in both editor AND exported builds.
	# The old Image.load(globalize_path(...)) silently fails in exported packs.
	if ResourceLoader.exists(path):
		var tex = ResourceLoader.load(path)
		if tex is Texture:
			return tex
	# Fallback for truly external paths (outside res://)
	var img = Image.new()
	var abs_path = ProjectSettings.globalize_path(path)
	if img.load(abs_path) == OK:
		var tex = ImageTexture.new()
		tex.create_from_image(img, 0)
		return tex
	push_warning("[main] Could not load icon: " + path)
	return null

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
	var vbox = $MainUI/DebugMenu/VBoxContainer
	var cb = vbox.get_node_or_null("CloseButton")
	if cb:
		# Remove any stale .tscn connection first to avoid double-firing
		if cb.is_connected("pressed", self, "_on_CloseDebugButton_pressed"):
			cb.disconnect("pressed", self, "_on_CloseDebugButton_pressed")
		if not cb.is_connected("pressed", self, "toggle_debug_menu"):
			cb.connect("pressed", self, "toggle_debug_menu")
	var sib = vbox.get_node_or_null("SystemInfoButton")
	if sib and not sib.is_connected("pressed", self, "_on_SystemInfoButton_pressed"):
		sib.connect("pressed", self, "_on_SystemInfoButton_pressed")

func _connect_input_debug_button():
	# This button existed in the scene but had no connection — now it works.
	var idb = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("InputDebugButton")
	if idb and not idb.is_connected("pressed", self, "_on_InputDebugButton_pressed"):
		idb.connect("pressed", self, "_on_InputDebugButton_pressed")

func play_boot_sequence():
	if Global.has_booted:
		boot_screen.hide(); main_ui.show()
		if games_grid.get_child_count() > 0:
			games_grid.get_child(Global.last_focused_game_index).grab_focus()
		return

	var bios  = $BootScreen/BiosText
	var tween = $BootScreen/BootTween
	var crt   = $BootScreen/CRTScreen
	var logo  = $BootScreen/BootLogo

	boot_screen.color = Color(0,0,0,1)
	bios.modulate.a   = 0
	logo.modulate.a   = 0
	bios.bbcode_text  = ""
	crt.rect_scale    = Vector2(1, 0.02)
	crt.rect_pivot_offset = Vector2(960, 540)

	tween.interpolate_property(crt, "rect_scale", Vector2(1, 0.02), Vector2(1, 1), 0.4, Tween.TRANS_EXPO, Tween.EASE_OUT)
	tween.start()
	yield(tween, "tween_all_completed")

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
		["GPU", "VIDEOCORE VI",              "00ff41"],
		["OS",  "DEBIAN 12 BOOKWORM",        "00ff41"],
		["ROOT", root_path.substr(0, 30),    "00ffff"],
	]
	for check in checks:
		var line = "[color=#888888]" + check[0] + "                ".substr(0, 12-check[0].length()) + "[/color]  [color=#" + check[2] + "]" + check[1] + "[/color]\n"
		for c in line:
			bios.bbcode_text += c
			yield(get_tree().create_timer(0.005), "timeout")

	bios.bbcode_text += "\n[color=#00ffff]ALL SYSTEMS NOMINAL.[/color]\n"
	yield(get_tree().create_timer(0.4), "timeout")

	logo.rect_scale    = Vector2(0.1, 0.1)
	logo.modulate.a    = 0
	tween.interpolate_property(bios, "modulate:a", 1.0, 0.0, 0.3)
	tween.start()
	yield(tween, "tween_all_completed")

	tween.interpolate_property(logo, "rect_scale",  Vector2(0.1, 0.1), Vector2(1.0, 1.0), 0.5, Tween.TRANS_BACK, Tween.EASE_OUT)
	tween.interpolate_property(logo, "modulate:a",  0.0, 1.0, 0.3)
	tween.start()
	yield(tween, "tween_all_completed")
	yield(get_tree().create_timer(0.5), "timeout")

	tween.interpolate_property(boot_screen, "modulate:a", 1.0, 0.0, 0.5)
	tween.start()
	yield(tween, "tween_all_completed")

	Global.has_booted = true
	boot_screen.hide()
	main_ui.show()
	if games_grid.get_child_count() > 0:
		games_grid.get_child(0).grab_focus()

# ── Game Launch ───────────────────────────────────────────────────────────────
func launch_game(game_name: String, index: int):
	if is_launching: return
	is_launching = true
	Global.last_focused_game_index = index

	var info = game_paths[game_name]

	# Scene-based apps (Media Player etc.) — just switch scene
	if info.has("scene"):
		get_tree().change_scene(info["scene"])
		is_launching = false
		return

	# ── Clean up any leftover flag files from a previous run ─────────────────
	var dir = Directory.new()
	for flag in [FLAG_READY, FLAG_DONE]:
		if File.new().file_exists(flag):
			dir.remove(flag)

	# ── Show loading overlay ──────────────────────────────────────────────────
	var lo  = $MainUI/LoadingOverlay
	var pb  = lo.get_node("FakeLoadingBar")
	var lbl = lo.get_node("LoadingLabel")
	pb.value  = 0
	lbl.text  = "LAUNCHING " + game_name.to_upper() + "..."
	lo.show()

	# ── Launch the game via wrapper.py ────────────────────────────────────────
	_perform_actual_launch(game_name)

	# ── Phase 1: wait for wrapper to signal the game process has started ──────
	# Uses a 50 ms timer instead of idle_frame to avoid burning CPU at 60 Hz.
	var start_ms  = OS.get_ticks_msec()
	var TIMEOUT_MS = 15000   # 15 seconds max (Undertale / box64 can be slow)
	var got_ready  = false

	while true:
		var elapsed = OS.get_ticks_msec() - start_ms
		pb.value = min(90.0, float(elapsed) / float(TIMEOUT_MS) * 90.0)

		if File.new().file_exists(FLAG_READY):
			got_ready = true
			dir.remove(FLAG_READY)
			break

		if elapsed >= TIMEOUT_MS:
			break

		yield(get_tree().create_timer(0.05), "timeout")

	if not got_ready:
		lbl.text = "LAUNCH FAILED — check logs"
		yield(get_tree().create_timer(2.5), "timeout")
		lo.hide()
		is_launching = false
		return

	# Brief pause so the game window has time to fully draw its first frame
	pb.value = 100.0
	lbl.text  = "STARTING..."
	yield(get_tree().create_timer(0.6), "timeout")
	lo.hide()

	# ── Minimise Godot so the game window can come to the foreground ──────────
	# Without this, Godot's fullscreen window sits on top and hides the game.
	OS.set_window_minimized(true)

	# ── Phase 2: wait for wrapper to signal the game has exited ──────────────
	while true:
		if File.new().file_exists(FLAG_DONE):
			dir.remove(FLAG_DONE)
			break
		yield(get_tree().create_timer(0.5), "timeout")

	# ── Restore Godot to fullscreen and give focus back to the menu ───────────
	OS.set_window_minimized(false)
	OS.set_window_fullscreen(true)
	yield(get_tree().create_timer(0.15), "timeout")

	if games_grid.get_child_count() > 0:
		games_grid.get_child(Global.last_focused_game_index).grab_focus()

	is_launching = false

func _perform_actual_launch(game_name: String):
	var info     = game_paths[game_name]
	var abs_path = root_path.plus_file(info["path"])
	var wrapper  = root_path.plus_file("utilities/pause_wrapper/wrapper.py")
	var python   = "python3"
	var inner_cmd = ""

	if abs_path.ends_with(".py"):
		inner_cmd = python + " \"" + abs_path + "\""
	elif abs_path.ends_with(".sh"):
		inner_cmd = "bash \"" + abs_path + "\""
	else:
		inner_cmd = "\"" + abs_path + "\""

	OS.execute(python, [wrapper, inner_cmd], false)

# ── Input / Navigation ────────────────────────────────────────────────────────
func _process(delta):
	if clock_label:
		var t = OS.get_time()
		clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]

	var joy_x   = Input.get_joy_axis(0, JOY_AXIS_0)
	var joy_y   = Input.get_joy_axis(0, JOY_AXIS_1)
	var deadzone = 0.4
	if abs(joy_x) > deadzone or abs(joy_y) > deadzone:
		if not _joystick_held:
			_joystick_held = true
			if joy_x > deadzone:   _move_focus( 1, 0)
			elif joy_x < -deadzone: _move_focus(-1, 0)
			elif joy_y > deadzone:  _move_focus( 0, 1)
			elif joy_y < -deadzone: _move_focus( 0,-1)
	else:
		_joystick_held = false

	if _attract_timer > 0:
		_attract_timer -= delta
		if _attract_timer <= 0: _show_attract_mode()

	var focus = get_focus_owner()
	if focus and focus is Button:
		var style = focus.get("custom_styles/focus")
		if style:
			var pulse = (sin(OS.get_ticks_msec() * 0.005) + 1.0) / 2.0
			style.border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)

func _move_focus(dx: int, dy: int):
	var focus = get_focus_owner()
	if not focus: return
	var idx   = focus.get_index()
	var total = games_grid.get_child_count()
	var cols  = games_grid.columns
	var row   = idx / cols
	var col   = idx % cols
	var nr    = row + dy
	var nc    = col + dx
	if nr < 0 or nr >= (total + cols - 1) / cols: return
	if nc < 0 or nc >= cols: return
	var next_idx = nr * cols + nc
	if next_idx < total: games_grid.get_child(next_idx).grab_focus()

func _on_btn_focus_entered(btn, game_name: String):
	attract_overlay.hide()
	_set_shaders_visible(true)
	_attract_timer = _ATTRACT_DELAY
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.1,1.1), 0.1); tw.start()

func _on_btn_focus_exited(btn):
	_attract_timer = 0
	attract_overlay.hide()
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1.1,1.1), Vector2(1,1), 0.1); tw.start()

func _show_attract_mode():
	var focus = get_focus_owner()
	if not focus: return
	var game_name = game_paths.keys()[focus.get_index()]
	if game_info.has(game_name):
		var info = game_info[game_name]
		attract_overlay.get_node("VBox/GameTitle").text = game_name.to_upper()
		attract_overlay.get_node("VBox/Desc").text      = info.description
		attract_overlay.get_node("VBox/Controls").text  = info.controls
		attract_overlay.show()
		_set_shaders_visible(false)

func _set_shaders_visible(visible: bool):
	var barrel = get_node_or_null("CRT_Barrel")
	var scanlines = get_node_or_null("CRT_Scanlines")
	if barrel: barrel.visible = visible
	if scanlines: scanlines.visible = visible

func _input(event):
	if input_debug_overlay.visible:
		var log_label = input_debug_overlay.get_node("Scroll/LogLabel")
		var text = ""
		if event is InputEventKey:
			text = "KEY: " + str(event.scancode) + " (" + OS.get_scancode_string(event.scancode) + ") " + ("PRESSED" if event.pressed else "RELEASED")
		elif event is InputEventJoypadButton:
			text = "JOY_BTN: " + str(event.button_index) + " " + ("PRESSED" if event.pressed else "RELEASED")
		elif event is InputEventJoypadMotion:
			if abs(event.axis_value) > 0.2:
				text = "JOY_AXIS: " + str(event.axis_index) + " VALUE: " + str(stepify(event.axis_value, 0.01))
		
		if text != "":
			log_label.text += text + "\n"
			var scroll = input_debug_overlay.get_node("Scroll")
			yield(get_tree(), "idle_frame")
			scroll.scroll_vertical = 99999
		
		if event.is_action_pressed("ui_cancel") or (event is InputEventJoypadButton and event.button_index == 0 and event.pressed):
			_on_InputDebugButton_pressed()

# ── Button Handlers ───────────────────────────────────────────────────────────
func _on_AboutButton_pressed():
	OS.alert("CTRL ARCADE v7.0\nCreated by Antigravity", "About")

func _on_SystemInfoButton_pressed():
	OS.alert("OS: " + OS.get_name() + "\nRoot: " + root_path, "System Info")

func _on_InputDebugButton_pressed():
	toggle_debug_menu()
	input_debug_overlay.visible = !input_debug_overlay.visible
	_set_shaders_visible(!input_debug_overlay.visible)
	if input_debug_overlay.visible:
		input_debug_overlay.get_node("Scroll/LogLabel").text = "--- HARDWARE INPUT DEBUGGER ---\n"

func toggle_debug_menu():
	debug_menu.visible = !debug_menu.visible
	_set_shaders_visible(!debug_menu.visible)

# Kept for backward compatibility (the .tscn still references this name)
func _on_CloseDebugButton_pressed():
	toggle_debug_menu()
