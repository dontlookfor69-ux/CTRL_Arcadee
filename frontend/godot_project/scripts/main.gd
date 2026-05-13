extends Control

# ── Global State ─────────────────────────────────────────────────────────────
var is_launching = false
var is_input_debugger_active = false
var root_path = ""
var _joystick_held = false
var game_info = {}

onready var games_grid = $MainUI/GamesCenter/GamesGrid
onready var debug_menu = $MainUI/DebugMenu
onready var main_ui = $MainUI
onready var boot_screen = $BootScreen
onready var clock_label = $MainUI/Header/HBox/ClockLabel
onready var about_button = get_node_or_null("MainUI/Header/HBox/AboutButton")
onready var input_debug_overlay = $MainUI/InputDebugOverlay
onready var attract_overlay = $MainUI/AttractMode

var C_BG = Color(0.05, 0, 0, 1)
var C_ACCENT = Color(0.0, 1.0, 1.0, 1)
var C_LIME = Color(0.2, 1.0, 0.2, 1)
var C_NEON_GREEN = Color("#39FF14")

var game_paths = {
	"Pacman": {"path": "games/pacman/launch_pacman.sh", "icon": "res://assets/icons/pacman.png"},
	"Tetris": {"path": "games/tetris/main.py", "icon": "res://assets/icons/tetris.png"},
	"DOOM": {"path": "games/doom/launch_doom.sh", "icon": "res://assets/icons/doom.png"},
	"Undertale": {"path": "games/undertale/launch_undertale.sh", "icon": "res://assets/icons/undertale.png"},
	"Just Shapes & Beats": {"path": "games/just_shapes_and_beats/game.py", "icon": "res://assets/icons/Just_Shapes_And_Beats.png"},
	"Minecraft Pi": {"path": "games/minecraft_pi/launch_mcpi.sh", "icon": "res://assets/icons/minecraft.png"},
	"Etch A Sketch AI": {"path": "utilities/etch_a_sketch_ai/main.py", "icon": "res://assets/icons/etch_a_sketch.png"},
	"Media Player": {"scene": "res://scenes/media_player.tscn", "icon": "res://assets/icons/Media_Player.png"}
}

const FLAG_READY = "/tmp/arcade_ready"
const FLAG_DONE = "/tmp/arcade_done"

func _ready():
	_detect_root_path()
	_load_game_info()
	main_ui.hide()
	boot_screen.show()
	boot_screen.modulate.a = 1.0
	_build_return_overlay()
	_build_loading_bar()
	_safe_connect_debug_buttons()
	_connect_input_debug_button()
	attract_overlay.hide()
	if about_button:
		about_button.connect("pressed", self, "_on_AboutButton_pressed")
	call_deferred("play_boot_sequence")

func _load_game_info():
	var f = File.new()
	if f.open("res://assets/game_info.json", File.READ) == OK:
		var res = JSON.parse(f.get_as_text())
		if res.error == OK:
			game_info = res.result
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

func _build_game_buttons():
	for child in games_grid.get_children():
		child.queue_free()
	var i = 0
	for game_name in game_paths.keys():
		var info = game_paths[game_name]
		var btn = Button.new()
		btn.rect_min_size = Vector2(250, 250)
		btn.focus_mode = Control.FOCUS_ALL
		btn.rect_pivot_offset = Vector2(125, 125)
		var is_installed = true
		if info.has("path"):
			var abs_p = root_path.plus_file(info["path"])
			if not File.new().file_exists(abs_p):
				is_installed = false
		
		var fs = StyleBoxFlat.new()
		fs.bg_color = Color(0,0,0,0.95) if is_installed else Color(0.1, 0, 0, 0.95)
		fs.border_color = C_ACCENT
		fs.set_border_width_all(4)
		btn.add_stylebox_override("normal", fs)
		btn.add_stylebox_override("focus", fs)
		btn.add_stylebox_override("hover", fs)
		
		var ir = TextureRect.new()
		ir.name = "Icon"
		ir.expand = true; ir.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ir.anchor_left = 0.5; ir.anchor_top = 0.4; ir.anchor_right = 0.5; ir.anchor_bottom = 0.4
		ir.margin_left = -70; ir.margin_right = 70; ir.margin_top = -70; ir.margin_bottom = 70
		if not is_installed:
			ir.modulate = Color(0.3, 0.3, 0.3)
		if game_name == "Etch A Sketch AI":
			ir.modulate = Color(0.2, 0.2, 0.2)
		btn.add_child(ir)
		_deferred_load_icon(ir, info["icon"])
		
		var lbl = Label.new()
		lbl.text = game_name.to_upper(); lbl.align = Label.ALIGN_CENTER
		lbl.anchor_top = 0.8; lbl.anchor_bottom = 0.8; lbl.anchor_right = 1.0
		if not is_installed:
			lbl.modulate = Color(0.6, 0.2, 0.2)
		btn.add_child(lbl)
		
		var tw = Tween.new(); tw.name = "HoverTween"; btn.add_child(tw)
		btn.connect("pressed", self, "launch_game", [game_name, i])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn, game_name])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		games_grid.add_child(btn)
		i += 1

