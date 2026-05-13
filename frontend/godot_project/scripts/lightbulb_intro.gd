extends Node2D

signal lightbulb_lit

# Pendulum state
var angle = 0.8          # Starting angle in radians (pulled to the side)
var angular_velocity = 0.0
var angular_damping = 0.995   # Slight energy loss per frame (air resistance)
var gravity = 9.8
var cord_length_px = 300.0    # Pixel length of the cord

var flicker_state = "off"  # "off", "flickering", "on"
var flicker_timer = 0.0
var flicker_alpha = 0.0
var icons_visible = false

var pivot = Vector2(960, 0)

func _ready():
    pivot.x = OS.get_window_size().x / 2
    set_process(true)
    set_physics_process(true)

func _physics_process(delta):
    # Pendulum differential equation: α = -(g/L) * sin(θ)
    var angular_acceleration = -(gravity / cord_length_px) * sin(angle)
    angular_velocity += angular_acceleration * delta * 60.0  # Scale to 60fps
    angular_velocity *= angular_damping
    angle += angular_velocity * delta * 60.0

func _process(delta):
    flicker_timer += delta
    
    match flicker_state:
        "off":
            flicker_alpha = 0.0
            if flicker_timer > 1.5:  # Start flickering after 1.5 seconds
                flicker_state = "flickering"
                flicker_timer = 0.0
        
        "flickering":
            # Random rapid on/off
            flicker_alpha = 1.0 if randf() > 0.4 else 0.0
            if flicker_timer > 2.0:  # Flicker for 2 seconds
                flicker_state = "on"
                flicker_alpha = 1.0
                icons_visible = true
                emit_signal("lightbulb_lit")
        
        "on":
            # Subtle slow flicker once fully on
            flicker_alpha = 1.0 - randf() * 0.05
    
    update()  # Trigger _draw()

func _draw():
    var bulb_pos = pivot + Vector2(sin(angle), cos(angle)) * cord_length_px
    _draw_cord(pivot, bulb_pos)
    _draw_bulb(bulb_pos, flicker_state != "off" and flicker_alpha > 0.5, flicker_alpha)

func _draw_cord(p1, p2):
    draw_line(p1, p2, Color(0.4, 0.35, 0.3), 4)  # Thick brownish cord

func _draw_bulb(center: Vector2, is_lit: bool, f_alpha: float):
    var bulb_radius = 60.0
    
    # Glow effect when lit (draw before bulb so it's behind)
    if is_lit:
        for i in range(8):
            var glow_r = bulb_radius + (8 - i) * 18
            var glow_alpha = f_alpha * 0.06 * (i / 8.0)
            draw_circle(center, glow_r, Color(1.0, 0.95, 0.7, glow_alpha))
    
    # Glass body
    var glass_color = Color(0.85, 0.88, 0.75, 0.9) if not is_lit else Color(1.0, 0.97, 0.8, 0.95)
    draw_circle(center, bulb_radius, glass_color)
    
    # 3D highlight (top-left)
    var highlight_pos = center + Vector2(-bulb_radius * 0.3, -bulb_radius * 0.35)
    draw_circle(highlight_pos, bulb_radius * 0.22, Color(1, 1, 1, 0.6 if is_lit else 0.3))
    
    # Filament (zigzag)
    var fil_color = Color(1.0, 0.8, 0.2, 1.0) if is_lit else Color(0.5, 0.4, 0.2, 0.8)
    var fil_points = [
        center + Vector2(-8, 10),
        center + Vector2(-4, 0),
        center + Vector2(0, 10),
        center + Vector2(4, 0),
        center + Vector2(8, 10),
    ]
    for i in range(fil_points.size() - 1):
        draw_line(fil_points[i], fil_points[i+1], fil_color, 2)
    
    # Base/neck (rectangle below bulb)
    var neck_rect = Rect2(center.x - 18, center.y + bulb_radius - 8, 36, 40)
    draw_rect(neck_rect, Color(0.6, 0.6, 0.6, 1.0))
    # Screw rings on base
    for ring_y in [8, 16, 24]:
        draw_line(
            Vector2(center.x - 18, center.y + bulb_radius - 8 + ring_y),
            Vector2(center.x + 18, center.y + bulb_radius - 8 + ring_y),
            Color(0.4, 0.4, 0.4, 1.0), 2
        )
