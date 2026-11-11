# -*- coding: utf-8 -*-
"""底部状态栏三人混战（pvp3）回归验证。

背景：旧实现把 P3 状态画到战场顶部（_render_pvp3_hud，已删），用户要求回退成
底部状态栏三栏：左红 P1 / 中绿 P3 / 右蓝 P2，中间 VS 圆删除，1v1 不变。

检查项：
 1) pvp3：底部状态栏三栏描边精确色 + 栏位分区（红全在左三分之一 / 绿全在中 /
    蓝全在右三分之二起）
 2) pvp3：中央 VS 圆两种特征色都不在场
 3) pvp3：战场顶部 60 行无旧 HUD 的 AMMO 黄槽
 4) 1v1 回归：左红右蓝两栏、无绿、中央 VS 圆仍在
 5) 单人模式面板渲染不炸（中性描边）
 6) _stat_values：pvp3 读 P1/P2/P3 各自系列赛胜局
 7) P3 身份图标为绿色（红贴图色相旋转生效）
 8) 中栏换弹读条居中绘制不炸（黑色填充落在中三分之一）
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")

import pygame

pygame.init()

from main import Game
from ui.player_status_panel import PlayerStatusPanel
from core.settings import (
    COLOR_AMMO_FULL,
    COLOR_PLAYER2_TANK,
    COLOR_PLAYER3_TANK,
    COLOR_PLAYER_TANK,
    SCREEN_WIDTH,
    STATUS_PANEL_HEIGHT,
    UI_AREA_VS_BG,
    UI_AREA_VS_RADIUS,
    UI_AREA_VS_RING,
    UI_AREA_Y,
    WINDOW_HEIGHT,
)

THIRD = SCREEN_WIDTH // 3            # 266
TWO_THIRD = THIRD * 2                # 532
RED = COLOR_PLAYER_TANK              # (204,30,30)
GREEN = COLOR_PLAYER3_TANK           # (46,190,92)
BLUE = COLOR_PLAYER2_TANK            # (60,90,210)
VS_CX = SCREEN_WIDTH // 2
VS_CY = UI_AREA_Y + STATUS_PANEL_HEIGHT // 2

passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"[PASS] {name}" + (f" ({extra})" if extra else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" ({extra})" if extra else ""))


def scan(surface, rect, target):
    """区域内精确等于 target 的像素坐标列表。"""
    hits = []
    t = tuple(target)
    for y in range(rect.top, rect.bottom):
        for x in range(rect.left, rect.right):
            if tuple(surface.get_at((x, y)))[:3] == t:
                hits.append((x, y))
    return hits


def ui_rect():
    return pygame.Rect(0, UI_AREA_Y, SCREEN_WIDTH, STATUS_PANEL_HEIGHT)


def vs_disc():
    r = UI_AREA_VS_RADIUS
    return pygame.Rect(VS_CX - r, VS_CY - r, 2 * r, 2 * r)


def render_capture(g):
    """解冻开局提示后渲染一帧，返回屏幕表面（含底部状态栏）。"""
    g.round_over_pause = 0.0
    g._pause_after = None
    g._round_overlay_hold = 0.0
    g.render()
    return g.screen


def main():
    # ---------- 1~3) pvp3 底部状态栏 ----------
    g = Game()
    g.start_pvp3(5)
    scr = render_capture(g)
    area = ui_rect()

    red = scan(scr, area, RED)
    green = scan(scr, area, GREEN)
    blue = scan(scr, area, BLUE)
    check("pvp3 底部有红栏（左三分之一）",
          len(red) > 0 and all(x < THIRD for x, _y in red),
          f"{len(red)}px")
    check("pvp3 底部有绿栏（中三分之一）",
          len(green) > 0 and all(THIRD <= x < TWO_THIRD for x, _y in green),
          f"{len(green)}px")
    check("pvp3 底部有蓝栏（右三分之一）",
          len(blue) > 0 and all(x >= TWO_THIRD for x, _y in blue),
          f"{len(blue)}px")

    disc = vs_disc()
    check("pvp3 中央无 VS 圆（外描边色不在场）",
          len(scan(scr, disc, UI_AREA_VS_RING)) == 0)
    check("pvp3 中央无 VS 圆（圆底色不在场）",
          len(scan(scr, disc, UI_AREA_VS_BG)) == 0)

    top = pygame.Rect(0, 0, SCREEN_WIDTH, 60)
    check("pvp3 战场顶部无旧弹药 HUD（无 AMMO 黄槽）",
          len(scan(scr, top, COLOR_AMMO_FULL)) == 0)

    # ---------- 8) 中栏换弹读条 ----------
    # is_reloading 是只读属性（= reload_remaining > 0），直接设 reload_remaining 触发
    g.player3_tank.ammo = 0
    g.player3_tank.reload_remaining = 1.0
    scr = render_capture(g)
    band = pygame.Rect(THIRD, UI_AREA_Y + 70, TWO_THIRD - THIRD, 24)
    black = scan(scr, band, (0, 0, 0))
    check("中栏换弹读条居中绘制（黑填充落在中三分之一）",
          len(black) > 0 and all(THIRD <= x < TWO_THIRD for x, _y in black),
          f"{len(black)}px")

    # ---------- 4) 1v1 回归 ----------
    g2 = Game()
    g2.start_pvp(5)
    scr2 = render_capture(g2)
    red2 = scan(scr2, area, RED)
    blue2 = scan(scr2, area, BLUE)
    green2 = scan(scr2, area, GREEN)
    check("1v1 回归：左红右蓝两栏",
          len(red2) > 0 and all(x < SCREEN_WIDTH // 2 for x, _y in red2)
          and len(blue2) > 0 and all(x >= SCREEN_WIDTH // 2 for x, _y in blue2),
          f"red={len(red2)} blue={len(blue2)}")
    check("1v1 回归：无绿栏", len(green2) == 0)
    check("1v1 回归：中央 VS 圆仍在",
          len(scan(scr2, vs_disc(), UI_AREA_VS_RING)) > 0)

    # ---------- 5) 单人模式不炸 ----------
    class StubTank:
        ammo = 3
        shotgun_active = False
        shotgun_ammo = 0
        is_reloading = False
        reload_remaining = 0.0

    class StubGameSingle:
        match_mode = "single"
        player_tank = StubTank()
        player2_tank = None
        player3_tank = None
        round_manager = None
        score_manager = None
        spawn_manager = None

    surf = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))
    try:
        PlayerStatusPanel().render(surf, StubGameSingle())
        neutral = scan(surf, area, (70, 70, 78))
        check("单人模式面板渲染不炸（中性描边在场）", len(neutral) > 0)
    except Exception as e:
        check("单人模式面板渲染不炸（中性描边在场）", False, repr(e))

    # ---------- 6) _stat_values pvp3 ----------
    class StubRM:
        side_a_wins = 1
        side_b_wins = 2
        side_c_wins = 3

    class StubGame3:
        match_mode = "pvp3"
        round_manager = StubRM()
        player_tank = object()
        player2_tank = object()
        player3_tank = object()

    panel = PlayerStatusPanel()
    sg = StubGame3()
    v1 = panel._stat_values(sg, sg.player_tank)
    v2 = panel._stat_values(sg, sg.player2_tank)
    v3 = panel._stat_values(sg, sg.player3_tank)
    check("pvp3 胜局读数 P1/P2/P3 = 1/2/3",
          v1 == (1, 1) and v2 == (2, 2) and v3 == (3, 3),
          f"{v1} {v2} {v3}")

    # ---------- 7) P3 图标为绿色 ----------
    icon = panel._p3_icon
    ok_icon = icon is not None
    if ok_icon:
        rs = gs = bs = n = 0
        w, h = icon.get_size()
        for x in range(w):
            for y in range(h):
                c = icon.get_at((x, y))
                if c.a > 128:
                    rs += c.r
                    gs += c.g
                    bs += c.b
                    n += 1
        ok_icon = n > 0 and gs // n > rs // n + 20 and gs // n > bs // n + 20
    check("P3 身份图标为绿色（红贴图色相旋转生效）", ok_icon)

    print(f"\n{passed} passed, {failed} failed")
    pygame.quit()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