func _deferred_load_icon(ir, icon_path):
	yield(get_tree(), "idle_frame")
	var tex = _load_texture_safe(icon_path)
	if tex:
		ir.texture = tex

func _build_controls_bar():
	var old = main_ui.get_node_or_null("ControlsBar")
	if old:
		old.queue_free()
	var bar = Control.new(); bar.name = "ControlsBar"
	bar.anchor_top = 1.0; bar.anchor_bottom = 1.0; bar.anchor_right = 1.0
	bar.margin_top = -55; bar.margin_bottom = 0
	var bg = ColorRect.new(); bg.anchor_right = 1.0; bg.anchor_bottom = 1.0; bg.color = Color(0, 0, 0, 0.9)
	bar.add_child(bg)
	var line = ColorRect.new(); line.anchor_right = 1.0; line.margin_bottom = 2; line.color = C_ACCENT
	bar.add_child(line)
	var hbox = HBoxContainer.new(); hbox.anchor_right = 1.0; hbox.anchor_bottom = 1.0
	hbox.margin_left = 40; hbox.margin_right = -40; hbox.alignment = BoxContainer.ALIGN_CENTER
	hbox.add_constant_override("separation", 80)
	bar.add_child(hbox)
	var controls = [["🕹 NAVIGATE", "Arrows"], ["🔴 LAUNCH", "Button 1"], ["⎋ ⎋ EXIT", "Double ESC"]]
	for pair in controls:
		var vbox = VBoxContainer.new(); vbox.alignment = BoxContainer.ALIGN_CENTER
		var k = Label.new(); k.text = pair[0]; k.add_color_override("font_color", C_ACCENT); vbox.add_child(k)
		var d = Label.new(); d.text = pair[1]; d.add_color_override("font_color", Color(0.6,0.6,0.6)); vbox.add_child(d)
		hbox.add_child(vbox)
	main_ui.add_child(bar)

func _load_texture_safe(path: String) -> Texture:
	if ResourceLoader.exists(path):
		var tex = ResourceLoader.load(path)
		if tex is Texture:
			return tex
	var abs_p = root_path.plus_file(path) if not path.begins_with("res://") else ProjectSettings.globalize_path(path)
	var img = Image.new()
	if img.load(abs_p) == OK:
		var tex = ImageTexture.new(); tex.create_from_image(img); return tex
	return null

