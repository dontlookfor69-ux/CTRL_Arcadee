extends Control

# ── References ──────────────────────────────────────────────────────────────
var audio_player : AudioStreamPlayer

# ── State Variables ─────────────────────────────────────────────────────────
var songs = []                 # Array of {"name", "path", "title"}
var matching_songs = []        # Filtered matching songs
var query = ""                 # Search query
var valid_chars = []           # Spelled characters currently active
var selected_char_idx = 0      # Highlighted letter on wheel
var selected_song_idx = 0      # Highlighted song in results list

enum FocusMode { FOCUS_WHEEL, FOCUS_LIST }
var current_focus_mode = FocusMode.FOCUS_WHEEL

# Playback State
var current_song_idx = -1
var is_playing = false
var elapsed_time = 0.0
var total_duration = 0.0

# Mouse motion wheel handling
var mouse_accum = Vector2()
const SCROLL_THRESHOLD = 20.0

# Joystick repeating state
var _joy_held_x = false
var _joy_held_y = false
var _joy_repeat_timer_x = 0.0
var _joy_repeat_timer_y = 0.0
const JOY_REPEAT_DELAY = 0.35
const JOY_REPEAT_INTERVAL = 0.15

# Windows 95 Opening Dialog Animation
var open_dialog_visible = false
var open_dialog_progress = 0.0
var open_dialog_target_song = null

# Custom font refs
var font_ui : Font
var font_ui_bold : Font
var font_large : Font

# ── Animation & Glitch FX ───────────────────────────────────────────────────
var glitch_timer    = 0.0
var glitch_interval = 5.0
var glitch_phase    = -1.0
var vu_bars         = []
var vu_bar_targets  = []
var scan_overlay    : ColorRect

# ── Dynamic Controls ────────────────────────────────────────────────────────
var wheel_control : Control
var search_query_label : Label
var song_list_ui : ItemList
var playback_status_label : Label
var open_dialog_box : Panel
var open_dialog_progress_bar : ProgressBar
var open_dialog_label : Label

