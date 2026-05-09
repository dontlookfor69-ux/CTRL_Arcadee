extends Control

var p1_held = false
var p2_press_count = 0

onready var games_grid = $MainUI/Panel/GamesScroll/GamesGrid
onready var debug_menu = $MainUI/DebugMenu
onready var main_ui = $MainUI
onready var boot_screen = $BootScreen

var game_paths = {
	"Pacman": {"path": "games/pacman/build_and_run.sh", "icon": "res://assets/icons/pacman.png"},
	"Tetris": {"path": "games/tetris/main.py", "icon": "res://assets/icons/tetris.png"},
	"DOOM": {"path": "games/doom/launch_doom.sh", "icon": "res://assets/icons/doom.png"},
	"Undertale": {"path": "games/undertale/launch_undertale.sh", "icon": "res://assets/icons/undertale.png"},
	"Just Shapes & Beats": {"path": "games/just_shapes_and_beats/launch_jsab.sh", "icon": "res://assets/icons/jsab.png"},
	"Minecraft Pi": {"path": "games/minecraft_pi/launch_mcpi.sh", "icon": "res://assets/icons/minecraft.png"},
	"Etch A Sketch AI": {"path": "utilities/etch_a_sketch_ai/main.py", "icon": "res://assets/icons/etch_a_sketch.png"},
	"Media Player": {"scene": "res://scenes/media_player.tscn", "icon": ""}
}

func _ready():
	main_ui.hide()
	boot_screen.show()
	boot_screen.modulate = Color(1, 1, 1, 1)
	
	for game_name in game_paths.keys():
		var btn = TextureButton.new()
		var tex = load_external_texture(game_paths[game_name]["icon"])
		if tex:
			btn.texture_normal = tex
		else:
			# Create a simple default icon programmatically
			var img = Image.new()
			img.create(200, 200, false, Image.FORMAT_RGBA8)
			img.fill(Color(0.2, 0.4, 0.8, 1.0))
			var def_tex = ImageTexture.new()
			def_tex.create_from_image(img)
			btn.texture_normal = def_tex
		
		# Add a label below the icon
		var vbox = VBoxContainer.new()
		var label = Label.new()
		label.text = game_name
		label.align = Label.ALIGN_CENTER
		vbox.add_child(btn)
		vbox.add_child(label)
		
		games_grid.add_child(vbox)
		btn.rect_pivot_offset = Vector2(100, 100)
		btn.focus_mode = Control.FOCUS_ALL
		btn.connect("pressed", self, "launch_game", [game_name])
		btn.connect("focus_entered", self, "_on_btn_focus_entered", [btn])
		btn.connect("focus_exited", self, "_on_btn_focus_exited", [btn])
		btn.connect("mouse_entered", btn, "grab_focus")
	play_boot_sequence()

func play_boot_sequence():
	if Global.has_booted:
		boot_screen.hide()
		main_ui.show()
		if games_grid.get_child_count() > 0:
			games_grid.get_child(0).get_child(0).grab_focus()
		return
		
	var logo = $BootScreen/BootLogo
	var tween = $BootScreen/BootTween
	
	var icon = load_external_texture("res://assets/images/icon.png")
	if not icon: icon = load_external_texture("res://assets/icons/pacman.png")
	logo.texture = icon
	
	logo.rect_scale = Vector2(0, 0)
	logo.modulate = Color(1, 1, 1, 0)
	
	tween.interpolate_property(logo, "rect_scale", Vector2(0, 0), Vector2(1.5, 1.5), 1.5, Tween.TRANS_BOUNCE, Tween.EASE_OUT)
	tween.interpolate_property(logo, "modulate", Color(1, 1, 1, 0), Color(1, 1, 1, 1), 1.0, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT)
	tween.start()
	yield(tween, "tween_all_completed")
	
	yield(get_tree().create_timer(1.0), "timeout")
	
	tween.interpolate_property(boot_screen, "modulate", Color(1, 1, 1, 1), Color(1, 1, 1, 0), 0.8, Tween.TRANS_LINEAR, Tween.EASE_IN_OUT)
	tween.start()
	yield(tween, "tween_all_completed")
	
	Global.has_booted = true
	boot_screen.hide()
	main_ui.show()
	if games_grid.get_child_count() > 0:
		games_grid.get_child(0).get_child(0).grab_focus()

func _on_btn_focus_entered(btn):
	var tween = Tween.new()
	btn.add_child(tween)
	tween.interpolate_property(btn, "rect_scale", Vector2(1,1), Vector2(1.15, 1.15), 0.15, Tween.TRANS_SINE, Tween.EASE_OUT)
	tween.start()

func _on_btn_focus_exited(btn):
	var tween = Tween.new()
	btn.add_child(tween)
	tween.interpolate_property(btn, "rect_scale", btn.rect_scale, Vector2(1,1), 0.15, Tween.TRANS_SINE, Tween.EASE_OUT)
	tween.start()

func load_external_texture(path):
	var img = Image.new()
	var global_path = ProjectSettings.globalize_path(path)
	var err = img.load(global_path)
	if err == OK:
		var tex = ImageTexture.new()
		tex.create_from_image(img, 0) # 0 = no filter (pixel art style)
		return tex
	return null

# Music player logic moved to standalone Media Player scene.


func _process(delta):
	if not main_ui.visible:
		return
		
	if Input.is_action_just_pressed("debug_combo_p1"):
		p1_held = true
		p2_press_count = 0
	elif Input.is_action_just_released("debug_combo_p1"):
		p1_held = false
		p2_press_count = 0
		
	if p1_held and Input.is_action_just_pressed("debug_combo_p2"):
		p2_press_count += 1
		if p2_press_count >= 3:
			toggle_debug_menu()
			p1_held = false
			p2_press_count = 0

func launch_game(game_name):
	if not game_paths.has(game_name):
		return
		
	var game_info = game_paths[game_name]
	if game_info.has("scene"):
		# Launch internal godot scene (like media player)
		get_tree().change_scene(game_info["scene"])
		return
		
	var path = game_info["path"]
	
	# Compute absolute paths robustly
	var project_root = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir()
	var absolute_target_path = project_root.plus_file(path)
	var wrapper_script = project_root.plus_file("utilities/pause_wrapper/wrapper.py")
	
	print("Launching via wrapper: ", game_name, " -> ", absolute_target_path)
	
	var output = []
	var is_windows = OS.get_name() == "Windows"
	
	if is_windows:
		# Use python directly on Windows
		OS.execute("python", [wrapper_script, absolute_target_path], true, output)
	else:
		# Use bash and python3 on Linux/Pi
		OS.execute("bash", ["-c", "python3 '" + wrapper_script + "' '" + absolute_target_path + "'"], true, output)
		
	print("Game closed. Output: ", output)
	if games_grid.get_child_count() > 0:
		games_grid.get_child(0).get_child(0).grab_focus()

func toggle_debug_menu():
	debug_menu.visible = !debug_menu.visible
	if debug_menu.visible:
		$MainUI/DebugMenu/VBoxContainer/CloseButton.grab_focus()
	else:
		if games_grid.get_child_count() > 0:
			games_grid.get_child(0).get_child(0).grab_focus()

func _on_CloseDebugButton_pressed():
	toggle_debug_menu()
