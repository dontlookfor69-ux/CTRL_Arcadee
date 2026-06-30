extends Control

# ── Global State ────────────────────────────────────────────────────
var is_launching = false
var is_input_debugger_active = false
var root_path = ""
var game_info = {}

# ── Arcade controller constants ──────────────────────────────────────────
const BTN_X     = 0
const BTN_A     = 1
const BTN_B     = 2
const BTN_Y     = 3
const BTN_Z     = 5
const BTN_BACK  = 6
const BTN_C     = 7
const BTN_START = 9
const BTN_MENU  = 12

const HAT_UP    = 12
const HAT_DOWN  = 13
const HAT_LEFT  = 14
const HAT_RIGHT = 15

var _hat_last_dir  = Vector2(0, 0)
var _hat_held      = false
var _hat_repeat_timer = 0.0
const HAT_REPEAT_DELAY    = 0.35
const HAT_REPEAT_INTERVAL = 0.15

# Carousel state
var _carousel_index = 0
var _carousel_nodes = []
var _carousel_moving = false

onready var carousel = $MainUI/Carousel
onready var game_name_label = $MainUI/GameNameLabel
onready var debug_menu = $MainUI/DebugMenu
onready var main_ui = $MainUI
onready var boot_screen = $BootScreen
onready var clock_label = $MainUI/Header/HBox/ClockLabel
onready var input_debug_overlay = $MainUI/InputDebugOverlay
onready var attract_overlay = $MainUI/AttractMode

var C_BG = Color(0.05, 0, 0, 1)
var C_ACCENT = Color(0.0, 1.0, 1.0, 1)
var C_LIME = Color(0.2, 1.0, 0.2, 1)
var C_NEON_GREEN = Color("#39FF14")

var game_paths = {
	"Pacman": {"path": "games/pacman/launch_pacman.sh", "icon": "res://assets/icons/pacman.png"},
	"Tetris": {"path": "games/tetris/main.py", "icon": "res://assets/icons/tetris.png"},
	"Undertale": {"path": "games/undertale/launch_undertale.sh", "icon": "res://assets/icons/undertale.png"},
	"Just Shapes & Beats": {"path": "games/just_shapes_and_beats/Just Shapes And Beats for arcade Linux/game.py", "icon": "res://assets/icons/Just_Shapes_And_Beats.png"},
	"Flappy Bird": {"path": "games/flappybird/flappybird/main.py", "icon": "res://assets/icons/flappybird.png"},
	"Etch A Sketch AI": {"path": "utilities/etch_a_sketch_ai/main.py", "icon": "res://assets/icons/etch_a_sketch.png"},
	"Media Player": {"scene": "res://scenes/media_player.tscn", "icon": "res://assets/icons/Media_Player.png"},
	"Tennis for 2": {"path": "games/tennis_for_2/main.py", "icon": "res://assets/icons/tennis_icon.png"}
}

const FLAG_READY = "/tmp/arcade_ready"
const FLAG_DONE = "/tmp/arcade_done"

var idle_timer = 0.0
var screensaver_active = false
var screensaver_move_timer = 0.0
var screensaver_fade = 1.0
var scroll_offset = 0.0

var sfx_move = AudioStreamPlayer.new()
var sfx_launch = AudioStreamPlayer.new()
var bgm_player = AudioStreamPlayer.new()
var global_scores = {}

# ── Visual FX ──────────────────────────────────────────────────────────────────
var fx_glitch_timer    = 0.0
var fx_glitch_interval = 10.0
var fx_glitch_phase    = -1.0

func _ready():
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	root_path = Global.root_path
	_load_game_info()
	main_ui.hide()
	boot_screen.show()
	boot_screen.modulate.a = 1.0
	
	var title_font = _get_ui_font(38)
	var hint_font = _get_ui_font(20)
	if game_name_label:
		game_name_label.add_font_override("font", title_font)
	var launch_hint = $MainUI/LaunchHint
	if launch_hint:
		launch_hint.add_font_override("font", hint_font)
		
	_build_return_overlay()
	_build_loading_bar()
	_safe_connect_debug_buttons()
	_connect_input_debug_button()
	attract_overlay.hide()
	
	add_child(sfx_move)
	add_child(sfx_launch)
	add_child(bgm_player)
	_load_sfx_from_wav(sfx_move, "/frontend/godot_project/assets/sfx/move.wav")
	_load_sfx_from_wav(sfx_launch, "/frontend/godot_project/assets/sfx/launch.wav")
	
	# Try to load BGM
	if File.new().file_exists(root_path + "/frontend/godot_project/assets/bgm/menu.ogg"):
		var stream = AudioStreamOGGVorbis.new()
		var f = File.new()
		if f.open(root_path + "/frontend/godot_project/assets/bgm/menu.ogg", File.READ) == OK:
			stream.data = f.get_buffer(f.get_len())
			stream.loop = true
			bgm_player.stream = stream
			bgm_player.volume_db = -10.0
			bgm_player.play()
			f.close()
	elif File.new().file_exists(root_path + "/frontend/godot_project/assets/bgm/menu.wav"):
		_load_sfx_from_wav(bgm_player, "/frontend/godot_project/assets/bgm/menu.wav")
		if bgm_player.stream:
			bgm_player.stream.loop_mode = AudioStreamSample.LOOP_FORWARD
			bgm_player.volume_db = -10.0
			bgm_player.play()
	
	call_deferred("play_boot_sequence")