func _ready():
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	
	audio_player = AudioStreamPlayer.new()
	add_child(audio_player)
	
	# Load standard fonts
	font_ui = _get_ui_font(16)
	font_ui_bold = _get_ui_font(16, true)
	font_large = _get_ui_font(24, true)
	
	# Hide all original search and YouTube panels
	for child in $WindowFrame/MainContent.get_children():
		child.hide()
	$WindowFrame/MenuBar.hide()
	$WindowFrame/ControlsBar.hide()
	
	# Reconnect close buttons to exit safely
	var close_btn = get_node_or_null("WindowFrame/TitleBar/WinButtons/CloseBtn")
	if close_btn:
		if close_btn.is_connected("pressed", self, "_on_BackBtn_pressed"):
			close_btn.disconnect("pressed", self, "_on_BackBtn_pressed")
		close_btn.connect("pressed", self, "_on_BackBtn_pressed")
		
	# Create custom main content inside WindowFrame
	var custom_content = HBoxContainer.new()
	custom_content.name = "CustomContent"
	custom_content.anchor_right = 1.0
	custom_content.anchor_bottom = 1.0
	custom_content.margin_left = 10
	custom_content.margin_top = 35
	custom_content.margin_right = -10
	custom_content.margin_bottom = -30
	custom_content.add_constant_override("separation", 12)
	$WindowFrame.add_child(custom_content)
	
	# Left Side: Alphabet Wheel Panel
	var left_panel = Panel.new()
	left_panel.rect_min_size = Vector2(480, 0)
	left_panel.size_flags_vertical = SIZE_EXPAND_FILL
	var sb_left = StyleBoxFlat.new()
	sb_left.bg_color = Color(0.753, 0.753, 0.753)
	sb_left.border_width_left = 2
	sb_left.border_width_top = 2
	sb_left.border_width_right = 2
	sb_left.border_width_bottom = 2
	sb_left.border_color = Color(1, 1, 1) # Bevel look
	left_panel.add_stylebox_override("panel", sb_left)
	custom_content.add_child(left_panel)
	
	# Wheel Control (handles draw and rotation)
	wheel_control = Control.new()
	wheel_control.anchor_right = 1.0
	wheel_control.anchor_bottom = 1.0
	wheel_control.connect("draw", self, "_on_wheel_draw")
	left_panel.add_child(wheel_control)
	
	# Right Side: Search results and Playback Status
	var right_vbox = VBoxContainer.new()
	right_vbox.size_flags_horizontal = SIZE_EXPAND_FILL
	right_vbox.size_flags_vertical = SIZE_EXPAND_FILL
	right_vbox.add_constant_override("separation", 10)
	custom_content.add_child(right_vbox)
	
	# Search input status line (Sunken Windows 95 look)
	var search_panel = Panel.new()
	search_panel.rect_min_size = Vector2(0, 36)
	var sb_search = StyleBoxFlat.new()
	sb_search.bg_color = Color(1, 1, 1) # White field
	sb_search.border_width_left = 2
	sb_search.border_width_top = 2
	sb_search.border_color = Color(0.376, 0.376, 0.376) # Sunken dark gray borders
	search_panel.add_stylebox_override("panel", sb_search)
	right_vbox.add_child(search_panel)
	
	search_query_label = Label.new()
	search_query_label.rect_min_size = Vector2(0, 36)
	search_query_label.valign = Label.VALIGN_CENTER
	search_query_label.margin_left = 10
	search_query_label.add_color_override("font_color", Color(0, 0, 0))
	search_query_label.add_font_override("font", font_large)
	search_query_label.text = "SEARCH: "
	search_panel.add_child(search_query_label)
	
	# Song List results (Sunken ItemList)
	song_list_ui = ItemList.new()
	song_list_ui.size_flags_horizontal = SIZE_EXPAND_FILL
	song_list_ui.size_flags_vertical = SIZE_EXPAND_FILL
	song_list_ui.add_font_override("font", font_ui_bold)
	song_list_ui.add_color_override("font_color", Color(0, 0, 0))
	var sb_list = StyleBoxFlat.new()
	sb_list.bg_color = Color(1, 1, 1)
	sb_list.border_width_left = 2
	sb_list.border_width_top = 2
	sb_list.border_color = Color(0.376, 0.376, 0.376)
	song_list_ui.add_stylebox_override("bg", sb_list)
	right_vbox.add_child(song_list_ui)
	
	# Playback Status bar (Cyber panel)
	var status_panel = Panel.new()
	status_panel.rect_min_size = Vector2(0, 160)
	var sb_status = StyleBoxFlat.new()
	sb_status.bg_color = Color(0.1, 0.1, 0.15)
	sb_status.border_width_left = 2
	sb_status.border_width_top = 2
	sb_status.border_width_right = 2
	sb_status.border_width_bottom = 2
	sb_status.border_color = Color(0, 1, 1)
	status_panel.add_stylebox_override("panel", sb_status)
	right_vbox.add_child(status_panel)
	
	playback_status_label = Label.new()
	playback_status_label.anchor_right = 1.0
	playback_status_label.margin_left = 15
	playback_status_label.margin_top = 10
	playback_status_label.margin_right = -15
	playback_status_label.margin_bottom = 40
	playback_status_label.add_color_override("font_color", Color(0, 1, 0.5))
	playback_status_label.add_font_override("font", font_ui_bold)
	playback_status_label.text = "Status: Stopped\nNo track playing."
	status_panel.add_child(playback_status_label)
	
	# ── VU Meter ─────────────────────────────────────────────────────────────
	var vu_hbox = HBoxContainer.new()
	vu_hbox.anchor_left  = 0.0
	vu_hbox.anchor_right = 1.0
	vu_hbox.margin_left   = 15
	vu_hbox.margin_top    = 52
	vu_hbox.margin_right  = -15
	vu_hbox.margin_bottom = 96
	vu_hbox.add_constant_override("separation", 2)
	status_panel.add_child(vu_hbox)
	for _vi in range(24):
		var bar_bg = Panel.new()
		bar_bg.size_flags_horizontal = SIZE_EXPAND_FILL
		bar_bg.rect_min_size = Vector2(0, 44)
		var sb_vu_bg = StyleBoxFlat.new()
		sb_vu_bg.bg_color = Color(0.02, 0.04, 0.04)
		bar_bg.add_stylebox_override("panel", sb_vu_bg)
		vu_hbox.add_child(bar_bg)
		var bar = ColorRect.new()
		bar.anchor_left   = 0.0
		bar.anchor_right  = 1.0
		bar.anchor_top    = 1.0
		bar.anchor_bottom = 1.0
		bar.margin_top    = -3
		bar.color = Color(0.0, 1.0, 0.5)
		bar_bg.add_child(bar)
		vu_bars.append(bar)
		vu_bar_targets.append(randf() * 0.3)
	
	# ── CRT scan-flicker overlay ──────────────────────────────────────────────
	scan_overlay = ColorRect.new()
	scan_overlay.anchor_right  = 1.0
	scan_overlay.anchor_bottom = 1.0
	scan_overlay.color = Color(0.0, 0.8, 1.0, 0.0)
	scan_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(scan_overlay)
	
	var ctrl_hbox = HBoxContainer.new()
	ctrl_hbox.anchor_top = 1.0
	ctrl_hbox.anchor_bottom = 1.0
	ctrl_hbox.anchor_right = 1.0
	ctrl_hbox.margin_top = -60
	ctrl_hbox.margin_bottom = -10
	ctrl_hbox.alignment = BoxContainer.ALIGN_CENTER
	ctrl_hbox.add_constant_override("separation", 20)
	status_panel.add_child(ctrl_hbox)
	
	var btn_prev = _create_cyber_button("[ ⏮ PREV (A) ]")
	btn_prev.connect("pressed", self, "_skip_song", [-1])
	ctrl_hbox.add_child(btn_prev)
	
	var btn_play = _create_cyber_button("[ ⏯ PLAY/PAUSE (B) ]")
	btn_play.connect("pressed", self, "_toggle_play_pause")
	ctrl_hbox.add_child(btn_play)
	
	var btn_stop = _create_cyber_button("[ ⏹ STOP ]")
	btn_stop.connect("pressed", self, "_stop_playback")
	ctrl_hbox.add_child(btn_stop)
	
	var btn_exit = _create_cyber_button("[ ⏏ EXIT (BACK) ]")
	btn_exit.connect("pressed", self, "_on_BackBtn_pressed")
	ctrl_hbox.add_child(btn_exit)
	
	# Windows 95 Startup Animation Dialog Box (Popup Panel)
	open_dialog_box = Panel.new()
	open_dialog_box.rect_min_size = Vector2(420, 150)
	open_dialog_box.anchor_left = 0.5
	open_dialog_box.anchor_top = 0.5
	open_dialog_box.anchor_right = 0.5
	open_dialog_box.anchor_bottom = 0.5
	open_dialog_box.margin_left = -210
	open_dialog_box.margin_top = -75
	open_dialog_box.margin_right = 210
	open_dialog_box.margin_bottom = 75
	
	var sb_dlg = StyleBoxFlat.new()
	sb_dlg.bg_color = Color(0.753, 0.753, 0.753)
	sb_dlg.border_width_left = 3
	sb_dlg.border_width_top = 3
	sb_dlg.border_width_right = 3
	sb_dlg.border_width_bottom = 3
	sb_dlg.border_color = Color(1, 1, 1) # Raised bevel look
	open_dialog_box.add_stylebox_override("panel", sb_dlg)
	open_dialog_box.hide()
	add_child(open_dialog_box)
	
	# Title bar for Dialog
	var dlg_title = Panel.new()
	dlg_title.anchor_right = 1.0
	dlg_title.margin_left = 3
	dlg_title.margin_top = 3
	dlg_title.margin_right = -3
	dlg_title.margin_bottom = 25
	var sb_dt = StyleBoxFlat.new()
	sb_dt.bg_color = Color(0.0, 0.0, 0.502) # Win95 Active Title Blue
	dlg_title.add_stylebox_override("panel", sb_dt)
	open_dialog_box.add_child(dlg_title)
	
	var dlg_title_lbl = Label.new()
	dlg_title_lbl.text = "ActiveMovie Control"
	dlg_title_lbl.add_color_override("font_color", Color(1, 1, 1))
	dlg_title_lbl.add_font_override("font", font_ui_bold)
	dlg_title_lbl.margin_left = 6
	dlg_title_lbl.margin_top = 4
	dlg_title_lbl.margin_bottom = 22
	dlg_title.add_child(dlg_title_lbl)
	
	# Dialog Body Text
	open_dialog_label = Label.new()
	open_dialog_label.margin_left = 20
	open_dialog_label.margin_top = 45
	open_dialog_label.margin_right = 400
	open_dialog_label.add_color_override("font_color", Color(0, 0, 0))
	open_dialog_label.add_font_override("font", font_ui)
	open_dialog_label.text = "Opening media..."
	open_dialog_box.add_child(open_dialog_label)
	
	# Dialog Progress Bar
	open_dialog_progress_bar = ProgressBar.new()
	open_dialog_progress_bar.margin_left = 20
	open_dialog_progress_bar.margin_top = 80
	open_dialog_progress_bar.margin_right = 400
	open_dialog_progress_bar.margin_bottom = 104
	open_dialog_progress_bar.percent_visible = true
	var sb_pb_fg = StyleBoxFlat.new()
	sb_pb_fg.bg_color = Color(0.0, 0.0, 0.5) # Solid blue progress blocks
	open_dialog_progress_bar.add_stylebox_override("fg", sb_pb_fg)
	var sb_pb_bg = StyleBoxFlat.new()
	sb_pb_bg.bg_color = Color(1, 1, 1)
	sb_pb_bg.border_width_left = 1
	sb_pb_bg.border_width_top = 1
	sb_pb_bg.border_color = Color(0.376, 0.376, 0.376)
	open_dialog_progress_bar.add_stylebox_override("bg", sb_pb_bg)
	open_dialog_box.add_child(open_dialog_progress_bar)
	
	# Scan for local songs
	_scan_local_songs()
	_update_spelling_wheel()

