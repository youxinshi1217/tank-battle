# -*- coding: utf-8 -*-
"""P3 鼠标玩家（三人混战）无头验证脚本。

覆盖：
  1) 三人混战开局：P1/P2/P3 均在场，出生点互异；
  2) P3 车身每帧向鼠标移动、到位停止；炮管朝向鼠标；
  3) 鼠标左键事件 → 恰好发射一枚 owner="p3" 子弹并扣 1 弹药；
  4) p3 子弹命中 P1：P1 毁、本局继续（仅 1 毁不结算）；
  5) 再毁 P2：本局结算 P3 胜、胜局记账、进入下一局；
  6) 1v1 回归：start_pvp 不产生 P3，p1 子弹命中 P2 正常结算。

跑法：SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy venv_py310/Scripts/python.exe _verify_p3_mouse.py
"""
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Game
from entities.bullet import Bullet

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))


def place(g, tank, sx, sy):
    g._reset_player_for_stage(sx, sy, tank)


def open_cell(g, taken, min_dist=6.0):
    for _ in range(200):
        sx, sy = g._pick_random_player_spawn()
        if all(math.hypot(sx - tx, sy - ty) >= min_dist * 50 for tx, ty in taken):
            return sx, sy
    return g._pick_random_player_spawn()


def near_open_cell(g, anchor, lo=120.0, hi=260.0):
    """取一个距 anchor [lo,hi] 像素、且直线路径不撞墙的合法出生点。"""
    from core.collision import rect_hits_obstacle

    def segment_open(p, q):
        steps = int(math.hypot(q[0] - p[0], q[1] - p[1]) // 8) + 1
        for i in range(steps + 1):
            t = i / max(1, steps)
            r = g.player3_tank.rect.copy()
            r.center = (round(p[0] + (q[0] - p[0]) * t),
                        round(p[1] + (q[1] - p[1]) * t))
            if rect_hits_obstacle(r, g.game_map):
                return False
        return True

    best = None
    for _ in range(400):
        sx, sy = g._pick_random_player_spawn()
        d = math.hypot(sx - anchor[0], sy - anchor[1])
        if lo <= d <= hi and segment_open(anchor, (sx, sy)):
            return sx, sy
        if best is None or d < math.hypot(best[0] - anchor[0], best[1] - anchor[1]):
            best = (sx, sy)
    return best


def warm_clock(g, frames=3):
    """预热时钟：首帧 tick 的 dt 尖峰会冲飞子弹/冲掉逻辑，先空转几帧。"""
    for _ in range(frames):
        g.clock.tick(60)


def main():
    pygame.init()
    g = Game()

    # ---------- 1) 三人混战开局 ----------
    g.start_pvp3(5)
    check("pvp3 模式标记", g.match_mode == "pvp3")
    check("P3 在场", g.player3_tank is not None)
    p1, p2, p3 = g.player_tank, g.player2_tank, g.player3_tank
    d12 = math.hypot(p1.x - p2.x, p1.y - p2.y)
    d13 = math.hypot(p1.x - p3.x, p1.y - p3.y)
    d23 = math.hypot(p2.x - p3.x, p2.y - p3.y)
    check("出生点互异(P1/P2)", d12 > 100, f"{d12:.0f}px")
    check("出生点互异(P1/P3)", d13 > 100, f"{d13:.0f}px")
    check("出生点互异(P2/P3)", d23 > 100, f"{d23:.0f}px")

    # 解冻开局提示，进入可操作战斗 + 预热时钟（防首帧 dt 尖峰）
    g.round_over_pause = 0.0
    g._pause_after = None
    g._round_overlay_hold = 0.0
    warm_clock(g)

    # ---------- 2) 布置到空旷点 ----------
    a = open_cell(g, [])
    b = open_cell(g, [a])
    c = open_cell(g, [a, b])
    tgt = near_open_cell(g, c)
    place(g, p1, *a)
    place(g, p2, *b)
    place(g, p3, *c)
    start_dist = math.hypot(tgt[0] - p3.x, tgt[1] - p3.y)

    # ---------- 3) 鼠标移动 + 朝向 ----------
    for _ in range(240):
        p3.handle_mouse_input(tgt, 1.0 / 60.0,
                              g._solid_tanks_excluding(p3))
    moved = math.hypot(tgt[0] - p3.x, tgt[1] - p3.y)
    check("P3 跟车逼近鼠标", moved < start_dist * 0.2,
          f"{start_dist:.0f}px -> {moved:.0f}px")
    check("P3 到位停止", moved <= 64 * 0.9 + 4, f"余 {moved:.1f}px")
    dx, dy = tgt[0] - p3.x, tgt[1] - p3.y
    if math.hypot(dx, dy) > 1.0:
        want = math.atan2(dx, -dy)
        diff = abs((p3.angle - want + math.pi) % (2 * math.pi) - math.pi)
        check("P3 炮管朝向鼠标", diff < 1e-6, f"Δ={diff:.2e}rad")

    # ---------- 4) 左键发射一枚 ----------
    ammo_before = p3.ammo
    pygame.event.post(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 100)}))
    g.handle_events()
    p3_bullets = [bl for bl in g.bullets if bl.owner == "p3"]
    check("左键一发 p3 子弹", len(p3_bullets) == 1 and p3.ammo == ammo_before - 1,
          f"bullets={len(g.bullets)} ammo {ammo_before}->{p3.ammo}")

    # ---------- 5) p3 弹命中 P1：本局继续 ----------
    g.bullets = []
    b_hit = Bullet(p1.rect.centerx, p1.rect.centery, 0, -1, g.game_map, owner="p3")
    b_hit.emitter = p3
    g.bullets.append(b_hit)
    warm_clock(g)
    g.clock.tick(60)
    g.update()
    check("p3 弹命中 P1 → P1 阵亡", p1 in g._dead_players)
    check("仅 1 毁本局不结算", not g._round_locked and g._round_locked is False)
    check("P1 死后不参与后续", p1 in g._dead_players)

    # ---------- 6) 再毁 P2：本局 P3 胜 ----------
    b_hit2 = Bullet(p2.rect.centerx, p2.rect.centery, 0, -1, g.game_map, owner="p3")
    b_hit2.emitter = p3
    g.bullets.append(b_hit2)
    warm_clock(g)
    g.clock.tick(60)
    g.update()
    check("P3 胜本局", g._last_round_winner == "p3"
          and g._series_wins.get("p3") == 1
          and g.round_manager.side_c_wins == 1)
    check("本局锁定", g._round_locked)
    check("系列未结束(先胜3局)", not g.round_manager.match_over
          and g.round_manager.current_round == 2)

    # ---------- 7) 1v1 回归 ----------
    g2 = Game()
    g2.start_pvp(5)
    check("1v1 无 P3", g2.player3_tank is None and g2.match_mode == "pvp")
    q1, q2 = g2.player_tank, g2.player2_tank
    pa = open_cell(g2, [])
    pb = open_cell(g2, [pa])
    place(g2, q1, *pa)
    place(g2, q2, *pb)
    g2.round_over_pause = 0.0
    g2._pause_after = None
    g2._round_overlay_hold = 0.0
    warm_clock(g2)
    bh = Bullet(q2.rect.centerx, q2.rect.centery, 0, -1, g2.game_map, owner="p1")
    bh.emitter = q1
    g2.bullets.append(bh)
    warm_clock(g2)
    g2.clock.tick(60)
    g2.update()
    check("1v1：p1 弹命中 P2 正常结算", q2 in g2._dead_players
          and g2.round_manager.side_a_wins == 1
          and g2._last_round_a_win is True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    main()
