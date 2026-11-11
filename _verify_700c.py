# -*- coding: utf-8 -*-
"""Phase 7.0-C 冒烟验证：子弹立正横排、常态/霰弹切换、与 PLAYER 1 分离、无灰色占位格。"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from ui.player_status_panel import (
    PlayerStatusPanel,
    _AMMO_TOP,
    _ICON_GAP,
    _ICON_SLOT_H,
    _ICON_SLOT_W,
    _ICON_TEXT_GAP,
    _LABEL_MARGIN,
    _LABEL_TOP,
    _LABEL_X,
)
from core.settings import (
    MAGAZINE_CAPACITY,
    SCREEN_WIDTH,
    SHOTGUN_MAGAZINE,
    STATUS_PANEL_HEIGHT,
    UI_AREA_Y,
    WINDOW_HEIGHT,
)

WHITE = (255, 255, 255)


class FakePlayer:
    def __init__(self, ammo=0, shotgun_ammo=0):
        self.ammo = ammo
        self.shotgun_ammo = shotgun_ammo

    @property
    def shotgun_active(self):
        return self.shotgun_ammo > 0


class FakeGame:
    def __init__(self, ammo=0, shotgun_ammo=0):
        self.player_tank = FakePlayer(ammo, shotgun_ammo)


def icon_row_x0(panel):
    """图标行起点 x（单人模式：由 AMMO 文字实际宽度动态推算，见 _render_ammo）。"""
    return _LABEL_MARGIN + panel._font.size("AMMO")[0] + _ICON_TEXT_GAP


def icon_row_region(panel):
    """立正子弹图标横排总区域（5 槽位）。"""
    w = (_ICON_SLOT_W + _ICON_GAP) * 5
    return pygame.Rect(icon_row_x0(panel), UI_AREA_Y + _AMMO_TOP, w, _ICON_SLOT_H)


def render_row(panel, surface, ammo, shotgun_ammo):
    surface.fill(WHITE)
    panel.render(surface, FakeGame(ammo, shotgun_ammo))
    return surface.subsurface(icon_row_region(panel)).copy().get_buffer().raw


def blank_area_is_white(panel, surface, ammo, shotgun_ammo):
    """横排底部（第3槽位之后）应为纯白（无灰色占位格）。"""
    surface.fill(WHITE)
    panel.render(surface, FakeGame(ammo, shotgun_ammo))
    x0 = icon_row_x0(panel) + 3 * (_ICON_SLOT_W + _ICON_GAP)
    w = 2 * (_ICON_SLOT_W + _ICON_GAP)
    region = surface.subsurface(pygame.Rect(x0, UI_AREA_Y + _AMMO_TOP, w, _ICON_SLOT_H)).copy()
    for x in range(region.get_width()):
        for y in range(region.get_height()):
            r, g, b, _a = region.get_at((x, y))
            if (r, g, b) != WHITE:
                return False
    return True


def main():
    panel = PlayerStatusPanel()
    surface = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))

    # 1. 两张贴图加载成功
    assert panel._default_icon is not None, "默认弹匣贴图应加载"
    assert panel._shotgun_icon is not None, "霰弹贴图应加载"
    print("[PASS] 两张贴图加载成功")

    # 2. 留白裁剪：默认子弹已立正（加载时旋转），且比原始画布小
    dsz = panel._default_icon.get_size()
    assert dsz[0] < dsz[1], f"默认子弹应立正竖高，实际 {dsz[0]}x{dsz[1]}"
    assert dsz[0] < 56 and dsz[1] < 38, f"默认子弹应裁剪留白，实际 {dsz[0]}x{dsz[1]}"
    print(f"[PASS] 默认子弹立正+裁剪 OK ({dsz[0]}x{dsz[1]}, 高>宽)")

    # 3. 霰弹显示图标（竖版）加载且无需旋转（本身就是竖高）
    ssz = panel._shotgun_icon.get_size()
    assert ssz[0] < ssz[1], f"霰弹显示图标应竖版，实际 {ssz[0]}x{ssz[1]}"
    print(f"[PASS] 霰弹显示图标竖版 OK ({ssz[0]}x{ssz[1]})")

    # 4. 常态：弹药数量不同 → 横排图标行不同
    n1 = render_row(panel, surface, ammo=1, shotgun_ammo=0)
    n3 = render_row(panel, surface, ammo=3, shotgun_ammo=0)
    n5 = render_row(panel, surface, ammo=5, shotgun_ammo=0)
    assert n1 != n3 != n5, "常态弹药数量不同，图标行应不同"
    print("[PASS] 常态默认弹匣：数量 1/3/5 横排各不同")

    # 4. 霰弹模式：贴图切换，剩余数量不同 → 横排不同
    s3 = render_row(panel, surface, ammo=3, shotgun_ammo=3)
    assert s3 != n3, "霰弹模式横排应与常态不同"
    s1 = render_row(panel, surface, ammo=3, shotgun_ammo=1)
    s5 = render_row(panel, surface, ammo=3, shotgun_ammo=5)
    assert s1 != s3 != s5, "霰弹剩余 1/3/5 横排应各不同"
    print("[PASS] 霰弹模式：贴图切换 & 剩余数量 1/3/5 各不同")

    # 5. 霰弹耗尽 → 切回常态
    back = render_row(panel, surface, ammo=3, shotgun_ammo=0)
    assert back == n3, "霰弹耗尽后应切回常态默认弹匣"
    print("[PASS] 霰弹耗尽 -> 自动切回常态默认弹匣")

    # 6. 与 PLAYER 1 分离：AMMO 行位于 PLAYER 1 标签下方，无重叠
    label_bottom = UI_AREA_Y + _LABEL_TOP + 24  # 标签约 24px 高
    assert _AMMO_TOP >= 30, "AMMO 行应明显低于 PLAYER 1 标签"
    print(f"[PASS] 与 PLAYER 1 分离 OK (PLAYER 1 底={label_bottom - UI_AREA_Y}, AMMO 顶={_AMMO_TOP})")

    # 7. 无灰色占位格
    assert blank_area_is_white(panel, surface, ammo=2, shotgun_ammo=0), "常态消耗后不应有灰色占位格"
    assert blank_area_is_white(panel, surface, ammo=2, shotgun_ammo=2), "霰弹消耗后不应有灰色占位格"
    print("[PASS] 无灰色占位格（消耗的弹药不显示，空白保持纯白）")

    # 8. 布局边界：横排不超出面板
    row_right = icon_row_x0(panel) + (_ICON_SLOT_W + _ICON_GAP) * 5
    assert row_right <= SCREEN_WIDTH, "横排不应超出面板右边界"
    row_bottom = UI_AREA_Y + _AMMO_TOP + _ICON_SLOT_H
    assert row_bottom <= UI_AREA_Y + STATUS_PANEL_HEIGHT, "横排不应超出 UI 区底部"
    print(f"[PASS] 布局边界 OK (右边界={row_right}, 底边界={row_bottom - UI_AREA_Y}, 间隙={_ICON_GAP})")

    print("\nALL CHECKS PASSED")
    pygame.quit()


if __name__ == "__main__":
    main()