func _process(delta):
	# ── Win95 Dialog Opening Animation Progress ─────────────────────────────────
	if open_dialog_visible:
		open_dialog_progress += delta * 125.0 # Fills progress bar in ~0.8s
		open_dialog_progress_bar.value = min(100.0, open_dialog_progress)
		if open_dialog_progress >= 100.0:
			open_dialog_visible = false
			open_dialog_box.hide()
			_play_song_now(open_dialog_target_song)
			
	# ── Audio Player Progress Time Update ─────────────────────────────────────
	if is_playing and audio_player and audio_player.playing:
		elapsed_time = audio_player.get_playback_position()
		_update_status_ui()
	elif is_playing and audio_player and not audio_player.playing:
		# Auto-skip to next song at end of playback
		_skip_song(1)
	
	# ── Keep wheel pulse animations alive ────────────────────────────────────
	if wheel_control:
		wheel_control.update()
	
	# ── VU Meter + Glitch FX ─────────────────────────────────────────────────
	_update_fx(delta)

	# ── Joystick Navigation Polling ───────────────────────────────────────────
	var joy_x = 0.0
	var joy_y = 0.0
	
	# Check axes
	var ax0 = Input.get_joy_axis(0, JOY_AXIS_0)
	var ax1 = Input.get_joy_axis(0, JOY_AXIS_1)
	if abs(ax0) > 0.4:
		joy_x = ax0
	if abs(ax1) > 0.4:
		joy_y = ax1
		
	# Check hats (often mapped as axes 6 & 7 in wrapper/evdev)
	var ax6 = Input.get_joy_axis(0, 6)
	var ax7 = Input.get_joy_axis(0, 7)
	if abs(ax6) > 0.3:
		joy_x = ax6
	if abs(ax7) > 0.3:
		joy_y = ax7

	# Handle X-axis repeating (Spelling Wheel)
	var dir_x = 0
	if joy_x > 0.4: dir_x = 1
	elif joy_x < -0.4: dir_x = -1
	
	if dir_x != 0:
		if not _joy_held_x:
			_joy_held_x = true
			_joy_repeat_timer_x = JOY_REPEAT_DELAY
			_scroll_wheel(dir_x)
		else:
			_joy_repeat_timer_x -= delta
			if _joy_repeat_timer_x <= 0.0:
				_joy_repeat_timer_x = JOY_REPEAT_INTERVAL
				_scroll_wheel(dir_x)
	else:
		_joy_held_x = false
		_joy_repeat_timer_x = 0.0
		
	# Handle Y-axis repeating (Song List)
	var dir_y = 0
	if joy_y > 0.4: dir_y = 1
	elif joy_y < -0.4: dir_y = -1
	
	if dir_y != 0:
		if not _joy_held_y:
			_joy_held_y = true
			_joy_repeat_timer_y = JOY_REPEAT_DELAY
			_scroll_song_list(dir_y)
		else:
			_joy_repeat_timer_y -= delta
			if _joy_repeat_timer_y <= 0.0:
				_joy_repeat_timer_y = JOY_REPEAT_INTERVAL
				_scroll_song_list(dir_y)
	else:
		_joy_held_y = false
		_joy_repeat_timer_y = 0.0

