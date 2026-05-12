extends Control

# ── Global State ─────────────────────────────────────────────────────────────
var is_launching   = false
var is_input_debugger_active = false
var root_path      = ""
var _joystick_held = false
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
	_build_controls_bar()
	_safe_connect_debug_buttons()
	_connect_input_debug_button()
	
	# Attract mode is permanently disabled per requirements
	attract_overlay.hide()

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
		var info = game_paths[game_name]
		var btn = Button.new()
		btn.rect_min_size = Vector2(220, 260); btn.focus_mode = Control.FOCUS_ALL
		btn.rect_pivot_offset = Vector2(110, 130)
		
		# [NEW] Check if game is installed
		var is_installed = true
		if info.has("path"):
			var abs_p = root_path.plus_file(info["path"])
			if not File.new().file_exists(abs_p):
				is_installed = false
		
		var fs = StyleBoxFlat.new()
		fs.bg_color = Color(0,0,0,0.9) if is_installed else Color(0.1, 0, 0, 0.9)
		fs.border_color = C_ACCENT if is_installed else Color(0.4, 0.1, 0.1)
		fs.set_border_width_all(4)
		btn.set("custom_styles/normal", fs); btn.set("custom_styles/focus", fs); btn.set("custom_styles/hover", fs)
		
		var tex = _load_texture_safe(info["icon"])
		if tex:
			var ir = TextureRect.new()
			ir.texture = tex; ir.expand = true; ir.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			ir.anchor_left = 0.5; ir.anchor_top = 0.4; ir.anchor_right = 0.5; ir.anchor_bottom = 0.4
			ir.margin_left = -70; ir.margin_right = 70; ir.margin_top = -70; ir.margin_bottom = 70
			if not is_installed: ir.modulate = Color(0.3, 0.3, 0.3)
			btn.add_child(ir)
		
		var lbl = Label.new()
		lbl.text = game_name.to_upper(); lbl.align = Label.ALIGN_CENTER
		lbl.anchor_top = 0.8; lbl.anchor_bottom = 0.8; lbl.anchor_right = 1.0
		if not is_installed: lbl.modulate = Color(0.6, 0.2, 0.2)
		btn.add_child(lbl)
		
		if not is_installed:
			var ni = Label.new()
			ni.text = "NOT INSTALLED"; ni.align = Label.ALIGN_CENTER
			ni.anchor_top = 0.5; ni.anchor_bottom = 0.5; ni.anchor_right = 1.0
			ni.add_color_override("font_color", Color(1, 0, 0))
			btn.add_child(ni)

		var tw = Tween.new(); tw.name = "HoverTween"; btn.add_child(tw)
		btn.connect("pressed", self, "launch_game", [game_name, i])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn, game_name])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		games_grid.add_child(btn)
		i += 1

func _build_controls_bar():
	var bar = Label.new()
	bar.name = "ControlsBar"
	bar.text = "JOYSTICK: Navigate    A / Button 1: Launch    Double-ESC: Pause Menu"
	bar.align = Label.ALIGN_CENTER
	bar.valign = Label.VALIGN_CENTER
	bar.anchor_top = 1.0; bar.anchor_bottom = 1.0; bar.anchor_right = 1.0
	bar.margin_top = -60; bar.margin_bottom = 0
	
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0.7); sb.set_border_width_all(2); sb.border_color = C_ACCENT
	bar.add_stylebox_override("normal", sb)
	bar.add_color_override("font_color", C_LIME)
	main_ui.add_child(bar)

func _load_texture_safe(path: String) -> Texture:
	if ResourceLoader.exists(path):
		var tex = ResourceLoader.load(path)
		if tex is Texture: return tex
	var img = Image.new()
	var abs_path = ProjectSettings.globalize_path(path)
	if img.load(abs_path) == OK:
		var tex = ImageTexture.new()
		tex.create_from_image(img, 0)
		return tex
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
		if cb.is_connected("pressed", self, "_on_CloseDebugButton_pressed"):
			cb.disconnect("pressed", self, "_on_CloseDebugButton_pressed")
		if not cb.is_connected("pressed", self, "toggle_debug_menu"):
			cb.connect("pressed", self, "toggle_debug_menu")
	var sib = vbox.get_node_or_null("SystemInfoButton")
	if sib and not sib.is_connected("pressed", self, "_on_SystemInfoButton_pressed"):
		sib.connect("pressed", self, "_on_SystemInfoButton_pressed")

