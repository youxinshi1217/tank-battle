# -*- coding: utf-8 -*-
"""
地图渲染器
把 GameMap 的 Tile 层画到 pygame Surface。碰撞只认 Tile 层；本层视觉可精细表达，
不受单一格子方块限制（细节：边缘高光、田盾内衬、铆钉、裂纹、颗粒噪点）。

渲染规则（纯视觉，不影响碰撞）：
  - 每个障碍格取 "基础色"：优先 GameMap.visual_colors（按区域配色），否则按 TileType 默认。
  - LJR 装饰笔画（is_decorative）保持干净默认色 + 细描边，作为视觉焦点。
  - 普通障碍用现代细节画法：顶部受光、底部投影、内衬面板、角铆钉、随机裂纹与颗粒，
    使每一格不再单调。
"""
import math
import random

import pygame

from core.settings import (
    TILE_SIZE,
    COLOR_BRICK,
    COLOR_STEEL,
    COLOR_GRID_LINE,
    SHOW_GRID_LINES,
)
from maps.tile import TileType
from maps.game_map import GameMap

_TILE_COLORS = {
    TileType.BRICK: COLOR_BRICK,
    TileType.STEEL: COLOR_STEEL,
}


def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def _shade(color, d):
    return (_clamp(color[0] + d), _clamp(color[1] + d), _clamp(color[2] + d))


def _lighter(color):
    return _shade(color, 26)


def _darker(color):
    return _shade(color, -30)


def _rect(cx, cy, r):
    """以( cx,cy ) 为中心、半径 r 的 pygame Rect（pygame.arc 用）。"""
    return pygame.Rect(int(cx - r), int(cy - r), int(r * 2), int(r * 2))


def _lower_half(points, cy):
    """取多边形位于 cy 下方的部分（用于叠背光侧壁），并闭合到上下分界。

    若整个多边形都在 cy 之下/之上，退化为原多边形。
    """
    below = [p for p in points if p[1] >= cy]
    above = [p for p in points if p[1] < cy]
    if not below:
        return points
    if not above:
        return points
    # 找出穿越分界线的两个交点并拼接闭合
    out = []
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        if (y0 - cy) * (y1 - cy) < 0:
            t = (cy - y0) / (y1 - y0)
            out.append((x0 + (x1 - x0) * t, cy))
            out.append((x1, y1))
        elif y0 >= cy:
            out.append((x0, y0))
    return out if len(out) >= 3 else points


def _draw_modern_obstacle(surface, rect, base, rng):
    """现代细节障碍：高光/阴影/内衬/铆钉/裂纹/颗粒。"""
    x0, y0, w, h = rect
    tint = rng.randint(-10, 10)
    base = _shade(base, tint)

    light = _shade(base, 40)     # 顶部受光
    dark = _shade(base, -34)     # 底部/边缘投影
    edge = _shade(base, -24)

    # 平铺底色
    pygame.draw.rect(surface, base, rect)

    # 受光与投影边（1px）
    pygame.draw.line(surface, light, (x0, y0), (x0 + w - 1, y0))
    pygame.draw.line(surface, light, (x0, y0), (x0, y0 + h - 1))
    pygame.draw.line(surface, dark, (x0, y0 + h - 1), (x0 + w - 1, y0 + h - 1), 2)
    pygame.draw.line(surface, dark, (x0 + w - 1, y0), (x0 + w - 1, y0 + h - 1), 2)

    # 田盾内衬面板
    px0, py0 = x0 + 2, y0 + 2
    px1, py1 = x0 + w - 3, y0 + h - 3
    pygame.draw.rect(surface, _shade(base, -18), (px0, py0, px1 - px0, py1 - py0))
    pygame.draw.line(surface, dark, (px0, py1), (px1, py1))
    pygame.draw.line(surface, dark, (px1, py0), (px1, py1))

    # 四角铆钉
    rivet = _shade(base, 52)
    rivet_d = _shade(base, -22)
    for rx, ry in ((px0, py0), (px1 - 1, py0), (px0, py1 - 1), (px1 - 1, py1 - 1)):
        pygame.draw.rect(surface, rivet_d, (rx + 1, ry + 1, 3, 3))
        pygame.draw.rect(surface, rivet, (rx, ry, 3, 3))

    # 随机短裂纹（横向边角的破败感）
    for _ in range(rng.randint(1, 3)):
        a = x0 + rng.randint(3, w - 5)
        b = y0 + rng.randint(3, h - 5)
        la = rng.choice([-1, 1]) * rng.randint(2, 4)
        lb = rng.choice([-1, 1]) * rng.randint(2, 4)
        pygame.draw.line(surface, _shade(base, -40), (a, b), (a + la, b + lb), 1)

    # 微观颗粒/脏点（小颗粒，打破纯色）
    for _ in range(rng.randint(0, 4)):
        sx = x0 + rng.randint(1, w - 2)
        sy = y0 + rng.randint(1, h - 2)
        pygame.draw.rect(surface, _shade(base, rng.choice([-26, -16, 18, 30])), (sx, sy, 2, 1))