# ── Load UI Font ─────────────────────────────────────────────────────────────
func _get_ui_font(size: int, bold: bool = false) -> Font:
	var font = DynamicFont.new()
	var font_data = DynamicFontData.new()
	var font_path = "res://assets/fonts/retro.ttf"
	
	# Fallback system font paths
	var font_paths = [
		font_path,
		"/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
		"/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
	]
	
	for p in font_paths:
		if File.new().file_exists(p):
			font_data.font_path = p
			break
	font.font_data = font_data
	font.size = size
	return font

# ── Audio Scanner ────────────────────────────────────────────────────────────
func _scan_local_songs():
	songs.clear()
	var dir = Directory.new()
	
	var paths_to_scan = [
		"res://assets/music",
		Global.root_path.plus_file("frontend/godot_project/assets/music"),
		Global.root_path.plus_file("games/just_shapes_and_beats/Just Shapes And Beats for arcade Linux/Media"),
		Global.root_path.plus_file("games/pacman/Pacman for Arcade/media"),
		Global.root_path.plus_file("games/tetris/Sounds")
	]
	
	var seen_files = {}
	for path in paths_to_scan:
		if dir.open(path) == OK:
			dir.list_dir_begin(true, true)
			var filename = dir.get_next()
			while filename != "":
				if not filename.begins_with(".") and (filename.ends_with(".mp3") or filename.ends_with(".wav") or filename.ends_with(".ogg") or filename.ends_with(".import")):
					var raw_name = filename.replace(".import", "")
					var clean_name = raw_name.get_file().get_basename().replace("_", " ")
					if not seen_files.has(clean_name):
						seen_files[clean_name] = true
						songs.append({
							"name": clean_name,
							"path": path.plus_file(raw_name),
							"title": clean_name
						})
				filename = dir.get_next()
			dir.list_dir_end()
			
	# Sort songs alphabetically
	songs.sort_custom(self, "_sort_by_name")