func _load_sfx_from_wav(player, rel_path):
	var f = File.new()
	if f.open(root_path + rel_path, File.READ) == OK:
		var buf = f.get_buffer(f.get_len())
		f.close()
		var stream = AudioStreamSample.new()
		stream.format = AudioStreamSample.FORMAT_16_BITS
		stream.mix_rate = 44100
		stream.data = buf.subarray(44, buf.size() - 1)
		player.stream = stream

func _get_ui_font(size):
	var font = DynamicFont.new()
	var font_data = DynamicFontData.new()
	var font_paths = [
		"/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
		"/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
		"res://assets/fonts/retro.ttf"
	]
	for p in font_paths:
		if File.new().file_exists(p):
			font_data.font_path = p
			break
	font.font_data = font_data
	font.size = size
	return font

func _load_game_info():
	var f = File.new()
	if f.open("res://assets/game_info.json", File.READ) == OK:
		var res = JSON.parse(f.get_as_text())
		if res.error == OK:
			game_info = res.result
		f.close()
		
	if f.open(root_path + "/games/highscores.json", File.READ) == OK:
		var res = JSON.parse(f.get_as_text())
		if res.error == OK:
			global_scores = res.result
		f.close()

func _detect_root_path():
	pass # Handled by global.gd

func _build_carousel():
	for child in carousel.get_children():
		child.queue_free()
	_carousel_nodes.clear()
	
	var i = 0
	for game_name in game_paths.keys():
		var info = game_paths[game_name]
		var node = Control.new()
		node.name = "Slot_" + str(i)
		node.rect_min_size = Vector2(266, 266)
		node.rect_size = Vector2(266, 266)
		node.rect_pivot_offset = Vector2(133, 133)
		
		var is_installed = true
		if info.has("path"):
			var abs_p = root_path.plus_file(info["path"])
			if not File.new().file_exists(abs_p):
				is_installed = false
				
		var panel = Panel.new()
		panel.anchor_right = 1.0
		panel.anchor_bottom = 1.0
		var sb = StyleBoxFlat.new()
		sb.bg_color = Color(0,0,0,0.95) if is_installed else Color(0.1, 0, 0, 0.95)
		sb.border_color = C_ACCENT
		sb.set_border_width_all(4)
		panel.add_stylebox_override("panel", sb)
		node.add_child(panel)
		
		var ir = TextureRect.new()
		ir.name = "Icon"
		ir.expand = true
		ir.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ir.anchor_left = 0.5
		ir.anchor_top = 0.5
		ir.anchor_right = 0.5
		ir.anchor_bottom = 0.5
		ir.margin_left = -80
		ir.margin_right = 80
		ir.margin_top = -80
		ir.margin_bottom = 80
		if not is_installed:
			ir.modulate = Color(0.3, 0.3, 0.3)
		node.add_child(ir)
		_deferred_load_icon(ir, info["icon"])
		
		var tw = Tween.new()
		tw.name = "Tween"
		node.add_child(tw)
		
		carousel.add_child(node)
		_carousel_nodes.append({"node": node, "name": game_name})
		i += 1
		
	_carousel_index = Global.last_focused_game_index
	scroll_offset = float(_carousel_index)
	_update_carousel(true)

func _sort_by_dist(a, b):
	return a["dist"] > b["dist"]

func _update_carousel(immediate = false):
	if immediate:
		scroll_offset = float(_carousel_index)
	var total = _carousel_nodes.size()
	if total == 0: return
	
	var game_name = _carousel_nodes[_carousel_index]["name"]
	var score = global_scores.get(game_name, 0)
	if score > 0:
		game_name_label.text = game_name.to_upper() + " (BEST: " + str(score) + ")"
	else:
		game_name_label.text = game_name.to_upper()