def _draw_plain_obstacle(surface, rect, color):
    """干净默认色 + 细描边（用于 LJR 装饰笔画，保持字形聚焦）。"""
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, _shade(color, -40), rect, 1)


class MapRenderer:
    def __init__(self, game_map: GameMap):
        self.game_map = game_map

    def render(self, surface: pygame.Surface) -> None:
        # Phase 8.6 平滑形状层（Stage 5「戈壁环岛」起）：
        # 碰撞走连续几何层（game_map.geometry，圆/圆环浮点判定）；
        # 视觉由形状层单独表达 —— 若 shapes["shapes_only"] 为真，
        # 则跳过逐格方块绘制，只画形状层（避免「方块 + 真圆弧」叠画成乱码观感）。
        # 两层共用同一组半径/半宽/球心，物理上不可能不一致。
        shapes = getattr(self.game_map, "shapes", None)
        if shapes and shapes.get("shapes_only"):
            self._draw_ground(surface, shapes.get("ground"))
            self._draw_shapes(surface, shapes)
            return
        if SHOW_GRID_LINES:
            self._draw_grid_lines(surface)
        self._draw_obstacles(surface)
        self._draw_decorations(surface)
        if shapes:
            self._draw_shapes(surface, shapes)

    # ------------------------------------------------------------------
    # 平滑形状层（纯视觉）
    # ------------------------------------------------------------------
    def _draw_ground(self, surface: pygame.Surface, ground) -> None:
        """纯形状层模式下的战场底色（沙地 + 极淡暗角）。"""
        if not ground:
            return
        size = self.game_map.size * TILE_SIZE
        surface.fill(ground)
        for i in range(6):
            v = 8 - i
            shade = (_clamp(ground[0] - v), _clamp(ground[1] - v), _clamp(ground[2] - v))
            pygame.draw.rect(surface, shade, (i * 8, i * 8, size - i * 16, size - i * 16), 8)
    def _draw_shapes(self, surface: pygame.Surface, shapes: dict) -> None:
        """绘制平滑形状：扇形沙洲 + 钢球 + LJR 水印。

        形状描述里的坐标单位是「格」，此处统一乘 TILE_SIZE 转像素。
        """
        # 1) LJR 水印先画（在最底层，像铺在沙地上的水印）
        wm = shapes.get("watermark")
        if wm:
            self._draw_watermark(surface, wm)

        # 2) 沙洲环段：先落影，再主体，再受光边
        segs = shapes.get("segments")
        if segs is None:
            segs = shapes.get("fans", [])     # 兼容旧数据
        for seg in segs:
            self._draw_segment(surface, seg)

        # 3) 钢球：落影 + 本体 + 描边 + 高光
        for ball in shapes.get("balls", []):
            self._draw_ball(surface, ball)

    def _draw_watermark(self, surface: pygame.Surface, wm: dict) -> None:
        """LJR 水印：按字模点阵逐单元画半透明方块，居中于地图。

        ★ 修Bug（2026-10-21）：原来用 `special_flags=pygame.BLEND_RGBA_ADD`。
        实测 pygame 的 BLEND_RGBA_ADD **完全忽略 src 的 alpha 通道**，
        直接把 (126,92,54,72) 的 RGB 全量相加，底色 (206,172,118) 直接
        饱和成 (255,255,172) —— 一块刺眼的亮黄斑，而不是淡色水印。
        改用普通 alpha 混合（去掉 special_flags），得到 (183,149,100)，
        才是「沙地上淡淡一层字」的效果。
        """
        scale = wm["scale"]
        unit = TILE_SIZE * scale
        w = wm["width"] * unit
        h = wm["height"] * unit
        size = self.game_map.size * TILE_SIZE
        ox = (size - w) / 2.0
        oy = (size - h) / 2.0
        layer = pygame.Surface((int(w) + 2, int(h) + 2), pygame.SRCALPHA)
        r, g, b = wm["color"]
        for cx, cy in wm["cells"]:
            layer.fill(
                (r, g, b, wm["alpha"]),
                pygame.Rect(int(cx * unit), int(cy * unit), int(unit), int(unit)),
            )
        # 普通 alpha 混合（不用 ADD），alpha 才真正生效
        surface.blit(layer, (int(ox), int(oy)))

    def _draw_segment(self, surface: pygame.Surface, seg: dict) -> None:
        """梯形环段：一整圈环形沙洲被 8 条缺口切成 8 段，每段是饱满的梯形环块。

        几何（关键，勿随意改）：
          - 外沿（远离圆心）：恒定 r_out 的**正圆弧**，角跨度 2*span_out。
          - 内沿（朝向圆心）：恒定 r_in 的**正圆弧**，角跨度 2*span_in。
            span_in > span_out（缺口走廊在内侧张得更开），所以内侧更宽、
            外侧更窄 —— 正是手绘稿里「梯形环段、内宽外窄」的形态。
          - 两侧是**直边**（从 (base-span, r_in) 连到 (base-span, r_out)），
            不是曲线，这样形如厚实的梯形砖，不会出现尖刺 / 箭羽。

        角跨度由碰撞侧的走廊半宽 asin(NOTCH_HALF_W / r) 反推，视觉与碰撞一致，
        玩家看到的沙洲就一定撞得到（无隐形墙）。

        画法（自下而上）：
          1) 落影：整片右下偏移的深色副本。
          2) 主体：整片受光色打底。
          3) 背光侧壁：沿背光侧边缘压一条深色带。
          4) 描边：外沿亮弧 + 内沿暗弧（都只在本段角区间内）。
        """
        cx = seg["cx"] * TILE_SIZE
        cy = seg["cy"] * TILE_SIZE
        r_in = seg["r_in"] * TILE_SIZE
        r_out = seg["r_out"] * TILE_SIZE
        base = math.radians(seg["angle"])
        s_in = math.radians(seg["span_in"])
        s_out = math.radians(seg["span_out"])
        steps = 48

        def arc(rad, s):
            """以 base 为中心、角跨度 +-s 的圆弧点列（从 -s 正走到 +s）。"""
            pts = []
            for i in range(steps + 1):
                a = base - s + 2.0 * s * i / steps
                pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
            return pts

        # 外沿正走（宽） -> 右直边 -> 内沿回程（窄） -> 左直边自动闭合
        pts = arc(r_out, s_out) + arc(r_in, s_in)[::-1]
        if len(pts) < 3:
            return

        # 1) 体积感：内壁暗带 + 外沿高光。
        #    ★ 早期版本用「整片偏移投影」表达体积，结果影子会横跨缺口、
        #    在缺口两侧戳出一排深色弧块（看着像地图破了个洞）。
        #    改用「内壁暗带（r_in 起 7px 的暗色条）+ 外沿亮边」后，
        #    体积感有了，缺口干干净净，且暗带天然不会溢出到缺口里
        #    （它只沿内弧走，两端被环段自身截断）。
        inner_band = []
        n_i = max(8, steps // 2)
        for i in range(n_i + 1):
            a_ = base - s_in + 2 * s_in * i / n_i
            inner_band.append((cx + math.cos(a_) * (r_in + 7.0),
                               cy + math.sin(a_) * (r_in + 7.0)))
        for i in range(n_i, -1, -1):
            a_ = base - s_in + 2 * s_in * i / n_i
            inner_band.append((cx + math.cos(a_) * r_in,
                               cy + math.sin(a_) * r_in))
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if len(inner_band) >= 3:
            pygame.draw.polygon(layer, (*seg["shadow"], 120), inner_band)
        surface.blit(layer, (0, 0))

        # 2) 主体：整片沙黄
        pygame.draw.polygon(surface, seg["top"], pts)

        # 4) 描边：外沿亮弧（受光高光）+ 内沿暗弧（内壁阴影）
        pygame.draw.arc(surface, _lighter(seg["top"]), _rect(cx, cy, r_out - 1),
                        math.degrees(base - s_out), math.degrees(base + s_out), 3)
        pygame.draw.arc(surface, _darker(seg["side"]), _rect(cx, cy, r_in + 1),
                        math.degrees(base - s_in), math.degrees(base + s_in), 2)
        # 两条直边（缺口侧壁）描一道暗线，让「通道」的直边感更明确
        for sgn in (1.0, -1.0):
            p1 = (cx + math.cos(base + sgn * s_out) * r_out,
                  cy + math.sin(base + sgn * s_out) * r_out)
            p2 = (cx + math.cos(base + sgn * s_in) * r_in,
                  cy + math.sin(base + sgn * s_in) * r_in)
            pygame.draw.line(surface, _darker(seg["side"]), p1, p2, 2)

    def _draw_ball(self, surface: pygame.Surface, ball: dict) -> None:
        """钢球：真圆 + 落影 + 描边 + 左上高光。"""
        cx = int(ball["cx"] * TILE_SIZE)
        cy = int(ball["cy"] * TILE_SIZE)
        # ★ 用 build_shapes 预先算好的整数像素半径（已 math.ceil）。
        # 不能用 int(ball["r"]*TILE_SIZE)：pygame 画圆像素覆盖不是完美圆，
        # 截断 1px 就会在边界留下「格心是障碍色却是空地」的亚像素失配。
        r = max(3, int(ball.get("r_px") or math.ceil(ball["r"] * TILE_SIZE)))

        # 落影
        sh = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(sh, (*ball["shadow"], 95), (cx + 8, cy + 10), r)
        surface.blit(sh, (0, 0))

        # 本体 + 描边
        pygame.draw.circle(surface, ball["rim"], (cx, cy), r)
        pygame.draw.circle(surface, ball["light"], (cx, cy), max(2, r - 2))
        # 高光
        pygame.draw.circle(surface, _lighter(ball["light"]),
                           (cx - r // 3, cy - r // 3), max(1, r // 3))

    def _draw_decorations(self, surface: pygame.Surface) -> None:
        """绘制装饰覆盖层（纯观感，不参与碰撞）。
        装饰格一定落在 EMPTY 上；此处叠加警示灯/泄漏/蒸汽/管线。
        """
        deco = getattr(self.game_map, "decorations", None)
        if not deco:
            return
        for kind, row, col in deco:
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            if kind == "wl":        # 红色警示灯 + 辉光
                pygame.draw.circle(surface, (120, 20, 20),
                                   (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 6)
                pygame.draw.circle(surface, (255, 60, 40),
                                   (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 3)
            elif kind == "arc":     # 高压电弧（淡蓝细线）
                pygame.draw.line(surface, (120, 190, 255),
                                 (x + 4, y + 8), (x + TILE_SIZE - 6, y + 4), 1)
            elif kind == "lk":      # 化学泄漏（青色液滴）
                pygame.draw.circle(surface, (80, 220, 200),
                                   (x + TILE_SIZE // 2, y + TILE_SIZE - 6), 4)
                pygame.draw.rect(surface, (50, 170, 160),
                                 (x + TILE_SIZE // 2 - 2, y + 6, 4, TILE_SIZE - 14))
            elif kind == "st":      # 蒸汽喷口（淡白雾团）
                for d, a in ((3, 90), (5, 60)):
                    pygame.draw.circle(surface, (220, 222, 220),
                                       (x + TILE_SIZE // 2, y + TILE_SIZE // 2), d)
            elif kind == "pipe":    # 边缘管线（深灰横管）
                pygame.draw.rect(surface, (90, 92, 98),
                                 (x + 6, y + TILE_SIZE // 2 - 2, TILE_SIZE - 12, 4))
                pygame.draw.rect(surface, (60, 62, 66),
                                 (x + 6, y + TILE_SIZE // 2 + 1, TILE_SIZE - 12, 2))

    def _draw_grid_lines(self, surface: pygame.Surface) -> None:
        size = self.game_map.size
        width = size * TILE_SIZE
        height = size * TILE_SIZE
        for col in range(size + 1):
            x = col * TILE_SIZE
            pygame.draw.line(surface, COLOR_GRID_LINE, (x, 0), (x, height))
        for row in range(size + 1):
            y = row * TILE_SIZE
            pygame.draw.line(surface, COLOR_GRID_LINE, (0, y), (width, y))

    def _draw_obstacles(self, surface: pygame.Surface) -> None:
        visual = getattr(self.game_map, "visual_colors", None)
        for row, col, tile_type, is_decorative in self.game_map.iter_tiles():
            base = None
            if visual is not None and visual[row][col]:
                base = visual[row][col]
            if base is None:
                base = _TILE_COLORS.get(tile_type)
            if base is None:
                continue
            rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if is_decorative:
                _draw_plain_obstacle(surface, rect, base)
            else:
                _draw_modern_obstacle(surface, rect, base,
                                      random.Random((row << 8) | col))