func _connect_input_debug_button():
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

	# ── [NEW] Set BIOS Font Size ───────────────────────────────────────────
	var df = DynamicFont.new()
	# Try to find a font file, fallback to default but large
	var font_paths = ["res://assets/fonts/Px437_IBM_VGA_8x16.ttf", "res://assets/fonts/vga.ttf"]
	for p in font_paths:
		if ResourceLoader.exists(p):
			df.font_data = load(p)
			break
	df.size = 20
	bios.add_font_override("normal_font", df)

	# ── [NEW] TV Power-On Effect ──────────────────────────────────────────
	boot_screen.color = Color(1, 1, 1, 1) # White flash
	yield(get_tree().create_timer(0.08), "timeout")
	tween.interpolate_property(boot_screen, "color", Color(1,1,1,1), Color(0,0,0,1), 0.15)
	tween.start()
	yield(tween, "tween_all_completed")

	# Initial CRT horizontal line grow
	crt.rect_scale = Vector2(1, 0.02); crt.rect_pivot_offset = Vector2(960, 540)
	tween.interpolate_property(crt, "rect_scale", Vector2(1, 0.02), Vector2(1, 1), 0.3, Tween.TRANS_EXPO, Tween.EASE_OUT)
	tween.start()
	yield(tween, "tween_all_completed")
	
	# Static Noise Iterations
	for i in range(8):
		boot_screen.color = Color(0.1, 0.1, 0.1, 1) if i % 2 == 0 else Color(0,0,0,1)
		yield(get_tree().create_timer(0.03), "timeout")
	boot_screen.color = Color(0,0,0,1)

	bios.modulate.a = 1; bios.bbcode_text = ""
	var bios_lines = [
		"[color=#00ff41]██████╗ ██████╗ ██╗  ████████╗[/color]",
		"[color=#00ff41]██╔════╝╚══██╔╝ ██║  ╚══██╔══╝[/color]",
		"[color=#00ff41]██║       ██║  ██║     ██║[/color]",
		"[color=#00ff41]╚██████╗ ██████╔╝ ███████╗██║[/color]",
		"[color=#00ff41] ╚═════╝ ╚═════╝  ╚══════╝╚═╝   [color=#00ffff]ARCADE[/color][/color]",
		"",
		"[color=#aaaaaa]BIOS v8.0  |  2026 CTRL Systems[/color]",
		"",
	]
	# Fast BIOS Typing
	for line in bios_lines:
		bios.bbcode_text += line + "\n"
		yield(get_tree().create_timer(0.001), "timeout")

	bios.bbcode_text += "MEMORY CHECK: "
	var mem = 0
	while mem < 8192:
		mem += 512
		var t = bios.bbcode_text.split("MEMORY CHECK: ")[0] + "MEMORY CHECK: " + str(mem) + "MB OK"
		bios.bbcode_text = t
		yield(get_tree().create_timer(0.003), "timeout")
	bios.bbcode_text += "\n"

	# ── [NEW] Fast-Scrolling System Logs ──────────────────────────────────
	var logs = [
		"Initializing kernel modules...", "USB 1-1: New high-speed device found",
		"snd_bcm2835: audio initialized", "vc4-drm: display pipeline ready",
		"EXT4-fs: mounted root partition", "Switching to VT 7...",
		"Godot Engine v3.x startup...", "Loading asset packs...",
		"Optimizing GLES2 shaders...", "Input mapping: Arcade Stick 1",
		"Handshake with wrapper.py OK", "Checking /tmp/arcade_ready..."
	]
	for i in range(30):
		var log_line = "[color=#666666]LOG [" + str(i) + "]: " + logs[i % logs.size()] + "[/color]\n"
		bios.bbcode_text += log_line
		yield(get_tree().create_timer(0.001), "timeout")

	# Fetch Real CPU Info
	var cpu_out = []
	OS.execute("bash", ["-c", "cat /proc/cpuinfo | grep 'Model' | head -1 | cut -d: -f2"], true, cpu_out)
	var cpu_model = cpu_out[0].strip_edges() if cpu_out.size() > 0 else "RASPBERRY PI 4B"

	var checks = [
		["CPU", cpu_model,                    "00ff41"],
		["GPU", "VIDEOCORE VI",              "00ff41"],
		["OS",  "DEBIAN 12 BOOKWORM",        "00ff41"],
		["ROOT", root_path.substr(0, 30),    "00ffff"],
	]
	# Slow Dramatic Table
	for check in checks:
		var line = "[color=#888888]" + check[0] + "                ".substr(0, 12-check[0].length()) + "[/color]  [color=#" + check[2] + "]" + check[1] + "[/color]\n"
		for c in line:
			bios.bbcode_text += c
			yield(get_tree().create_timer(0.005), "timeout")

	bios.bbcode_text += "\n[color=#00ffff]ALL SYSTEMS NOMINAL.[/color]\n"
	yield(get_tree().create_timer(0.4), "timeout")

	logo.rect_scale = Vector2(0.1, 0.1); logo.modulate.a = 0
	tween.interpolate_property(bios, "modulate:a", 1.0, 0.0, 0.2)
	tween.start()
	yield(tween, "tween_all_completed")

	tween.interpolate_property(logo, "rect_scale",  Vector2(0.1, 0.1), Vector2(1.0, 1.0), 0.4, Tween.TRANS_BACK, Tween.EASE_OUT)
	tween.interpolate_property(logo, "modulate:a",  0.0, 1.0, 0.2)
	tween.start()
	yield(tween, "tween_all_completed")
	yield(get_tree().create_timer(0.3), "timeout")

	tween.interpolate_property(boot_screen, "modulate:a", 1.0, 0.0, 0.4)
	tween.start()
	yield(tween, "tween_all_completed")

	Global.has_booted = true
	boot_screen.hide(); main_ui.show()
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

	# [NEW] Check for game existence
	var abs_path = root_path.plus_file(info["path"])
	if not File.new().file_exists(abs_path):
		OS.alert("Game not installed: " + game_name + "\nPlease check README for setup instructions.", "Error")
		is_launching = false
		return

	# ── [NEW] Transition: Blackout instead of Minimize ─────────────────────
	_set_ui_visible(false)
	_set_shaders_visible(false)

	var dir = Directory.new()
	for flag in [FLAG_READY, FLAG_DONE]:
		if File.new().file_exists(flag): dir.remove(flag)

	var lo  = $MainUI/LoadingOverlay
	var pb  = lo.get_node("FakeLoadingBar"); var lbl = lo.get_node("LoadingLabel")
	pb.value = 0; lbl.text = "LAUNCHING " + game_name.to_upper() + "..."; lo.show()

	_perform_actual_launch(game_name)

	var start_ms = OS.get_ticks_msec(); var TIMEOUT_MS = 15000; var got_ready = false
	while true:
		var elapsed = OS.get_ticks_msec() - start_ms
		pb.value = min(90.0, float(elapsed) / float(TIMEOUT_MS) * 90.0)
		if File.new().file_exists(FLAG_READY):
			got_ready = true; dir.remove(FLAG_READY); break
		if elapsed >= TIMEOUT_MS: break
		yield(get_tree().create_timer(0.05), "timeout")

	if not got_ready:
		lbl.text = "LAUNCH FAILED"; yield(get_tree().create_timer(2.0), "timeout")
		lo.hide(); _set_ui_visible(true); is_launching = false
		return

	pb.value = 100.0; lbl.text = "STARTING..."; yield(get_tree().create_timer(0.6), "timeout")
	lo.hide()

	# ── [NEW] Focus management with xdotool ────────────────────────────────
	# Ensure the game window gets input focus without disturbing Godot
	OS.execute("bash", ["-c", "xdotool search --pid $(pgrep -f 'python3.*wrapper') windowfocus 2>/dev/null || true"], false)

	# ── Wait for game exit ──────────────────────────────────────────────────
	while true:
		if File.new().file_exists(FLAG_DONE):
			dir.remove(FLAG_DONE); break
		yield(get_tree().create_timer(0.5), "timeout")

	# ── Restore UI ─────────────────────────────────────────────────────────
	_set_ui_visible(true)
	_set_shaders_visible(true)
	yield(get_tree().create_timer(0.1), "timeout")
	if games_grid.get_child_count() > index:
		games_grid.get_child(index).grab_focus()
	is_launching = false