func _build_loading_bar():
	var lo = $MainUI/LoadingOverlay; if not lo: return
	for child in lo.get_children():
		child.queue_free()
	var flbl = Label.new(); flbl.name = "FlashLabel"; flbl.text = "LOADING..."
	flbl.anchor_left = 0.5; flbl.anchor_top = 0.45; flbl.anchor_right = 0.5; flbl.anchor_bottom = 0.45
	flbl.margin_left = -200; flbl.margin_right = 200; flbl.align = Label.ALIGN_CENTER
	var df = DynamicFont.new(); df.size = 32; flbl.add_font_override("font", df); lo.add_child(flbl)
	var frame = ColorRect.new(); frame.name = "Frame"; frame.color = Color(0, 1, 1, 0.2)
	frame.anchor_left = 0.5; frame.anchor_top = 0.6; frame.anchor_right = 0.5; frame.anchor_bottom = 0.6
	frame.margin_left = -300; frame.margin_right = 300; frame.margin_top = -15; frame.margin_bottom = 15
	lo.add_child(frame)
	var pb = ProgressBar.new(); pb.name = "FakeLoadingBar"; pb.anchor_right = 1.0; pb.anchor_bottom = 1.0
	var sb = StyleBoxFlat.new(); sb.bg_color = C_ACCENT; pb.add_stylebox_override("fg", sb)
	var bgs = StyleBoxFlat.new(); bgs.bg_color = Color(0,0,0,1); pb.add_stylebox_override("bg", bgs)
	pb.percent_visible = false; frame.add_child(pb)
	var lbl = Label.new(); lbl.name = "LoadingLabel"; lbl.anchor_left = 0.0; lbl.anchor_right = 1.0; lbl.anchor_top = 0.6
	lbl.margin_top = 30; lbl.align = Label.ALIGN_CENTER; lbl.add_color_override("font_color", C_NEON_GREEN); lo.add_child(lbl)

func _build_return_overlay():
	var old = get_node_or_null("ReturnOverlay"); if old:
		old.queue_free()
	var ro = ColorRect.new(); ro.name = "ReturnOverlay"; ro.color = Color(0, 0, 0, 1)
	ro.anchor_right = 1.0; ro.anchor_bottom = 1.0; ro.visible = false; add_child(ro)
	var rtl = RichTextLabel.new(); rtl.name = "Console"; rtl.anchor_right = 1.0; rtl.anchor_bottom = 1.0
	rtl.margin_left = 20; rtl.margin_top = 20; rtl.bbcode_enabled = true; rtl.add_color_override("default_color", C_NEON_GREEN); ro.add_child(rtl)

func _safe_connect_debug_buttons():
	var vbox = $MainUI/DebugMenu/VBoxContainer; var cb = vbox.get_node_or_null("CloseButton")
	if cb:
		if cb.is_connected("pressed", self, "_on_CloseDebugButton_pressed"):
			cb.disconnect("pressed", self, "_on_CloseDebugButton_pressed")
		if not cb.is_connected("pressed", self, "toggle_debug_menu"):
			cb.connect("pressed", self, "toggle_debug_menu")

func _connect_input_debug_button():
	var idb = $MainUI/DebugMenu/VBoxContainer.get_node_or_null("InputDebugButton")
	if idb:
		if not idb.is_connected("pressed", self, "_on_InputDebugButton_pressed"):
			idb.connect("pressed", self, "_on_InputDebugButton_pressed")

