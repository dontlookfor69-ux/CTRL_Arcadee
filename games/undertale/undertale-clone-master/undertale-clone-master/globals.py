#!/usr/bin/python3
# coding=utf-8
"""
globals.py — Undertale clone shared state.

IMPORTANT: frisk and rooms are NOT imported here anymore.
They must be imported AFTER pygame.init() in main.py.
This prevents the crash caused by frisk/rooms touching pygame display
before it is initialised.
"""
import pygame

DEBUG = True

accept = [pygame.K_RETURN, pygame.K_z]
cancel = [pygame.KMOD_SHIFT, pygame.K_x]
option = [pygame.KMOD_CTRL, pygame.K_c]
up    = pygame.K_UP
left  = pygame.K_LEFT
right = pygame.K_RIGHT
down  = pygame.K_DOWN
arrows = [up, left, right, down]

width  = 640
height = 480
center = (int(width / 2), int(height / 2))
screen_rect = pygame.Rect((0, 0, width, height))

# DO NOT CHANGE THESE to avoid UNDOCUMENTED BAD STUFF.
running = True
event_lock = False
layers = {}

# These are set later by main.py after pygame.init()
display      = pygame.Surface((1, 1))  # internal 640x480 buffer (set in main.py)
real_display = None                     # actual fullscreen display (set in main.py)

# Lazy-initialised by main.py
chara = None
room  = None
last_save_room_name = ''
time  = 0
start_time = 0.0


def quit():
    """Gracefully quit the game."""
    global running
    running = False
    pygame.quit()
    raise SystemExit


class UndertaleError(Exception):
    """
    Fatal error that shows the Annoying Dog.
    Use when the SAVE is FUBAR or a room is broken.
    """
    pass