func _perform_actual_launch(game_name: String):
	var info = game_paths[game_name]; var abs_path = root_path.plus_file(info["path"])
	var wrapper = root_path.plus_file("utilities/pause_wrapper/wrapper.py")
	var inner_cmd = ""
	if abs_path.ends_with(".py"): inner_cmd = "python3 \"" + abs_path + "\""
	elif abs_path.ends_with(".sh"): inner_cmd = "bash \"" + abs_path + "\""
	else: inner_cmd = "\"" + abs_path + "\""
	OS.execute("python3", [wrapper, inner_cmd], false)

func _set_ui_visible(visible: bool):
	main_ui.visible = visible
	$MainUI/Header.visible = visible
	$MainUI/GamesCenter.visible = visible
	# Keep the background black when UI is hidden

# ── Input / Navigation ────────────────────────────────────────────────────────
func _process(delta):
	if clock_label:
		var t = OS.get_time(); clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]
	var joy_x = Input.get_joy_axis(0, JOY_AXIS_0); var joy_y = Input.get_joy_axis(0, JOY_AXIS_1)
	if abs(joy_x) > 0.4 or abs(joy_y) > 0.4:
		if not _joystick_held:
			_joystick_held = true
			if joy_x > 0.4: _move_focus(1, 0)
			elif joy_x < -0.4: _move_focus(-1, 0)
			elif joy_y > 0.4: _move_focus(0, 1)
			elif joy_y < -0.4: _move_focus(0,-1)
	else: _joystick_held = false

	var focus = get_focus_owner()
	if focus and focus is Button:
		var style = focus.get("custom_styles/focus")
		if style:
			var pulse = (sin(OS.get_ticks_msec() * 0.005) + 1.0) / 2.0
			style.border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)