func play_boot_sequence():
	_set_shaders_visible(true)
	if Global.has_booted:
		boot_screen.hide()
		main_ui.show()
		_build_game_buttons()
		_build_controls_bar()
		if games_grid.get_child_count() > 0:
			games_grid.get_child(Global.last_focused_game_index).grab_focus()
		return
	
	var cl = CanvasLayer.new()
	cl.layer = 5
	add_child(cl)
	var bg = ColorRect.new()
	bg.color = Color(0,0,0,1)
	bg.anchor_right = 1.0
	bg.anchor_bottom = 1.0
	cl.add_child(bg)
	
	var bios = RichTextLabel.new()
	bios.bbcode_enabled = true
	bios.anchor_right = 1.0
	bios.anchor_bottom = 1.0
	bios.margin_left = 20
	bios.margin_top = 20
	bios.add_color_override("default_color", C_NEON_GREEN)
	bg.add_child(bios)
	
	bg.color = Color(1, 1, 1, 1)
	yield(get_tree().create_timer(0.08), "timeout")
	bg.color = Color(0,0,0,1)
	
	var log_pool = ["BOOT_OS_V8", "DISK_MOUNT_OK", "VIDEO_DRIVER_V3D", "INPUT_MAPPING", "NEURAL_LINK_ESTABLISHED"]
	for i in range(250):
		bios.bbcode_text += ">>> " + log_pool[randi() % log_pool.size()] + " 0x" + str(randi()).left(8) + " [READY]\n"
		var vs = bios.get_v_scroll()
		if vs:
			vs.value = vs.max_value
		if i % 10 == 0:
			yield(get_tree(), "idle_frame")
	
	yield(get_tree().create_timer(0.2), "timeout")
	bios.hide()
	
	var pb_frame = ColorRect.new()
	pb_frame.color = Color(0,1,0,0.2)
	pb_frame.rect_min_size = Vector2(900, 50)
	pb_frame.anchor_left = 0.5
	pb_frame.anchor_top = 0.5
	pb_frame.margin_left = -450
	pb_frame.margin_top = -25
	bg.add_child(pb_frame)
	var pb = ProgressBar.new()
	pb.anchor_right = 1.0
	pb.anchor_bottom = 1.0
	var bsb = StyleBoxFlat.new()
	bsb.bg_color = C_NEON_GREEN
	pb.add_stylebox_override("fg", bsb)
	pb.percent_visible = false
	pb_frame.add_child(pb)
	for i in range(101):
		pb.value = i
		if i % 5 == 0:
			yield(get_tree(), "idle_frame")
	yield(get_tree().create_timer(0.2), "timeout")
	pb_frame.queue_free()
	
	# [FIX] HIGH QUALITY RETRO LOGO (Stacked CTRL and ARCADE)
	var font = DynamicFont.new()
	# Try to load a system font or common retro-style font on Raspberry Pi
	var font_data = DynamicFontData.new()
	var font_paths = [
		"/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
		"/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
		"res://assets/fonts/retro.ttf" # Fallback if exists
	]
	for p in font_paths:
		if File.new().file_exists(p):
			font_data.font_path = p
			break
	font.font_data = font_data
	font.size = 180
	
	var logo_container = VBoxContainer.new()
	logo_container.anchor_left = 0.0
	logo_container.anchor_right = 1.0
	logo_container.anchor_top = 0.0
	logo_container.anchor_bottom = 1.0
	logo_container.alignment = BoxContainer.ALIGN_CENTER
	logo_container.add_constant_override("separation", -20)
	bg.add_child(logo_container)
	
	var lbl_ctrl = Label.new()
	lbl_ctrl.text = "CTRL"
	lbl_ctrl.align = Label.ALIGN_CENTER
	lbl_ctrl.add_font_override("font", font)
	lbl_ctrl.add_color_override("font_color", C_NEON_GREEN)
	logo_container.add_child(lbl_ctrl)
	
	var lbl_arcade = Label.new()
	lbl_arcade.text = "ARCADE"
	lbl_arcade.align = Label.ALIGN_CENTER
	lbl_arcade.add_font_override("font", font)
	lbl_arcade.add_color_override("font_color", C_NEON_GREEN)
	logo_container.add_child(lbl_arcade)
	
	var start_ms = OS.get_ticks_msec()
	while OS.get_ticks_msec() - start_ms < 2000:
		# Glitch logic: Stay clean mostly, but occasionally jump partially out of screen
		if randf() > 0.95:
			logo_container.rect_position = Vector2(rand_range(-500, 500), rand_range(-100, 100))
			logo_container.modulate = Color(1, 0, 1) # Magenta glitch
		elif randf() > 0.90:
			logo_container.rect_position = Vector2(rand_range(-50, 50), 0)
			logo_container.modulate = Color(1, 1, 1) # White glitch
		else:
			logo_container.rect_position = Vector2(0, 0)
			logo_container.modulate = C_NEON_GREEN
		
		# Flicker logic
		logo_container.visible = (randf() > 0.05)
		yield(get_tree().create_timer(0.04), "timeout")
	
	# Fade out fast
	var tw = Tween.new()
	add_child(tw)
	tw.interpolate_property(cl.get_child(0), "modulate:a", 1.0, 0.0, 0.2)
	tw.start()
	yield(tw, "tween_all_completed")
	cl.queue_free()
	tw.queue_free()
	
	Global.has_booted = true
	_build_game_buttons()
	_build_controls_bar()
	boot_screen.hide()
	main_ui.show()
	if games_grid.get_child_count() > 0:
		games_grid.get_child(0).grab_focus()

