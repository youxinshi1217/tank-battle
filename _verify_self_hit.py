# -*- coding: utf-8 -*-
"""自弹反弹自伤（PVP）验证：SELF_HIT_ENABLED 规则。

覆盖：
  1) PVP  P1 自弹(反弹后)命中自己 → 对手(P2)得胜局 + 爆炸音效
  2) 对照  bounce=0 贴脸多帧 → 完全无效果（开火不自杀）
  3) PVP  护盾免疫自弹（不摧毁、不结算）
  4) PVP  P1 自弹自杀 → 不计击杀分/不加击毁数
  5) PVP  P2 自弹自杀 → 对手(P1)得胜局（对称）
  6) 回退  SELF_HIT_ENABLED=False → 自弹完全不生效
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
from entities.bullet import Bullet

results = []


def check(name: str, ok: bool) -> None:
    results.append((name, ok))
    print(("[PASS] " if ok else "[FAIL] ") + name, flush=True)


def step(game, frames: int, fps: int = 60) -> None:
    for _ in range(frames):
        game.clock.tick(fps)
        game.update()


def skip_intro(game) -> None:
    game.round_over_pause = 0.0
    game._pause_after = None
    game._pvp_destroyed = {}


def self_bullet(game, owner: str, tank, bounce: int = 1) -> Bullet:
    """构造一枚完全贴住 tank 的自弹：dx=dy=0 每帧不移动，保证持续重叠。"""
    b = Bullet(tank.rect.centerx, tank.rect.centery, 0.0, 0.0,
               game.game_map, owner=owner)
    b.bounce_count = bounce
    b.rect.topleft = tank.rect.topleft
    game.bullets.append(b)
    return b


def new_game(rounds=3):
    g = M.Game()
    g.start_pvp(rounds=rounds)
    skip_intro(g)
    return g


# ------------------------------------------------------------------ #
print("===== [1] PVP：P1 自弹(反弹后)命中自己 → P2 胜局 + 爆炸音效 =====", flush=True)
g1 = new_game()
calls = []
_orig_play = g1.audio.play
g1.audio.play = lambda *a, **k: calls.append(a[0] if a else None)
b1 = self_bullet(g1, "p1", g1.player_tank, bounce=1)
step(g1, 1)
g1.audio.play = _orig_play
check("[1] P1 自弹命中 → P2 得胜局",
      g1.round_manager.side_b_wins == 1)
check("[1] P1 自弹命中 → 子弹已销毁(alive=False)", not b1.alive)
check("[1] P1 自弹命中 → 播放玩家摧毁音效", "player_destroyed" in calls)

# ------------------------------------------------------------------ #
print("\n===== [2] 对照：bounce=0 贴脸 3 帧不触发（开火不自杀） =====", flush=True)
g2 = new_game()
self_bullet(g2, "p1", g2.player_tank, bounce=0)
step(g2, 3)
check("[2] bounce=0 贴脸 → 仍 PLAYING、无结算",
      g2.state == M.GameState.PLAYING and g2.round_over_pause == 0.0)
check("[2] bounce=0 贴脸 → 子弹仍在场", len(g2.bullets) == 1)

# ------------------------------------------------------------------ #
print("\n===== [3] PVP：护盾免疫自弹 =====", flush=True)
g3 = new_game()
g3.player_tank.apply_shield()
self_bullet(g3, "p1", g3.player_tank, bounce=1)
step(g3, 1)
check("[3] 护盾免疫自弹 → 未结算、仍 PLAYING",
      g3.state == M.GameState.PLAYING and g3.round_over_pause == 0.0)
check("[3] 护盾免疫自弹 → 玩家存活、子弹消耗",
      g3.player_tank not in g3._dead_players and len(g3.bullets) == 0)

# ------------------------------------------------------------------ #
print("\n===== [4] PVP：P1 自弹自杀 → P2 胜局、不计分 =====", flush=True)
g4 = new_game()
sc0 = g4.score_manager.current_score
kc0 = g4.score_manager.kill_count
self_bullet(g4, "p1", g4.player_tank, bounce=1)
step(g4, 1)
check("[4] P1 自弹自杀 → P2 得胜局", g4.round_manager.side_b_wins == 1)
check("[4] P1 自弹自杀 → 不计击杀分/不加击毁数",
      g4.score_manager.current_score == sc0
      and g4.score_manager.kill_count == kc0)

# ------------------------------------------------------------------ #
print("\n===== [5] PVP：P2 自弹自杀 → P1 胜局（对称） =====", flush=True)
g5 = new_game()
self_bullet(g5, "p2", g5.player2_tank, bounce=1)
step(g5, 1)
check("[5] P2 自弹自杀 → P1 得胜局", g5.round_manager.side_a_wins == 1)

# ------------------------------------------------------------------ #
print("\n===== [6] 回退开关：SELF_HIT_ENABLED=False =====", flush=True)
M.SELF_HIT_ENABLED = False
g6 = new_game()
self_bullet(g6, "p1", g6.player_tank, bounce=1)
step(g6, 1)
M.SELF_HIT_ENABLED = True
check("[6] 开关 False → 自弹完全不生效",
      g6.state == M.GameState.PLAYING and g6.round_over_pause == 0.0)
check("[6] 开关 False → 子弹未受影响", len(g6.bullets) == 1)

# ------------------------------------------------------------------ #
pygame.quit()
fails = [n for n, ok in results if not ok]
print("\n===== 汇总 =====", flush=True)
print(f"共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}", flush=True)
for n, ok in results:
    if not ok:
        print("  FAILED:", n, flush=True)
sys.exit(1 if fails else 0)