func _update_carousel_layout():
	var total = _carousel_nodes.size()
	if total == 0: return
	
	var center_x = 1280 / 2.0
	var center_y = 360.0 - 66.0
	
	# Current active name/score is updated based on the closest item
	var closest_idx = int(round(scroll_offset)) % total
	if closest_idx < 0: closest_idx += total
	
	var game_name = _carousel_nodes[closest_idx]["name"]
	var score = global_scores.get(game_name, 0)
	if score > 0:
		game_name_label.text = game_name.to_upper() + " (BEST: " + str(score) + ")"
	else:
		game_name_label.text = game_name.to_upper()
		
	var draw_order = []
	for i in range(total):
		var dist = i - scroll_offset
		if dist > total / 2.0: dist -= total
		if dist < -total / 2.0: dist += total
		draw_order.append({"index": i, "dist": abs(dist), "signed_dist": dist})
		
	draw_order.sort_custom(self, "_sort_by_dist")
	
	var z_idx = 0
	for d_item in draw_order:
		var i = d_item["index"]
		var dist = d_item["signed_dist"]
		var node = _carousel_nodes[i]["node"]
		
		# Move node to correct Z-order only if it changed, to save CPU layout updates
		if node.get_index() != z_idx:
			carousel.move_child(node, z_idx)
		z_idx += 1
		
		var target_x = center_x - 133
		var target_y = center_y - 133
		var target_scale = Vector2(1,1)
		var target_alpha = 1.0
		var target_color = C_ACCENT
		
		var abs_dist = abs(dist)
		if abs_dist <= 1.0:
			var t = abs_dist
			target_scale = Vector2(1.2, 1.2).linear_interpolate(Vector2(0.8, 0.8), t)
			target_alpha = lerp(1.0, 0.6, t)
			target_color = Color(1.0, 1.0, 1.0, 1.0).linear_interpolate(C_ACCENT, t)
			target_x = center_x - 133 + (300.0 * dist)
		elif abs_dist <= 2.0:
			var t = abs_dist - 1.0
			target_scale = Vector2(0.8, 0.8).linear_interpolate(Vector2(0.6, 0.6), t)
			target_alpha = lerp(0.6, 0.3, t)
			target_color = C_ACCENT
			target_x = center_x - 133 + (lerp(300.0, 466.0, t) * sign(dist))
		else:
			var t = min(1.0, abs_dist - 2.0)
			target_scale = Vector2(0.6, 0.6).linear_interpolate(Vector2(0.4, 0.4), t)
			target_alpha = lerp(0.3, 0.0, t)
			target_color = C_ACCENT
			target_x = center_x - 133 + (lerp(466.0, 600.0, t) * sign(dist))
			
		var panel = node.get_child(0)
		var sb = panel.get_stylebox("panel").duplicate()
		sb.border_color = target_color
		panel.add_stylebox_override("panel", sb)
		
		node.rect_position = Vector2(target_x, target_y)
		node.rect_scale = target_scale
		node.rect_rotation = 0.0
		node.modulate.a = target_alpha

func _deferred_load_icon(ir, icon_path):
	yield(get_tree(), "idle_frame")
	var tex = _load_texture_safe(icon_path)
	if tex:
		ir.texture = tex

func _build_controls_bar():
	pass # Controls bar is removed, using LaunchHint now

func _load_texture_safe(path: String) -> Texture:
	if ResourceLoader.exists(path):
		var tex = ResourceLoader.load(path)
		if tex is Texture:
			return tex
	var abs_p = root_path.plus_file(path) if not path.begins_with("res://") else ProjectSettings.globalize_path(path)
	var img = Image.new()
	if img.load(abs_p) == OK:
		var tex = ImageTexture.new()
		tex.create_from_image(img)
		return tex
	return null