func _sort_by_name(a, b) -> bool:
	return a["name"].to_lower() < b["name"].to_lower()

# ── Predictive Search Spelling Wheel Logic ────────────────────────────────────
func _update_spelling_wheel():
	# 1. Filter matching songs based on query
	matching_songs.clear()
	var norm_q = query.to_upper()
	for s in songs:
		var norm_s = s["name"].to_upper()
		if norm_q == "" or norm_s.begins_with(norm_q):
			matching_songs.append(s)
			
	# 2. Rebuild ItemList UI
	song_list_ui.clear()
	for i in range(matching_songs.size()):
		var prefix = "  "
		if i == selected_song_idx and current_focus_mode == FocusMode.FOCUS_LIST:
			prefix = "▶ "
		elif i == current_song_idx:
			prefix = "🎵 "
		song_list_ui.add_item(prefix + matching_songs[i]["name"])
		
	if current_focus_mode == FocusMode.FOCUS_LIST:
		song_list_ui.select(selected_song_idx)
		
	# 3. Find valid characters to continue search
	var distinct_next_chars = {}
	for s in matching_songs:
		var norm_s = s["name"].to_upper()
		if norm_s.length() > norm_q.length():
			var next_c = norm_s[norm_q.length()]
			distinct_next_chars[next_c] = true
			
	# Convert keys to sorted list
	valid_chars.clear()
	for c in distinct_next_chars.keys():
		valid_chars.append(c)
	valid_chars.sort()
	
	# Always append space, backspace, and clear if search active
	if query.length() > 0:
		valid_chars.append("⌫") # Backspace symbol
		valid_chars.append("✖") # Clear symbol
		
	# Keep selected character index bounds-checked
	if valid_chars.size() > 0:
		selected_char_idx = clamp(selected_char_idx, 0, valid_chars.size() - 1)
	else:
		selected_char_idx = 0
		
	# Re-render wheel drawing
	wheel_control.update()
	search_query_label.text = "SEARCH: " + query.to_upper()

# ── Custom Draw Alphabet Wheel ────────────────────────────────────────────────
func _on_wheel_draw():
	var center = Vector2(240, 240)
	var radius_outer = 165
	var radius_inner = 115
	
	# Draw main outer background (cyber black)
	wheel_control.draw_circle(center, radius_outer, Color(0.05, 0.05, 0.08))
	
	# Draw nice radial notches like a premium metal dial
	var num_notches = 60
	for i in range(num_notches):
		var angle = i * 2.0 * PI / num_notches
		var p1 = center + Vector2(cos(angle), sin(angle)) * (radius_outer - 2)
		var p2 = center + Vector2(cos(angle), sin(angle)) * (radius_outer - 8)
		# Pulse notches based on time for micro-animation!
		var pulse = (sin(OS.get_ticks_msec() * 0.003 + angle * 3.0) + 1.0) / 2.0
		var color = Color(0.2, 0.2, 0.25).linear_interpolate(Color(0.0, 0.8, 0.8), pulse * 0.4)
		wheel_control.draw_line(p1, p2, color, 1.5)
		
	# Draw dark letter track ring
	wheel_control.draw_circle(center, radius_outer - 15, Color(0.02, 0.02, 0.04))
	wheel_control.draw_circle(center, radius_outer - 45, Color(0.05, 0.05, 0.08))
	
	# Draw inner knob circle (metallic grid look)
	wheel_control.draw_circle(center, radius_inner, Color(0.12, 0.12, 0.16))
	# Inner knob bevel highlights
	wheel_control.draw_circle(center, radius_inner - 2, Color(0.18, 0.18, 0.22))
	wheel_control.draw_circle(center, radius_inner - 4, Color(0.08, 0.08, 0.1))
	
	# Focus highlight border around wheel
	if current_focus_mode == FocusMode.FOCUS_WHEEL:
		var pulse = (sin(OS.get_ticks_msec() * 0.008) + 1.0) / 2.0
		var border_color = Color(0, 1, 1).linear_interpolate(Color(1, 0, 1), pulse)
		wheel_control.draw_arc(center, radius_outer + 8, 0, 2 * PI, 64, border_color, 3)
	else:
		wheel_control.draw_arc(center, radius_outer + 8, 0, 2 * PI, 64, Color(0.3, 0.3, 0.3), 2)
		
	var N = valid_chars.size()
	if N == 0:
		var empty_lbl = "No Matches"
		var sz = font_ui_bold.get_string_size(empty_lbl)
		wheel_control.draw_string(font_ui_bold, center - sz/2, empty_lbl, Color(0.6, 0.2, 0.2))
		return
		
	# Draw letters evenly spaced on the circular track
	for i in range(N):
		var angle = i * 2.0 * PI / N - PI / 2.0
		var char_pos = center + Vector2(cos(angle), sin(angle)) * (radius_outer - 30)
		var c_str = str(valid_chars[i])
		var sz = font_ui_bold.get_string_size(c_str)
		var text_origin = Vector2(char_pos.x - sz.x / 2.0, char_pos.y + sz.y / 3.0)
		
		# Draw active selection slot
		if i == selected_char_idx:
			var box_rect = Rect2(char_pos - Vector2(18, 18), Vector2(36, 36))
			# Glowing neon-cyan box
			wheel_control.draw_rect(box_rect, Color(0.0, 0.6, 0.6, 0.8))
			wheel_control.draw_rect(box_rect, Color(0.0, 1.0, 1.0), false, 2)
			# Highlighted letter in white
			wheel_control.draw_string(font_ui_bold, text_origin, c_str, Color(1, 1, 1))
		else:
			# Non-selected letters in tech green/cyan
			wheel_control.draw_string(font_ui_bold, text_origin, c_str, Color(0.0, 0.8, 0.8))
			
	# Draw query count / navigation instructions in the center of the wheel
	var center_text = "DIAL SEARCH"
	var inst_text = "Scroll Wheel: Turn\nButton X: Select"
	if current_focus_mode == FocusMode.FOCUS_LIST:
		center_text = "[Songs List]"
		inst_text = "Scroll Wheel: Up/Down\nButton X: Play Song"
		
	var sz_ct = font_ui_bold.get_string_size(center_text)
	var text_color = Color(0, 1, 1) if current_focus_mode == FocusMode.FOCUS_WHEEL else Color(1, 0, 1)
	wheel_control.draw_string(font_ui_bold, center + Vector2(0, -25) - sz_ct/2, center_text, text_color)
	
	var lines = inst_text.split("\n")
	var l_idx = 0
	for line in lines:
		var sz_l = font_ui.get_string_size(line)
		wheel_control.draw_string(font_ui, center + Vector2(0, 10 + l_idx * 18) - sz_l/2, line, Color(0.6, 0.6, 0.7))
		l_idx += 1

