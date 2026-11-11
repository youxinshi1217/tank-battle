# -*- coding: utf-8 -*-
"""Task3 验证：双玩家战斗框架 —— P1/P2 开火 owner 归因（敌弹系统已退役）。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
from core.game_state import GameState

game = M.Game()
# 进入 PVP 双玩家骨架：手动注入 player2
from entities.player2_tank import Player2Tank
game.player2_tank = Player2Tank(400, 400, game.game_map)

# 1) 开火归因：模拟 P1/P2 开火 -> owner 正确（须重置冷却，否则同帧第二次被拦截）
game._try_fire_for(game.player_tank, "p1")
assert game.bullets and game.bullets[-1].owner == "p1"
game.fire_cooldown_remaining = 0.0
game._try_fire_for(game.player2_tank, "p2")
assert game.bullets[-1].owner == "p2"

# 2) 霰弹 owner 赋值
game._fire_shotgun_for(game.player_tank, "p1")
pellets = [b for b in game.bullets if getattr(b, "owner", None) == "p1"]
assert pellets, "霰弹弹丸应带 p1 owner"

print("T3 OK")
