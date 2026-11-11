# -*- coding: utf-8 -*-
"""PVP 胜方文案验证：局间提示 + 结算页标题。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M


def settle_pvp(game, tank):
    """模拟 PVP 单帧收集 + 结算：指定被摧毁坦克。"""
    game._pvp_destroyed[tank] = "test_owner"
    game._settle_pvp()


# ---------- 1) PVP 首局开战：intro 无胜方文案 ----------
game = M.Game()
game.start_pvp(rounds=3)
d = game._intermission_data()
assert d["result"] == "intro" and d["result_word"] == "", d
game.render()   # 渲染不崩

# ---------- 2) 玩家1击败玩家2 -> 玩家一胜利 ----------
settle_pvp(game, game.player2_tank)
assert game._last_round_a_win is True
d = game._intermission_data()
assert d["result"] == "win" and d["result_word"] == "玩家一胜利", d
assert d["a_wins"] == 1 and d["b_wins"] == 0
assert d["round"] == 2
game.render()   # 局间覆盖层渲染不崩

# ---------- 3) 玩家2击败玩家1 -> 玩家二胜利 ----------
game._start_round()
settle_pvp(game, game.player_tank)
assert game._last_round_a_win is False
d = game._intermission_data()
assert d["result"] == "loss" and d["result_word"] == "玩家二胜利", d
assert d["a_wins"] == 1 and d["b_wins"] == 1
assert d["round"] == 3
game.render()

# ---------- 4) 系列赛结算页标题：玩家一获胜（3局两胜）----------
class FakeFont:
    def __init__(self):
        self.captured = []
    def render(self, text, antialias, color):
        self.captured.append(text)
        return pygame.Surface((1, 1))

ff = FakeFont()
game.big_font = ff
game._start_round()
settle_pvp(game, game.player2_tank)          # 玩家一再胜 -> side_a_wins=2 -> match_over
assert game.round_manager.match_over and game.round_manager.a_win
game._render_result_panel()
assert ff.captured and ff.captured[0] == "玩家一胜利", ff.captured

# ---------- 5) 系列赛结算页标题：玩家二获胜 ----------
game2 = M.Game()
game2.start_pvp(rounds=3)
ff2 = FakeFont()
game2.big_font = ff2
settle_pvp(game2, game2.player_tank)         # P2 胜
game2._start_round()
settle_pvp(game2, game2.player_tank)         # P2 再胜 -> side_b_wins=2 -> match_over
assert game2.round_manager.match_over and not game2.round_manager.a_win
game2._render_result_panel()
assert ff2.captured and ff2.captured[0] == "玩家二胜利", ff2.captured

# ---------- 6) 双向胜负结算页标题均已覆盖（见 4/5） ----------

print("PVP win-text OK")