# ── Inputs and Controls Handling ──────────────────────────────────────────────
func _scroll_wheel(direction: int):
	if valid_chars.size() > 0:
		selected_char_idx = (selected_char_idx + direction + valid_chars.size()) % valid_chars.size()
		wheel_control.update()

func _scroll_song_list(direction: int):
	if matching_songs.size() > 0:
		selected_song_idx = (selected_song_idx + direction + matching_songs.size()) % matching_songs.size()
		song_list_ui.select(selected_song_idx)
		song_list_ui.ensure_current_is_visible()

func _input(event):
	# Exit back to Desktop
	if event is InputEventJoypadButton and event.pressed and event.button_index == 6: # BTN_BACK
		_on_BackBtn_pressed()
		return
	if event is InputEventKey and event.pressed and event.scancode == KEY_ESCAPE:
		_on_BackBtn_pressed()
		return
		
	# Skip forward (BTN_C or PageDown)
	if event is InputEventJoypadButton and event.pressed and event.button_index == 7: # BTN_C
		_skip_song(1)
		return
	if event is InputEventKey and event.pressed and event.scancode == KEY_PAGEDOWN:
		_skip_song(1)
		return
		
	# Skip backward / Restart (BTN_A or PageUp)
	if event is InputEventJoypadButton and event.pressed and event.button_index == 1: # BTN_A
		_skip_song(-1)
		return
	if event is InputEventKey and event.pressed and event.scancode == KEY_PAGEUP:
		_skip_song(-1)
		return
		
	# Play/Pause toggle (BTN_B or P)
	if event is InputEventJoypadButton and event.pressed and event.button_index == 2: # BTN_B
		_toggle_play_pause()
		return
	if event is InputEventKey and event.pressed and event.scancode == KEY_P:
		_toggle_play_pause()
		return
		
	# Play song immediately (BTN_Y or Y)
	if event is InputEventJoypadButton and event.pressed and event.button_index == 3: # BTN_Y
		if matching_songs.size() > 0:
			_trigger_win95_startup_animation(matching_songs[selected_song_idx])
		return
	if event is InputEventKey and event.pressed and event.scancode == KEY_Y:
		if matching_songs.size() > 0:
			_trigger_win95_startup_animation(matching_songs[selected_song_idx])
		return
		
	# Confirm Selection (BTN_X or Space/Enter)
	if event is InputEventJoypadButton and event.pressed and event.button_index == 0: # BTN_X
		_confirm_selection()
		return
	if event is InputEventKey and event.pressed and event.scancode in [KEY_SPACE, KEY_ENTER]:
		_confirm_selection()
		return
		
	# Keyboard Arrow keys for navigation
	if event is InputEventKey and event.pressed:
		match event.scancode:
			KEY_LEFT:
				_scroll_wheel(-1)
				return
			KEY_RIGHT:
				_scroll_wheel(1)
				return
			KEY_UP:
				_scroll_song_list(-1)
				return
			KEY_DOWN:
				_scroll_song_list(1)
				return
		
	# Mouse Motion Scroll Wheel Simulator
	if event is InputEventMouseMotion:
		mouse_accum += event.relative
		if abs(mouse_accum.x) >= SCROLL_THRESHOLD or abs(mouse_accum.y) >= SCROLL_THRESHOLD:
			var dir = 0
			if abs(mouse_accum.y) >= abs(mouse_accum.x):
				dir = 1 if mouse_accum.y > 0 else -1
			else:
				dir = 1 if mouse_accum.x > 0 else -1
				
			_on_scroll_dial(dir)
			mouse_accum = Vector2() # reset accumulator

