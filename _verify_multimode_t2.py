# -*- coding: utf-8 -*-
"""Task2 验证：Player2Tank 方向键+空格映射；继承 P1 基础能力。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame

pygame.init()
from entities.player2_tank import Player2Tank
from maps.game_map import GameMap
from maps import tile as T

# 空地图
g = [[T.TileType.EMPTY for _ in range(25)] for _ in range(25)]
gm = GameMap.from_map_data(g, [[False]*25 for _ in range(25)])

p2 = Player2Tank(100, 100, gm)
assert p2.ammo == 5 and p2.can_fire()

# 方向键：上=前进
keys = pygame.key.get_pressed()
import pygame as _p
class _Keys(dict):
    def __getitem__(self, k): return dict.get(self, k, False)
    def __setitem__(self, k, v): dict.__setitem__(self, k, v)
k = _Keys()
k[pygame.K_UP] = True
p2.handle_input(k, 1/60)
assert p2.physics.vx != 0 or p2.physics.vy != 0, "方向键上应产生位移"

# 左转
p2.physics.vx = 0.0; p2.physics.vy = 0.0
k2 = _Keys(); k2[pygame.K_LEFT] = True
old_a = p2.physics.facing_angle
p2.handle_input(k2, 1/60)
assert p2.physics.facing_angle != old_a, "方向键左应转向"

# 继承能力：弹药消耗
p2.consume_ammo()
assert p2.ammo == 4
# 继承护盾
p2.apply_shield()
assert p2.is_shielded

print("T2 OK")
