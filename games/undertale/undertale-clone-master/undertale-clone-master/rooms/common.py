#!/usr/bin/python3
# coding=utf-8
import math
import threading
import pygame
import globals
import draw
import os

class Room:
    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == 'background':
            try:
                pos = self.bg_pan
            except AttributeError:
                pos = (0, 0)
            self.background_layer.surface.blit(value, pos)
            self.background_layer.flip()
        elif key == 'bg_pos':
            try:
                self.background_layer.surface.blit(self.background, value)
                self.background_layer.flip()
            except AttributeError:
                pass

    def __int__(self):
        return int(self.id)

    def __init__(self, *args):
        self.id = 0
        self.name = ''
        self.background_layer = draw.get_layer(65536)
        self.background = pygame.Surface((globals.width, globals.height))
        self.bg_pan = (0, 0)
        self.objects = []
        self.song = None
        self.run_update = True
        self.entered = False
        self.exited = False
        self.update_thread = threading.Thread(target=self.update_loop,
                                              name='update loop for {}'.format(self.__class__.__name__), daemon=True)
        self.update_thread.start()
        self.c = 0
        self.clock = pygame.time.Clock()

    def __del__(self):
        self.run_update = False

    def draw(self):
        for i in self.objects:
            i.redraw()
            i.sprite.update()
            layer = draw.get_layer(i.weight)
            layer.surface.blit(i.sprite.image[0], i.pos)
            layer.flip()
        self.c += 1
        if self.c >= 30:
            self.c = 0
            globals.time += 1
        pygame.event.pump()
        self.clock.tick(30)

    def update_loop(self):
        pass

    def on_enter(self):
        if self.entered: return False
        self.entered = True
        return True

    def on_exit(self):
        if self.exited: return False
        self.exited = True
        return True

class RoomWalkable(Room):
    def __init__(self):
        Room.__init__(self)
        self.clock = pygame.time.Clock()
        self.chara_layer = draw.get_layer(128)
        self.walk_animate_init()
        self.walk_tick = 0

    def walk_animate_init(self):
        scale_factor = 2
        def scale_img(img, times):
            return pygame.transform.scale(img, (int(img.get_width() * times), int(img.get_height() * times)))
        
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        def get_p(n): return os.path.join(base, "sprites", n)

        self.upcycle = [scale_img(pygame.image.load(get_p(f"spr_maincharau_{i}.png")), scale_factor) for i in range(4)]
        self.down_cycle = [scale_img(pygame.image.load(get_p(f"spr_maincharad_{i}.png")), scale_factor) for i in range(4)]
        self.left_cycle = [scale_img(pygame.image.load(get_p(f"spr_maincharal_{i}.png")), scale_factor) for i in range(2)]
        self.right_cycle = [scale_img(pygame.image.load(get_p(f"spr_maincharar_{i}.png")), scale_factor) for i in range(2)]

    def walk_animate_loop(self):
        chara = globals.chara
        if not chara: return
        
        cycles = [self.upcycle, self.right_cycle, self.down_cycle, self.left_cycle]
        chara.sprite = cycles[chara.dir][0]
        if chara.moving:
            self.walk_tick += 1
            if self.walk_tick % 10 == 0:
                chara.sprite = cycles[chara.dir][(self.walk_tick // 10) % len(cycles[chara.dir])]

    def draw(self):
        super().draw()
        chara = globals.chara
        if not chara: return
        
        self.walk_animate_loop()
        self.chara_layer.clear()
        self.chara_layer.surface.blit(chara.sprite, (int(chara.pos[0]), int(chara.pos[1])))
        self.chara_layer.flip()

        if not globals.event_lock:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: globals.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: globals.quit()
                    if event.key in globals.accept:
                        for i in self.objects:
                            if abs(i.x - chara.x) < 50 and abs(i.y - chara.y) < 50:
                                i.interact(chara)
                                break
            
            keys = pygame.key.get_pressed()
            chara.moving = False
            if keys[globals.left]:
                chara.dir = 3; chara.moving = True; chara.x -= chara.movespeed
            elif keys[globals.right]:
                chara.dir = 1; chara.moving = True; chara.x += chara.movespeed
            elif keys[globals.up]:
                chara.dir = 0; chara.moving = True; chara.y -= chara.movespeed
            elif keys[globals.down]:
                chara.dir = 2; chara.moving = True; chara.y += chara.movespeed

        self.clock.tick(30)
