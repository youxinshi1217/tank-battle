# -*- coding: utf-8 -*-
"""Task5 验证：PVP 纯 1v1 —— 对局数选择、玩家互射结算、互毁作废、护盾免疫、PVP 局间文案、无波次敌人。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
from core.game_state import GameState
from core.match_config import get_win_rounds_from_n

# 1) 对局数选择：5/7/9/11/13 -> 胜局 3/4/5/6/7（⌈N/2⌉）
for n, w in [(5, 3), (7, 4), (9, 5), (11, 6), (13, 7)]:
    assert get_win_rounds_from_n(n) == w, (n, w)

# 2) start_pvp(5)：PVP 启动、P2 恒在场、局制 5/3、首局开战版
game = M.Game()
game.start_pvp(rounds=5)
assert game.match_mode == "pvp"
assert game.player2_tank is not None
assert game.round_manager.rounds_total == 5 and game.round_manager.win_needed == 3
assert game.round_over_pause > 0 and game._pause_after == "intro"

# 3) start_pvp(9)：局制 9/5；PVP 局间文案 P1/P2 + 五局四胜
game.start_pvp(rounds=9)
assert game.round_manager.rounds_total == 9 and game.round_manager.win_needed == 5
d = game._intermission_data()
assert d["a_label"] == "玩家一" and d["b_label"] == "玩家二"
assert d["format"] == "五局四胜"

# 4) 玩家互射：P1 子弹命中 P2 -> 收集 + 亲手 +1 分
game._pvp_destroyed = {}
before = game.score_manager.current_score
game._handle_player_bullet_hit_pvp("p1", game.player2_tank)
assert game._pvp_destroyed.get(game.player2_tank) == "p1"
assert game.score_manager.current_score == before + 1

# 5) 结算：P2 被摧毁 -> side_a(P1) 胜局 +1；系列未结束
game._settle_pvp()
assert game.round_manager.side_a_wins == 1
assert game._last_round_a_win is True
assert game.state == GameState.PLAYING

# 6) 互毁作废重开：双方本帧都被摧毁 -> 不记胜局、先播爆炸(hold)再自动重开复位
wins_before = game.round_manager.side_a_wins
game._pvp_destroyed = {game.player_tank: "p2", game.player2_tank: "p1"}
game._settle_pvp()
assert game.round_manager.side_a_wins == wins_before      # 不记胜局
assert game.round_over_pause == M.PVP_EXPLOSION_HOLD_SECONDS
assert game._round_overlay_hold == M.PVP_EXPLOSION_HOLD_SECONDS
assert game._pause_after == "round"
for _ in range(300):                                        # 推进过爆炸 hold
    game.clock.tick(60)
    game.update()
assert game.round_manager.round_over is False            # 爆炸播完已重开复位

# 7) 护盾免疫：P2 持盾时被 P1 命中 -> 不摧毁、无 +1 分
game.player2_tank.shield_remaining = 5.0
game._pvp_destroyed = {}
game._handle_player_bullet_hit_pvp("p1", game.player2_tank)
assert game.player2_tank not in game._pvp_destroyed, "护盾应免疫对方子弹"

# 8) PVP 不生成波次敌人、不推进波次结算
game.round_over_pause = 0.0
game._pause_after = None
game.bullets = []
game._pvp_destroyed = {}
for _ in range(60):
    game.clock.tick(60)
    game.update()
assert len(game.enemy_tanks) == 0, "PVP 不应生成波次敌人"
assert game.round_manager.side_a_wins == wins_before      # 无波次结算
assert game.round_manager.side_b_wins == 0

print("T5 OK")