func launch_game(game_name, index):
	if is_launching:
		return
	is_launching = true
	Global.last_focused_game_index = index
	var info = game_paths[game_name]
	if info.has("scene"):
		get_tree().change_scene(info["scene"])
		is_launching = false
		return
	var abs_path = root_path.plus_file(info["path"])
	if not File.new().file_exists(abs_path):
		_show_game_not_available()
		return
	$MainUI/Header.visible = false
	$MainUI/GamesCenter.visible = false
	_set_shaders_visible(false)
	var dir = Directory.new()
	for flag in [FLAG_READY, FLAG_DONE]:
		if File.new().file_exists(flag):
			dir.remove(flag)
	var lo = $MainUI/LoadingOverlay
	lo.show()
	var pb = lo.get_node("Frame/FakeLoadingBar")
	var lbl = lo.get_node("LoadingLabel")
	var flbl = lo.get_node("FlashLabel")
	pb.value = 0
	lbl.text = "LAUNCHING..."
	_perform_actual_launch(game_name)
	var start_ms = OS.get_ticks_msec()
	var got_ready = false
	while true:
		var elapsed = OS.get_ticks_msec() - start_ms
		pb.value = min(98.0, float(elapsed) / 15000.0 * 100.0)
		flbl.visible = (int(elapsed / 200) % 2 == 0)
		if File.new().file_exists(FLAG_READY):
			got_ready = true
			dir.remove(FLAG_READY)
			break
		if elapsed >= 15000:
			break
		yield(get_tree().create_timer(0.05), "timeout")
	if not got_ready:
		lo.hide()
		_show_game_not_available()
		return
	yield(get_tree().create_timer(0.5), "timeout")
	if File.new().file_exists(FLAG_DONE):
		lo.hide()
		dir.remove(FLAG_DONE)
		_show_game_not_available()
		return
	pb.value = 100.0
	lbl.text = "READY"
	yield(get_tree().create_timer(0.4), "timeout")
	lo.hide()
	OS.execute("bash", ["-c", "xdotool search --pid $(pgrep -f 'python3.*wrapper') windowfocus 2>/dev/null || true"], false)
	while true:
		if File.new().file_exists(FLAG_DONE):
			dir.remove(FLAG_DONE)
			break
		yield(get_tree().create_timer(0.5), "timeout")
	
	$ReturnOverlay.show()
	var console = $ReturnOverlay/Console
	console.bbcode_text = ""
	for i in range(120):
		console.bbcode_text += ">>> RESTORE_NODE_" + str(randi()).left(6) + "\n"
		var vs = console.get_v_scroll()
		if vs:
			vs.value = vs.max_value
		if i % 15 == 0:
			$ReturnOverlay.rect_position = Vector2(rand_range(-30, 30), rand_range(-30, 30))
			if randf() > 0.9:
				$ReturnOverlay.color = Color(1, 1, 1, 1)
			else:
				$ReturnOverlay.color = Color(0,0,0,1)
			yield(get_tree(), "idle_frame")
	
	$ReturnOverlay.rect_position = Vector2(0,0)
	$ReturnOverlay.color = Color(0,0,0,1)
	yield(get_tree().create_timer(0.2), "timeout")
	$ReturnOverlay.hide()
	$MainUI/Header.visible = true
	$MainUI/GamesCenter.visible = true
	_set_shaders_visible(true)
	is_launching = false
	if games_grid.get_child_count() > index:
		games_grid.get_child(index).grab_focus()