func _toggle_focus():
	if current_focus_mode == FocusMode.FOCUS_WHEEL:
		current_focus_mode = FocusMode.FOCUS_LIST
	else:
		current_focus_mode = FocusMode.FOCUS_WHEEL
	_update_spelling_wheel()

func _on_scroll_dial(direction: int):
	if current_focus_mode == FocusMode.FOCUS_WHEEL:
		_scroll_wheel(direction)
	else:
		_scroll_song_list(direction)

func _confirm_selection():
	if current_focus_mode == FocusMode.FOCUS_WHEEL:
		if valid_chars.size() == 0:
			return
		var char_sel = valid_chars[selected_char_idx]
		if char_sel == "⌫":
			if query.length() > 0:
				query = query.substr(0, query.length() - 1)
		elif char_sel == "✖":
			query = ""
		else:
			query += char_sel
			
		selected_song_idx = 0
		_update_spelling_wheel()
	elif current_focus_mode == FocusMode.FOCUS_LIST:
		if matching_songs.size() > 0:
			var song_to_play = matching_songs[selected_song_idx]
			_trigger_win95_startup_animation(song_to_play)

# ── Audio Playback Actions ────────────────────────────────────────────────────
func _trigger_win95_startup_animation(song):
	open_dialog_target_song = song
	open_dialog_progress = 0.0
	open_dialog_progress_bar.value = 0.0
	open_dialog_label.text = "Opening: " + song["name"] + "..."
	open_dialog_box.show()
	open_dialog_visible = true

func _play_song_now(song):
	# Stop existing player
	audio_player.stop()
	
	# Find song index in full list
	current_song_idx = songs.find(song)
	
	var stream = null
	var path = song["path"]
	
	if path.begins_with("res://") and ResourceLoader.exists(path):
		stream = load(path)
	else:
		if path.ends_with(".wav"):
			stream = _load_external_wav(path)
		elif path.ends_with(".mp3"):
			stream = _load_external_mp3(path)
		elif path.ends_with(".ogg"):
			var f = File.new()
			if f.open(path, File.READ) == OK:
				stream = AudioStreamOGGVorbis.new()
				stream.data = f.get_buffer(f.get_len())
				f.close()
	
	if stream:
		audio_player.stream = stream
		audio_player.stream_paused = false
		audio_player.play()
		is_playing = true
		elapsed_time = 0.0
		total_duration = stream.get_length() if stream.has_method("get_length") else 120.0
	else:
		is_playing = false
		current_song_idx = -1
		
	_update_status_ui()

func _toggle_play_pause():
	if not is_playing: return
	if not audio_player.stream_paused:
		audio_player.stream_paused = true
		playback_status_label.text = "Status: Paused\nTrack: " + songs[current_song_idx]["name"]
	else:
		audio_player.stream_paused = false
		_update_status_ui()

func _stop_playback():
	is_playing = false
	audio_player.stop()
	current_song_idx = -1
	_update_status_ui()

func _skip_song(dir: int):
	if songs.size() == 0: return
	
	# If skip backwards (dir = -1) and elapsed > 3s, just restart current song
	if dir == -1 and elapsed_time > 3.0:
		audio_player.seek(0.0)
		elapsed_time = 0.0
		return
		
	var next_idx = 0
	if current_song_idx != -1:
		next_idx = (current_song_idx + dir + songs.size()) % songs.size()
	
	var next_song = songs[next_idx]
	_trigger_win95_startup_animation(next_song)

func _update_status_ui():
	if current_song_idx == -1:
		playback_status_label.text = "Status: Stopped\nNo track playing."
		return
		
	var song_name = songs[current_song_idx]["name"]
	var play_state = "Playing"
	if audio_player.stream_paused:
		play_state = "Paused"
		
	playback_status_label.text = "Status: " + play_state + "\nTrack: " + song_name + "\nTime: " + _format_time(elapsed_time) + " / " + _format_time(total_duration)

func _format_time(sec: float) -> String:
	var m = int(sec) / 60
	var s = int(sec) % 60
	return "%d:%02d" % [m, s]