func _move_focus(dx: int, dy: int):
	var focus = get_focus_owner()
	if not focus: return
	var idx = focus.get_index(); var total = games_grid.get_child_count(); var cols = games_grid.columns
	var nr = (idx / cols) + dy; var nc = (idx % cols) + dx
	if nr < 0 or nr >= (total + cols - 1) / cols or nc < 0 or nc >= cols: return
	var next_idx = nr * cols + nc
	if next_idx < total: games_grid.get_child(next_idx).grab_focus()

func _on_btn_focus_entered(btn, game_name: String):
	_set_shaders_visible(true)
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.1,1.1), 0.1); tw.start()

func _on_btn_focus_exited(btn):
	var tw = btn.get_node_or_null("HoverTween")
	if tw: tw.interpolate_property(btn, "rect_scale", Vector2(1.1,1.1), Vector2(1,1), 0.1); tw.start()

func _show_attract_mode():
	pass # Disabled per Phase 2 requirements

func _set_shaders_visible(visible: bool):
	var barrel = get_node_or_null("CRT_Barrel")
	var scanlines = get_node_or_null("CRT_Scanlines")
	if barrel: barrel.visible = visible
	if scanlines: scanlines.visible = visible

func _input(event):
	if input_debug_overlay.visible:
		var log_label = input_debug_overlay.get_node("Scroll/LogLabel"); var text = ""
		if event is InputEventKey:
			text = "KEY: " + str(event.scancode) + " (" + OS.get_scancode_string(event.scancode) + ") " + ("PRESSED" if event.pressed else "RELEASED")
		elif event is InputEventJoypadButton:
			text = "JOY_BTN: " + str(event.button_index) + " " + ("PRESSED" if event.pressed else "RELEASED")
		elif event is InputEventJoypadMotion and abs(event.axis_value) > 0.2:
			text = "JOY_AXIS: " + str(event.axis_index) + " VALUE: " + str(stepify(event.axis_value, 0.01))
		if text != "":
			log_label.text += text + "\n"
			var scroll = input_debug_overlay.get_node("Scroll")
			yield(get_tree(), "idle_frame"); scroll.scroll_vertical = 99999
		if event.is_action_pressed("ui_cancel") or (event is InputEventJoypadButton and event.button_index == 0 and event.pressed):
			_on_InputDebugButton_pressed()

func _on_AboutButton_pressed():
	OS.alert("CTRL ARCADE v8.0\nCreated by Antigravity", "About")
func _on_SystemInfoButton_pressed():
	OS.alert("OS: " + OS.get_name() + "\nRoot: " + root_path, "System Info")
func _on_InputDebugButton_pressed():
	toggle_debug_menu(); input_debug_overlay.visible = !input_debug_overlay.visible
	_set_shaders_visible(!input_debug_overlay.visible)
	if input_debug_overlay.visible: input_debug_overlay.get_node("Scroll/LogLabel").text = "--- HARDWARE INPUT DEBUGGER ---\n"
func toggle_debug_menu():
	debug_menu.visible = !debug_menu.visible; _set_shaders_visible(!debug_menu.visible)
func _on_CloseDebugButton_pressed():
	toggle_debug_menu()