func _build_loading_bar():
	var lo = $MainUI/LoadingOverlay
	if not lo: return
	for child in lo.get_children():
		child.queue_free()
	var flbl = Label.new()
	flbl.name = "FlashLabel"
	flbl.text = "LOADING..."
	flbl.anchor_left = 0.5
	flbl.anchor_top = 0.45
	flbl.anchor_right = 0.5
	flbl.anchor_bottom = 0.45
	flbl.margin_left = -200
	flbl.margin_right = 200
	flbl.align = Label.ALIGN_CENTER
	var df = DynamicFont.new()
	df.size = 32
	flbl.add_font_override("font", df)
	lo.add_child(flbl)
	var frame = ColorRect.new()
	frame.name = "Frame"
	frame.color = Color(0, 1, 1, 0.2)
	frame.anchor_left = 0.5
	frame.anchor_top = 0.6
	frame.anchor_right = 0.5
	frame.anchor_bottom = 0.6
	frame.margin_left = -300
	frame.margin_right = 300
	frame.margin_top = -15
	frame.margin_bottom = 15
	lo.add_child(frame)
	var pb = ProgressBar.new()
	pb.name = "FakeLoadingBar"
	pb.anchor_right = 1.0
	pb.anchor_bottom = 1.0
	var sb = StyleBoxFlat.new()
	sb.bg_color = C_ACCENT
	pb.add_stylebox_override("fg", sb)
	var bgs = StyleBoxFlat.new()
	bgs.bg_color = Color(0,0,0,1)
	pb.add_stylebox_override("bg", bgs)
	pb.percent_visible = false
	frame.add_child(pb)
	var lbl = Label.new()
	lbl.name = "LoadingLabel"
	lbl.anchor_left = 0.0
	lbl.anchor_right = 1.0
	lbl.anchor_top = 0.6
	lbl.margin_top = 30
	lbl.align = Label.ALIGN_CENTER
	lbl.add_color_override("font_color", C_NEON_GREEN)
	lo.add_child(lbl)

func _build_return_overlay():
	var old = get_node_or_null("ReturnOverlay")
	if old:
		old.queue_free()
	var ro = ColorRect.new()
	ro.name = "ReturnOverlay"
	ro.color = Color(0, 0, 0, 1)
	ro.anchor_right = 1.0
	ro.anchor_bottom = 1.0
	ro.visible = false
	add_child(ro)
	var rtl = RichTextLabel.new()
	rtl.name = "Console"
	rtl.anchor_right = 1.0
	rtl.anchor_bottom = 1.0
	rtl.margin_left = 20
	rtl.margin_top = 20
	rtl.bbcode_enabled = true
	rtl.add_color_override("default_color", C_NEON_GREEN)
	ro.add_child(rtl)

func _safe_connect_debug_buttons():
	var vbox = $MainUI/DebugMenu/VBoxContainer
	var cb = vbox.get_node_or_null("CloseButton")
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
	Global.has_booted = true
	_build_carousel()
	boot_screen.hide()
	main_ui.show()

