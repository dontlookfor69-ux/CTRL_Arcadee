"""
arcade_controls.py — Shared joystick/button constants for CTRL_Arcadee
=======================================================================

Physical controller layout (two identical "axis 24 button gamepad with hat switch"):

  Joystick 0  →  Player 1 side of the cabinet
  Joystick 1  →  Player 2 side of the cabinet

HAT (D-pad / joystick lever):
  Hat 0  value (0,  1)  = UP
  Hat 0  value (0, -1)  = DOWN
  Hat 0  value (-1, 0)  = LEFT
  Hat 0  value ( 1, 0)  = RIGHT
  Hat 0  value (0,  0)  = CENTRE (neutral)

Buttons:
  Btn 0  = X   (primary fire / confirm)
  Btn 1  = A   (secondary action)
  Btn 2  = B   (tertiary action)
  Btn 3  = Y   (special / rotate)
  Btn 5  = Z   (= side button top — dash / use)
  Btn 6  = BACK  (back / cancel)
  Btn 7  = C   (= side button bottom — menu up)
  Btn 9  = START (Player 1 or Player 2 start)
  Btn 12 = MENU  (unknown / meta menu)
  Btn 13 = SIDE_BOT_R  (right side of cabinet, bottom)
  Btn 14 = SIDE_TOP_R  (right side of cabinet, top)

Controls summary per game
-------------------------
Pause menu   : HAT up/down = navigate | X (btn0) = confirm
Pac-Man P1   : HAT = move
Pac-Man P2   : HAT joy2 = move
Tetris       : HAT left/right = move | HAT up = rotate | HAT down = soft-drop | X = hard-drop
DOOM         : HAT left/right = turn | HAT up/down = move fwd/back | X = shoot
Just Shapes  : HAT = move | Z (btn5) = dash | START (btn9) = start / 1P
Just Shapes2P: joy2 HAT = move P2 | Z2 (btn5) = P2 dash
"""

# ── Joystick indices ─────────────────────────────────────────────────────────
JOY_P1 = 0
JOY_P2 = 1

# ── Button indices (same for both joysticks) ─────────────────────────────────
BTN_X      = 0   # Primary fire / confirm
BTN_A      = 1   # Secondary action
BTN_B      = 2   # Tertiary action
BTN_Y      = 3   # Special / rotate
BTN_Z      = 5   # Dash / use  (also labelled "side button top")
BTN_BACK   = 6   # Back / cancel
BTN_C      = 7   # Side button bottom
BTN_START  = 9   # Player 1 / Player 2 start
BTN_MENU   = 12  # Meta / unknown menu button
BTN_SIDE_BOT_R = 13  # Right-side bottom button (P1 joy only)
BTN_SIDE_TOP_R = 14  # Right-side top button    (P1 joy only)

# ── Hat values ───────────────────────────────────────────────────────────────
HAT_UP    = (0,  1)
HAT_DOWN  = (0, -1)
HAT_LEFT  = (-1, 0)
HAT_RIGHT = (1,  0)
HAT_NEUTRAL = (0, 0)

# ── Convenience: "any confirm button" for menus ──────────────────────────────
MENU_CONFIRM_BUTTONS = (BTN_X, BTN_A, BTN_START)
MENU_NAV_UP_BUTTONS  = ()   # handled via hat
MENU_NAV_DOWN_BUTTONS = ()  # handled via hat
MENU_BACK_BUTTONS    = (BTN_BACK,)
