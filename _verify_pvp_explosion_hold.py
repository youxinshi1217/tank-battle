# -*- coding: utf-8 -*-
"""PVP 击毁后"先播爆炸、再弹胜利提示"（explosion hold）验证。

背景：击毁瞬间会立即进入局间暂停，且暂停期 update 提前 return，导致爆炸特效被
冻结在首帧、胜利提示立刻盖上来。本次改动：
  - 暂停期纯特效（爆炸/飘字/震屏）继续推进
  - 覆盖层（胜利提示）延迟 PVP_EXPLOSION_HOLD_SECONDS（1.5s）后才出现
  - 被毁坦克隐藏（_dead_players）
  - 互毁/自弹自毁/最终局 统一先播爆炸

覆盖：
  1) 单次击毁：结算后进入暂停、hold=1.5s、覆盖层总时长扣除 hold
  2) 暂停期爆炸持续推进并在 hold 结束前完整消散
  3) hold 结束后才满足"显示覆盖层"条件（round_over_pause>0 且 hold<=0）
  4) 互毁作废：先播双方爆炸（无提示）再自动重开本局
  5) 被毁坦克已隐藏（_dead_players 写入）
  6) 自弹自毁：同样生成爆炸 + 隐藏坦克（与子弹击杀一致）
  7) 最终局（match_over）：先播爆炸再进结算页状态
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


class FakeClock:
    """固定帧长（默认 16ms）的假时钟：update() 用 get_time() 取 dt。"""

    def __init__(self, dt_ms: int = 16):
        self._dt = dt_ms

    def get_time(self) -> int:
        return self._dt

    def tick(self, fps: int) -> int:
        return self._dt


def new_game(rounds=3):
    g = M.Game()
    g.start_pvp(rounds=rounds)
    # 跳过首局 intro 提示
    g.round_over_pause = 0.0
    g._pause_after = None
    g._round_overlay_hold = 0.0
    g._pvp_destroyed = {}
    g.audio.play = lambda *a, **k: None
    return g


def kill_p2(game) -> None:
    """P1 用子弹击毁 P2（走真实命中 + 结算路径）。"""
    game._handle_player_bullet_hit_pvp("p1", game.player2_tank)
    game._settle_pvp()


def overlay_visible(game) -> bool:
    """与 render() 相同的覆盖层显示条件。"""
    return game.round_over_pause > 0 and game._round_overlay_hold <= 0


# ------------------------------------------------------------------ #
print("===== [1] 单次击毁：先播爆炸的暂停状态 =====", flush=True)
g1 = new_game()
kill_p2(g1)
check("[1] 击毁后进入局间暂停",
      g1.round_over_pause == M.ROUND_PAUSE_SECONDS)
check("[1] 暂停参数=ROUND_PAUSE_SECONDS/hold/'round'",
      (g1.round_over_pause, g1._round_overlay_hold, g1._pause_after) ==
      (M.ROUND_PAUSE_SECONDS, M.PVP_EXPLOSION_HOLD_SECONDS, "round"))
check("[1] 被毁坦克已隐藏", g1.player2_tank in g1._dead_players)
check("[1] 存活坦克未隐藏", g1.player_tank not in g1._dead_players)
check("[1] 生成爆炸", len(g1.explosions) == 1)
d1 = g1._intermission_data()
check("[1] 覆盖层总时长已扣除 hold",
      d1["total_pause"] == M.ROUND_PAUSE_SECONDS - M.PVP_EXPLOSION_HOLD_SECONDS)
check("[1] 覆盖层文案=玩家一胜利", d1["result_word"] == "玩家一胜利")
check("[1] hold 期间覆盖层不显示", not overlay_visible(g1))

# ------------------------------------------------------------------ #
print("\n===== [2] 暂停期爆炸持续推进、hold 后满足显示条件 =====", flush=True)
exp1 = g1.explosions[0]
age0 = exp1._age
g1.clock = FakeClock()
for _ in range(30):          # 0.48s：仍在 hold 内
    g1.update()
check("[2] 暂停期爆炸持续推进", exp1._age > age0 + 0.2)
check("[2] hold 未结束覆盖层仍不显示", g1.round_over_pause > 0 and not overlay_visible(g1))
# 继续推进，直到覆盖层条件首次满足（hold 刚结束的瞬间）
frames = 0
while not overlay_visible(g1):
    g1.update()
    frames += 1
    assert frames < 200, "hold 未在预期时间内结束"
d1b = g1._intermission_data()
check("[2] hold 结束后爆炸已完整消散",
      exp1._age >= exp1._lifetime or len(g1.explosions) == 0)
check("[2] hold 结束后满足覆盖层条件", overlay_visible(g1))
check("[2] 覆盖层出现时剩余从满格开始",
      abs(d1b["remaining"] - d1b["total_pause"]) < 0.05)
for _ in range(200):         # 推进到局间结束 → 下一局
    g1.update()
check("[2] 局间结束后进入下一局",
      g1.round_over_pause <= 0 and g1._pause_after is None)

# ------------------------------------------------------------------ #
print("\n===== [3] 互毁作废：先播爆炸、无提示、自动重开 =====", flush=True)
g3 = new_game()
g3._pvp_destroyed[g3.player_tank] = "p2"
g3._pvp_destroyed[g3.player2_tank] = "p1"
g3._settle_pvp()
check("[3] 互毁：暂停=hold/hold/'round'",
      (g3.round_over_pause, g3._round_overlay_hold, g3._pause_after) ==
      (M.PVP_EXPLOSION_HOLD_SECONDS, M.PVP_EXPLOSION_HOLD_SECONDS, "round"))
check("[3] 互毁：无胜方结算",
      not g3.round_manager.match_over and g3._last_round_a_win is None)
check("[3] 互毁：全程无覆盖层", not overlay_visible(g3))
g3.clock = FakeClock()
for _ in range(200):         # 推进到自动重开本局
    g3.update()
check("[3] 互毁：爆炸播完自动重开本局",
      g3.round_over_pause <= 0 and g3._pause_after is None)

# ------------------------------------------------------------------ #
print("\n===== [4] 自弹自毁：生成爆炸 + 隐藏坦克 =====", flush=True)
g4 = new_game()
b4 = Bullet(g4.player_tank.rect.centerx, g4.player_tank.rect.centery,
            0.0, 0.0, g4.game_map, owner="p1")
b4.bounce_count = 1
b4.rect.topleft = g4.player_tank.rect.topleft
g4.bullets.append(b4)
g4.update()                  # 一帧：自弹命中 + 结算
check("[4] 自弹自毁：生成爆炸", len(g4.explosions) == 1)
check("[4] 自弹自毁：隐藏坦克", g4.player_tank in g4._dead_players)
check("[4] 自弹自毁：对手得胜局", g4.round_manager.side_b_wins == 1)

# ------------------------------------------------------------------ #
print("\n===== [5] 最终局：先播爆炸再进结算页 =====", flush=True)
g5 = new_game(rounds=3)      # 三局两胜：胜 2 局即 match_over
kill_p2(g5)
check("[5] 首胜后未 match_over", not g5.round_manager.match_over)
# 跳过首胜的局间暂停，进入第 2 局
g5.round_over_pause = 0.0
g5._pause_after = None
g5._round_overlay_hold = 0.0
g5._start_round()
kill_p2(g5)                  # P1 二连胜 → match_over
check("[5] 二胜后 match_over", g5.round_manager.match_over)
check("[5] 最终局：先播爆炸、进入暂停(PLAYING)",
      g5.state == M.GameState.PLAYING
      and (g5.round_over_pause, g5._round_overlay_hold, g5._pause_after) ==
      (M.PVP_EXPLOSION_HOLD_SECONDS, M.PVP_EXPLOSION_HOLD_SECONDS, "result"))
check("[5] 最终局：hold 期间无覆盖层", not overlay_visible(g5))
g5.clock = FakeClock()
for _ in range(200):         # 推进过 hold → 进结算页状态
    g5.update()
check("[5] 最终局：hold 后进入结算页状态", g5.state == M.GameState.VICTORY)

# ------------------------------------------------------------------ #
pygame.quit()
fails = [n for n, ok in results if not ok]
print("\n===== 汇总 =====", flush=True)
print(f"共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}", flush=True)
for n, ok in results:
    if not ok:
        print("  FAILED:", n, flush=True)
sys.exit(1 if fails else 0)