func launch_game():
	if is_launching or _carousel_nodes.size() == 0:
		return
	var game_name = _carousel_nodes[_carousel_index]["name"]
	is_launching = true
	Global.last_focused_game_index = _carousel_index
	var info = game_paths[game_name]
	
	if info.has("scene"):
		$MainUI/Header.visible = false
		game_name_label.visible = false
		$MainUI/LaunchHint.visible = false
		
		var center_node = _carousel_nodes[_carousel_index]["node"]
		var anim_tw = Tween.new()
		add_child(anim_tw)
		
		for item in _carousel_nodes:
			if item["node"] != center_node:
				anim_tw.interpolate_property(item["node"], "modulate:a", item["node"].modulate.a, 0.0, 0.4, Tween.TRANS_CUBIC, Tween.EASE_OUT)
				
		sfx_launch.play()
		anim_tw.interpolate_property(center_node, "rect_scale", center_node.rect_scale, Vector2(0.85, 0.85), 0.3, Tween.TRANS_SINE, Tween.EASE_IN_OUT)
		anim_tw.interpolate_property(center_node, "rect_rotation", 0.0, -10.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.0)
		anim_tw.interpolate_property(center_node, "rect_rotation", -10.0, 10.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.1)
		anim_tw.interpolate_property(center_node, "rect_rotation", 10.0, 0.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.2)
		
		anim_tw.interpolate_property(center_node, "rect_scale", Vector2(0.85, 0.85), Vector2(30.0, 30.0), 0.4, Tween.TRANS_EXPO, Tween.EASE_IN, 0.3)
		anim_tw.interpolate_property(center_node, "modulate:a", 1.0, 0.0, 0.3, Tween.TRANS_EXPO, Tween.EASE_IN, 0.4)
		anim_tw.start()
		yield(anim_tw, "tween_all_completed")
		anim_tw.queue_free()
		
		get_tree().change_scene(info["scene"])
		is_launching = false
		return
		
	var abs_path = root_path.plus_file(info["path"])
	if not File.new().file_exists(abs_path):
		yield(_show_game_not_available(), "completed")
		return
		
	$MainUI/Header.visible = false
	game_name_label.visible = false
	$MainUI/LaunchHint.visible = false
	
	var center_node = _carousel_nodes[_carousel_index]["node"]
	var anim_tw = Tween.new()
	add_child(anim_tw)
	
	for item in _carousel_nodes:
		if item["node"] != center_node:
			anim_tw.interpolate_property(item["node"], "modulate:a", item["node"].modulate.a, 0.0, 0.4, Tween.TRANS_CUBIC, Tween.EASE_OUT)
			
	sfx_launch.play()
	# Anticipation shrink and shake
	anim_tw.interpolate_property(center_node, "rect_scale", center_node.rect_scale, Vector2(0.85, 0.85), 0.3, Tween.TRANS_SINE, Tween.EASE_IN_OUT)
	anim_tw.interpolate_property(center_node, "rect_rotation", 0.0, -10.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.0)
	anim_tw.interpolate_property(center_node, "rect_rotation", -10.0, 10.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.1)
	anim_tw.interpolate_property(center_node, "rect_rotation", 10.0, 0.0, 0.1, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT, 0.2)
	
	# Explosive zoom and fade
	anim_tw.interpolate_property(center_node, "rect_scale", Vector2(0.85, 0.85), Vector2(30.0, 30.0), 0.4, Tween.TRANS_EXPO, Tween.EASE_IN, 0.3)
	anim_tw.interpolate_property(center_node, "modulate:a", 1.0, 0.0, 0.3, Tween.TRANS_EXPO, Tween.EASE_IN, 0.4)
	anim_tw.start()
	yield(anim_tw, "tween_all_completed")
	
	carousel.visible = false
	anim_tw.queue_free()
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
	
	# Purge Godot memory and suspend while game runs
	_free_memory_for_game()
	
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
		if File.new().file_exists(FLAG_DONE):
			break
		if elapsed >= 15000:
			break
		yield(get_tree().create_timer(0.05), "timeout")
		
	if not got_ready:
		lo.hide()
		yield(_show_game_not_available(), "completed")
		return
		
	yield(get_tree().create_timer(0.5), "timeout")
	if File.new().file_exists(FLAG_DONE):
		lo.hide()
		dir.remove(FLAG_DONE)
		yield(_show_game_not_available(), "completed")
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
	
	_restore_memory_after_game()
	
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
	_restore_menu_after_exit()

func _restore_menu_after_exit():
	_update_carousel(true)
	$MainUI/Header.visible = true
	carousel.visible = true
	game_name_label.visible = true
	$MainUI/LaunchHint.visible = true
	_set_shaders_visible(true)
	is_launching = false

func _free_memory_for_game():
	for child in carousel.get_children():
		child.queue_free()
	_carousel_nodes.clear()
	if bgm_player.playing:
		bgm_player.stop()
	OS.window_minimized = true
	Engine.target_fps = 5