# ── Dynamic External Audio Loaders ───────────────────────────────────────────
func _load_external_wav(path: String) -> AudioStreamSample:
	var file = File.new()
	if file.open(path, File.READ) != OK:
		return null
	var bytes = file.get_buffer(file.get_len())
	file.close()
	
	var stream = AudioStreamSample.new()
	stream.format = AudioStreamSample.FORMAT_16_BITS
	stream.mix_rate = 44100
	
	# Parse WAV header
	if bytes.size() > 44:
		var rate = bytes[24] + (bytes[25] << 8) + (bytes[26] << 16) + (bytes[27] << 24)
		stream.mix_rate = rate
		
		var bps = bytes[34] + (bytes[35] << 8)
		if bps == 8:
			stream.format = AudioStreamSample.FORMAT_8_BITS
		else:
			stream.format = AudioStreamSample.FORMAT_16_BITS
			
		var channels = bytes[22] + (bytes[23] << 8)
		stream.stereo = (channels == 2)
		
		stream.data = bytes.subarray(44, bytes.size() - 1)
	else:
		stream.data = bytes
		
	return stream

func _load_external_mp3(path: String) -> AudioStreamMP3:
	var file = File.new()
	if file.open(path, File.READ) != OK:
		return null
	var bytes = file.get_buffer(file.get_len())
	file.close()
	
	var stream = AudioStreamMP3.new()
	stream.data = bytes
	return stream

# ── Quit / Return ─────────────────────────────────────────────────────────────
func _on_BackBtn_pressed():
	audio_player.stop()
	get_tree().change_scene("res://scenes/main_desktop.tscn")

func _exit_tree():
	audio_player.stop()

# ── FX: VU Meter + Glitch Burst ─────────────────────────────────────────────
func _update_fx(delta: float):
	# Animate VU bars
	var N = vu_bars.size()
	for i in range(N):
		if is_playing:
			if randf() < delta * 8.0:
				vu_bar_targets[i] = rand_range(0.3, 1.0)
			vu_bar_targets[i] = max(0.0, vu_bar_targets[i] - delta * 1.5)
		else:
			vu_bar_targets[i] = max(0.0, vu_bar_targets[i] - delta * 2.5)
		var bar = vu_bars[i]
		var h = max(3.0, vu_bar_targets[i] * 44.0)
		bar.margin_top = -h
		var v = vu_bar_targets[i]
		if v > 0.80:
			bar.color = Color(1.0, 0.15, 0.05)
		elif v > 0.55:
			bar.color = Color(1.0, 0.75, 0.0)
		else:
			bar.color = Color(0.0, 0.8 + v * 0.15, 0.4 + v * 0.35)
	
	# Trigger a glitch burst periodically
	glitch_timer += delta
	if glitch_timer >= glitch_interval:
		glitch_timer    = 0.0
		glitch_interval = rand_range(3.5, 10.0)
		glitch_phase    = 0.0
	
	# Active glitch animation (lasts ~0.35 s)
	if glitch_phase >= 0.0:
		glitch_phase += delta
		var intensity = sin(glitch_phase * PI / 0.35)
		if scan_overlay:
			scan_overlay.color = Color(0.0, 0.9, 1.0, intensity * 0.14)
		if search_query_label and randf() > 0.65:
			search_query_label.margin_left = 10.0 + rand_range(-6.0, 6.0)
		if glitch_phase >= 0.35:
			glitch_phase = -1.0
			if search_query_label:
				search_query_label.margin_left = 10.0
			if scan_overlay:
				scan_overlay.color = Color(0.0, 0.9, 1.0, 0.0)

func _create_cyber_button(text: String) -> Button:
	var btn = Button.new()
	btn.text = text
	btn.add_font_override("font", font_ui_bold)
	btn.add_color_override("font_color", Color(0, 1, 1))
	btn.add_color_override("font_color_hover", Color(1, 0, 1))
	btn.add_color_override("font_color_pressed", Color(1, 1, 1))
	
	var sb_normal = StyleBoxFlat.new()
	sb_normal.bg_color = Color(0.05, 0.05, 0.1)
	sb_normal.set_border_width_all(2)
	sb_normal.border_color = Color(0, 0.5, 0.5)
	btn.add_stylebox_override("normal", sb_normal)
	
	var sb_hover = sb_normal.duplicate()
	sb_hover.border_color = Color(1, 0, 1)
	btn.add_stylebox_override("hover", sb_hover)
	btn.add_stylebox_override("focus", sb_hover)
	
	var sb_pressed = sb_normal.duplicate()
	sb_pressed.bg_color = Color(0.2, 0, 0.2)
	sb_pressed.border_color = Color(1, 1, 1)
	btn.add_stylebox_override("pressed", sb_pressed)
	
	btn.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	return btn