func _show_game_not_available():
	var lo = $MainUI/LoadingOverlay
	lo.show()
	var bg = ColorRect.new()
	bg.color = Color(0,0,0,1)
	bg.anchor_right = 1.0
	bg.anchor_bottom = 1.0
	lo.add_child(bg)
	lo.move_child(bg, 0)
	for c in lo.get_children():
		if c != bg:
			c.hide()
	var err = Label.new()
	err.text = "THIS GAME IS NOT AVAILABLE"
	err.anchor_right = 1.0
	err.anchor_bottom = 1.0
	err.align = Label.ALIGN_CENTER
	err.valign = Label.VALIGN_CENTER
	var df = DynamicFont.new()
	df.size = 100
	err.add_font_override("font", df)
	err.add_color_override("font_color", Color(1,0,0))
	lo.add_child(err)
	var t = 0.0
	while t < 2.5:
		err.visible = (int(t * 8) % 2 == 0)
		t += 0.1
		yield(get_tree().create_timer(0.1), "timeout")
	err.queue_free()
	bg.queue_free()
	lo.hide()
	$MainUI/Header.visible = true
	$MainUI/GamesCenter.visible = true
	_set_shaders_visible(true)
	is_launching = false

func _perform_actual_launch(game_name):
	var info = game_paths[game_name]
	var abs_p = root_path.plus_file(info["path"])
	var wrap = root_path.plus_file("utilities/pause_wrapper/wrapper.py")
	var cmd = ""
	if abs_p.ends_with(".py"):
		cmd = "python3 \"" + abs_p + "\""
	elif abs_p.ends_with(".sh"):
		cmd = "bash \"" + abs_p + "\""
	else:
		cmd = "\"" + abs_p + "\""
	OS.execute("python3", [wrap, cmd], false)

func _process(delta):
	if clock_label:
		var t = OS.get_time()
		clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]
	var joy_x = Input.get_joy_axis(0, JOY_AXIS_0)
	var joy_y = Input.get_joy_axis(0, JOY_AXIS_1)
	if abs(joy_x) > 0.4 or abs(joy_y) > 0.4:
		if not _joystick_held:
			_joystick_held = true
			if joy_x > 0.4:
				_move_focus(1, 0)
			elif joy_x < -0.4:
				_move_focus(-1, 0)
			elif joy_y > 0.4:
				_move_focus(0, 1)
			elif joy_y < -0.4:
				_move_focus(0,-1)
	else:
		_joystick_held = false
	for btn in games_grid.get_children():
		var style = btn.get_stylebox("focus")
		if btn.has_focus():
			var pulse = (sin(OS.get_ticks_msec() * 0.008) + 1.0) / 2.0
			style.border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)
		else:
			style.border_color = C_ACCENT

func _move_focus(dx, dy):
	var f = get_focus_owner()
	if not f:
		return
	var idx = f.get_index()
	var total = games_grid.get_child_count()
	var cols = games_grid.columns
	var nr = (idx / cols) + dy
	var nc = (idx % cols) + dx
	if nr >= 0 and nr < (total + cols - 1) / cols and nc >= 0 and nc < cols:
		var next = nr * cols + nc
		if next < total:
			games_grid.get_child(next).grab_focus()

func _on_btn_focus_entered(btn, game_name):
	_set_shaders_visible(true)
	var tw = btn.get_node_or_null("HoverTween")
	if tw and tw.is_inside_tree():
		tw.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.1,1.1), 0.1)
		tw.start()

func _on_btn_focus_exited(btn):
	var tw = btn.get_node_or_null("HoverTween")
	if tw and tw.is_inside_tree():
		tw.interpolate_property(btn, "rect_scale", Vector2(1.1,1.1), Vector2(1,1), 0.1)
		tw.start()

func _set_shaders_visible(visible):
	var b = get_node_or_null("CRT_Barrel")
	var s = get_node_or_null("CRT_Scanlines")
	if b:
		b.visible = visible
	if s:
		s.visible = visible

func _on_AboutButton_pressed():
	OS.alert("CTRL ARCADE V8.0", "About")

func toggle_debug_menu():
	debug_menu.visible = !debug_menu.visible
	_set_shaders_visible(!debug_menu.visible)

func _on_CloseDebugButton_pressed():
	toggle_debug_menu()

func _on_InputDebugButton_pressed():
	toggle_debug_menu()
	input_debug_overlay.visible = !input_debug_overlay.visible
	_set_shaders_visible(!input_debug_overlay.visible)

func _on_SystemInfoButton_pressed():
	OS.alert("OS: " + OS.get_name() + "\nRoot: " + root_path, "System Info")