func _restore_memory_after_game():
	Engine.target_fps = 60
	OS.window_minimized = false
	OS.window_fullscreen = true
	_build_carousel()
	if bgm_player.stream:
		bgm_player.play()

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
	_restore_menu_after_exit()

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
	idle_timer += delta
	var total = _carousel_nodes.size()
	if total > 0:
		if idle_timer >= 60.0 and not is_launching and not debug_menu.visible and not input_debug_overlay.visible:
			if not screensaver_active:
				screensaver_active = true
			# Continuously scroll slowly
			scroll_offset += delta * 0.15
			# Wrap-around
			scroll_offset = fmod(scroll_offset, total)
			if scroll_offset < 0.0:
				scroll_offset += total
		else:
			if screensaver_active:
				screensaver_active = false
				# Snap to closest item
				_carousel_index = int(round(scroll_offset)) % total
				if _carousel_index < 0: _carousel_index += total
				
			# Smoothly glide to the target index
			var target = float(_carousel_index)
			var diff = target - scroll_offset
			if diff > total / 2.0:
				scroll_offset += total
			elif diff < -total / 2.0:
				scroll_offset -= total
				
			scroll_offset = lerp(scroll_offset, target, 8.0 * delta)
			
			scroll_offset = fmod(scroll_offset, total)
			if scroll_offset < 0.0:
				scroll_offset += total
				
		if not is_launching:
			_update_carousel_layout()
		
	# Fade out text when screensaver active, fade back in when user moves it
	if screensaver_active:
		screensaver_fade = max(0.0, screensaver_fade - delta * 2.0)
	else:
		screensaver_fade = min(1.0, screensaver_fade + delta * 3.0)
		
	if game_name_label:
		game_name_label.modulate.a = screensaver_fade
	var launch_hint = $MainUI/LaunchHint
	if launch_hint:
		launch_hint.modulate.a = screensaver_fade
	var header = $MainUI/Header
	if header:
		header.modulate.a = screensaver_fade

	if clock_label:
		var t = OS.get_time()
		clock_label.text = "%02d:%02d:%02d" % [t.hour, t.minute, t.second]

	# ── Game name glitch burst ─────────────────────────────────────────────
	if not is_launching and not screensaver_active:
		fx_glitch_timer += delta
		if fx_glitch_timer >= fx_glitch_interval:
			fx_glitch_timer    = 0.0
			fx_glitch_interval = rand_range(8.0, 20.0)
			fx_glitch_phase    = 0.0
		if fx_glitch_phase >= 0.0 and game_name_label:
			fx_glitch_phase += delta
			if fx_glitch_phase < 0.20:
				var pulse = abs(sin(fx_glitch_phase * PI * 22.0))
				game_name_label.add_color_override("font_color",
					Color(1.0, 0.1 + pulse * 0.2, 0.7 - pulse * 0.5))
			else:
				game_name_label.add_color_override("font_color", Color(1, 1, 1))
				fx_glitch_phase = -1.0

	var hat_x = 0.0
	var hat_y = 0.0
	var ax6 = Input.get_joy_axis(0, 6)
	var ax7 = Input.get_joy_axis(0, 7)
	if abs(ax6) > 0.3 or abs(ax7) > 0.3:
		hat_x = ax6
		hat_y = ax7
	else:
		var ax0 = Input.get_joy_axis(0, JOY_AXIS_0)
		var ax1 = Input.get_joy_axis(0, JOY_AXIS_1)
		if abs(ax0) > 0.4 or abs(ax1) > 0.4:
			hat_x = ax0
			hat_y = ax1

	var dir_x = 0
	if   hat_x >  0.35: dir_x = 1
	elif hat_x < -0.35: dir_x = -1

	if dir_x != 0:
		if not _hat_held:
			_hat_held = true
			_hat_repeat_timer = HAT_REPEAT_DELAY
			_move_carousel(dir_x)
		else:
			_hat_repeat_timer -= delta
			if _hat_repeat_timer <= 0.0:
				_hat_repeat_timer = HAT_REPEAT_INTERVAL
				_move_carousel(dir_x)
	else:
		_hat_held = false
		_hat_repeat_timer = 0.0
		
	# Pulsing border on center item
	if _carousel_nodes.size() > 0:
		var center_idx = int(round(scroll_offset)) % total
		if center_idx < 0: center_idx += total
		var center_node = _carousel_nodes[center_idx]["node"]
		var panel = center_node.get_child(0)
		var sb = panel.get_stylebox("panel")
		var pulse = (sin(OS.get_ticks_msec() * 0.008) + 1.0) / 2.0
		sb.border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)

func _input(event):
	if event is InputEventKey or event is InputEventJoypadButton or event is InputEventJoypadMotion:
		if event is InputEventJoypadMotion and abs(event.axis_value) < 0.2:
			pass # ignore small deadzone motions
		else:
			idle_timer = 0.0

	if is_launching: return

	if event is InputEventJoypadButton and event.pressed:
		var btn = event.button_index
		if   btn == HAT_LEFT:  _move_carousel(-1)
		elif btn == HAT_RIGHT: _move_carousel(1)
		elif btn == BTN_X:
			launch_game()
		elif btn == BTN_BACK:
			if debug_menu.visible:
				toggle_debug_menu()

	if event is InputEventKey and event.pressed and not event.echo:
		match event.scancode:
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				launch_game()
			KEY_LEFT:
				_move_carousel(-1)
			KEY_RIGHT:
				_move_carousel(1)

func _move_carousel(dir, silent = false):
	if _carousel_nodes.size() == 0: return
	_carousel_index = (_carousel_index + dir) % _carousel_nodes.size()
	if _carousel_index < 0:
		_carousel_index += _carousel_nodes.size()
	if not silent:
		sfx_move.play()
	_update_carousel(false)

func _set_shaders_visible(visible):
	var b = get_node_or_null("CRT_Barrel")
	var s = get_node_or_null("CRT_Scanlines")
	if b: b.visible = visible
	if s: s.visible = visible

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
