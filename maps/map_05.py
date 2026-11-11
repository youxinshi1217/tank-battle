# -*- coding: utf-8 -*-
"""
地图数据 - Stage 5「戈壁环岛」（完整环形沙洲 + 8 条等宽缺口，为追踪导弹定制）

设计来源：用户手绘稿《新地图.jpg》。图上实测：环带内沿约 6.6 格、外沿约 9.2 格
（厚约 2.6 格 = 83px），8 条缺口均匀分布，缺口之间是饱满的梯形沙洲，
四角各一颗大钢球、缺口正前方外侧各一颗小钢球。

★ 本关的**唯一铁律**（2026-10-21 用户拍板：背景和实体必须位置一致）：
    **视觉形状 == 碰撞形状 == 手绘稿形状，一个数都不膨胀。**

  演进过两代模型，最终一代才是对的：
    第一代「形状外扩 HALF_DIAG(0.707 格) 后，格心落在外扩形状内判障碍」——
      墙比手绘稿粗 1.41 格（45px），画出来是"胖环岛"；
    第二代「视觉/碰撞共用 solid_at()，但最后仍四舍五入进 25×25 方格子」——
      圆被强行降级成方块：74px 的钢球实际占 96×96px（放大 2.04 倍），
      全图障碍多占 21.5 格；且格心采样让缺口净宽从 96px 掉到 70px。
    第三代（现行）★ **连续几何碰撞**：
      环带/走廊/钢球全部以浮点几何直接参与物理判定，**不经格子**。
      `RingGeometry.rect_hit()` 用「矩形 vs 圆」解析解（零误差）+
      「矩形 vs 圆环」2px 采样（角点/中心必测）；导弹视线同样直接问几何。
      grid 层降级为只服务「出生点筛选 / 渲染回退」，物理真碰撞以几何为准。
      钢球半径回到真实美术尺寸（小球 27px / 大球 43px）—— 看到多大撞多大。

★ 关键教训（务必保留此注释）：缺口**不能用极角扇形**开。
  方格网在 0°/45°/22.5° 方向的采样密度不同，用扇形开缺口会让 8 条通道
  宽窄剧烈悬殊（实测最窄 0.00 格、最宽 4.00 格，差 4 格），玩家一半通道
  过不了一辆坦克。改用「到缺口中线的垂直距离 <= half_w」判定后，宽度与
  方向完全无关 —— 实测 8 条全部等宽、宽度差 0.00。

★ 缺口侧边为什么是**直边**而不是径向边：
  缺口边界 = 「到缺口中线的垂直距离 = NOTCH_HALF_W」的那条平行直线。
  环段是内外两段圆弧 + 两条直边围成的梯形；梯形的两个端点分别落在
  r_in / r_out 两个圆上，且两点的垂直距离都恰好 = NOTCH_HALF_W
  （因为 sin(asin(hw/r)) = hw/r），所以**那条直边就是碰撞判定用的那条线**，
  角模型与垂直距离模型完全等价，不是近似。

关卡设计（设计语言：戈壁黄昏 / 环形沙洲）：
  - 一整圈「环形沙洲」：内沿 6.6 格、外沿 9.2 格，环带厚 2.6 格（83px），
    是全场唯一的实体屏障，把地图分成「中央湖心广场」与「外环戈壁跑道」。
  - 8 条「缺口通道」以 45° 等分（22.5° + 45°k），走廊半宽 1.5 格
    = 通道净宽 96px ≈ 3.8 辆坦克，8 条完全等宽（宽度差 0.00）。
    这是全场唯一的高机动走廊，也是躲避追踪导弹的主路线。
  - 中央「湖心广场」半径 6.6 格全空，LJR 以半透明水印铺在广场地面 ——
    导弹来袭时的 ultimate dodging 舞台。
  - 8 颗小钢球（真实半径 0.85 格 = 27px）落在每条缺口的**正前方外侧**
    （轨道半径 11.5 格），球与沙洲缝隙 46px ≈ 1.86 辆坦克，
    既给缺口制造"冲出后急转"的节奏，又不封死通道。
  - 4 颗大钢球（真实半径 1.35 格 = 43px）落在 45/135/225/315° 对角远处
    （轨道半径 12.3 格），缝隙 56px ≈ 2.24 辆坦克，
    作为外环的四角掩体与狙击点。

导出：
  build_map_data()    -> (grid, is_decorative)  25×25 网格（只用于出生筛选/回退渲染）
  build_geometry()    -> RingGeometry 连续几何（★ 物理碰撞真口径）
  build_visual_data() -> 25×25 RGB|None 区域配色（逐格回退路径）
  build_shapes()      -> dict 平滑形状层（环带/钢球/LJR 水印，渲染器绘制）
  build_decorations() -> list 本关无格级装饰
"""
import math

from core.settings import GRID_SIZE, TILE_SIZE
from maps.tile import TileType
from maps.letters import LJR_SEQUENCE, LETTER_WIDTH, LETTER_GAP

# 地图中心（格坐标；25×25 地图中心是 12.5）
CX = CY = GRID_SIZE / 2.0

# 一个格的对角半长（0.707 格 = 22.6px）。
# ★ 已停用：连续几何模型下不再需要任何膨胀（保留常量仅供历史脚本引用）。
HALF_DIAG = math.sqrt(2) / 2.0

# ---------------------------------------------------------------
# 环形沙洲（BRICK）—— 尺寸即手绘稿尺寸，零膨胀
# ---------------------------------------------------------------
RING_R_IN = 6.60                # 内沿（格）= 211px
RING_R_OUT = 9.20               # 外沿（格）= 294px，环带厚 2.6 格 = 83px

# ---------------------------------------------------------------
# 缺口通道（径向走廊，半宽 = 通道半宽）
# ---------------------------------------------------------------
NOTCH_COUNT = 8
NOTCH_PHASE = 180.0 / NOTCH_COUNT   # 22.5°，落在两条环带"扇段"之间
NOTCH_HALF_W = 1.50            # 走廊半宽（格）-> 通道净宽 3.0 格 = 96px

# ---------------------------------------------------------------
# 钢球（STEEL）—— 半径即真实美术半径（连续几何，零膨胀）
# 球与沙洲缝隙：小球 46px / 大球 56px（均 >= 1.5 辆坦克 = 37.5px）
# ---------------------------------------------------------------
BALL_SMALL_R = 0.85            # 小球真实半径（格）= 27px，直径 54px
BALL_SMALL_ORBIT = 11.50       # 小球轨道半径（格）= 368px，缺口正前方外侧
BALL_BIG_R = 1.35              # 大球真实半径（格）= 43px，直径 86px
BALL_BIG_ORBIT = 12.30         # 大球轨道半径（格）= 394px

# ---------------------------------------------------------------
# LJR 水印（纯视觉，不占格、不参与碰撞）
# ---------------------------------------------------------------
LJR_WATERMARK_SCALE = 0.62      # 字模单元边长（格）
LJR_WATERMARK_ALPHA = 72
LJR_WATERMARK_COLOR = (126, 92, 54)

# ---------------------------------------------------------------
# 配色（对齐手绘稿的戈壁黄昏色系）
# ---------------------------------------------------------------
RING_TOP = (240, 216, 172)         # 沙洲受光面（浅米黄）
RING_SIDE = (152, 108, 58)         # 沙洲背光侧壁
RING_SHADOW = (94, 64, 34)         # 沙洲落影
BALL_LIGHT = (228, 224, 214)       # 钢球本体
BALL_RIM = (126, 126, 132)         # 钢球描边
BALL_BALL_SHADOW = (76, 54, 32)    # 钢球落影
GROUND_COLOR = (206, 172, 118)     # 沙地底色（比沙洲略深一档，缺口读作通道而非深坑）

# 玩家出生参考点（main 实际随机出生，此处仅回归校验）
PLAYER_SPAWN = (2, 2)

# 兼容旧引用名（本关形态已改为完整环带）
SECTOR_R_IN = RING_R_IN
SECTOR_R_OUT = RING_R_OUT
SECTOR_COUNT = NOTCH_COUNT


# ==================================================================
# 几何工具
# ==================================================================
def _ang_diff(a, b):
    """两个角度（度）之间的最小夹角，落在 [0, 180]。"""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def notch_angles():
    """8 条缺口通道的中线角（度）：22.5° + 45°k。"""
    step = 360.0 / NOTCH_COUNT
    return [NOTCH_PHASE + step * i for i in range(NOTCH_COUNT)]


def arc_segment_angles():
    """8 段环带实体的中线角（度）：落在两条缺口**正中间**。

    ★ 修 Bug（2026-10-21）：原来写的是 `half = step / 2.0`（=22.5°），
    而 `notch_angles()` 也是 `NOTCH_PHASE = 180/8 = 22.5` —— 两者数值相同，
    导致 8 段实体被画在**缺口位置**上，与碰撞网格整体错位 22.5°。
    正确的环段中线 = 缺口相位 + 半步长 = `NOTCH_PHASE + step/2`
    （缺口正中间 = 0°, 45°, 90° ...），与手绘稿一致。
    """
    step = 360.0 / NOTCH_COUNT
    mid = NOTCH_PHASE + step / 2.0      # 缺口正中间 = 0°, 45°, 90° ...
    return [mid + step * i for i in range(NOTCH_COUNT)]


def ball_specs():
    """全部钢球：(球心格x, 球心格y, 真实半径格, 是否大球)。

    ★ 半径就是**真实美术半径**（连续几何模型，2026-10-23 起）：
      早期为了迁就格子判定把半径撑到 1.15 格（含格半对角 0.707），
      结果 74px 的球实际占 96×96px。现在物理直接对圆判定，半径回归原尺寸，
      绘制半径 = 碰撞半径（像素取整向上），看到多大就撞多大。
    """
    out = []
    for deg in notch_angles():
        a = math.radians(deg)
        out.append((CX + math.cos(a) * BALL_SMALL_ORBIT,
                    CY + math.sin(a) * BALL_SMALL_ORBIT,
                    BALL_SMALL_R, False))
    for deg in (45.0, 135.0, 225.0, 315.0):
        a = math.radians(deg)
        out.append((CX + math.cos(a) * BALL_BIG_ORBIT,
                    CY + math.sin(a) * BALL_BIG_ORBIT,
                    BALL_BIG_R, True))
    return out


def in_notch_corridor(px, py, half_w=None):
    """点 (px,py) 是否落在任一缺口走廊内。

    ★ 核心：用「到缺口中线的垂直距离」判定，而非极角扇形。
    这样缺口宽度与它相对方格网的方向（0°/22.5°/45°）完全无关，
    8 条通道绝对等宽。横向切向距离 = |(p-c) ·perp|，perp 为中线的法向。
    """
    half_w = NOTCH_HALF_W if half_w is None else half_w
    dx = px - CX
    dy = py - CY
    for deg in notch_angles():
        s = math.sin(math.radians(deg))
        c = math.cos(math.radians(deg))
        if abs(-dx * s + dy * c) <= half_w:
            return True
    return False


def _in_ring(px, py):
    """点 (px,py) 是否落在环形沙洲内（**零膨胀**，尺寸即手绘稿尺寸）。"""
    d = math.hypot(px - CX, py - CY)
    if d < RING_R_IN or d > RING_R_OUT:
        return False
    return not in_notch_corridor(px, py)


def _in_ball(px, py):
    """点 (px,py) 是否落在某个钢球的占位圆内。"""
    for bx, by, br, _ in ball_specs():
        if math.hypot(px - bx, py - by) <= br:
            return True
    return False


def solid_at(px, py):
    """★ 网格口径的碰撞判据（格坐标）。

    注意：自 2026-10-23 连续几何模型起，**物理真碰撞不再走这个函数**，
    改走 `RingGeometry.rect_hit()`（像素矩形 vs 连续几何）。
    本函数保留给：网格生成（出生筛选/渲染回退）、视觉回退配色、验证脚本。
    """
    if _in_ball(px, py):
        return True
    return _in_ring(px, py)


# ==================================================================
# 连续几何（★ 物理碰撞真口径，2026-10-23 起）
# ==================================================================
class RingGeometry:
    """第 5 关的连续几何：环带 + 缺口走廊 + 钢球，全部浮点、不经格子。

    设计原则（用户拍板「背景和实体位置必须一样」的最终落地）：
      - 与渲染层（build_shapes）共用同一组半径/半宽/球心，物理上不可能不一致；
      - 矩形 vs 钢球：**解析解**（矩形上离球心最近的点），零误差；
      - 矩形 vs 环带：外接盒粗筛 + 2px 步长采样，**四角与中心必测**，
        偶合误差 ≤2px（相对 32px 的格子模型是 16 倍精度提升）；
      - 点判定（导弹视线）：直接查连续几何。
    """

    def __init__(self):
        self.cx = CX
        self.cy = CY
        self.r_in = RING_R_IN
        self.r_out = RING_R_OUT
        self.half_w = NOTCH_HALF_W
        # 预计算 8 条走廊的法向（sin, cos），供热路径复用
        self._normals = [(math.sin(math.radians(a)), math.cos(math.radians(a)))
                         for a in notch_angles()]
        self.balls = [(bx, by, br) for bx, by, br, _ in ball_specs()]
        # 钢球外接盒（格），热路径先挡掉绝大多数测试
        self._bboxes = [(bx - br, by - br, bx + br, by + br)
                        for bx, by, br in self.balls]

    # ---------------------------------------------------------- 点
    def point_in_ring(self, gx, gy):
        """格坐标：是否在环形沙洲内（不含走廊）。"""
        d2 = (gx - self.cx) ** 2 + (gy - self.cy) ** 2
        if d2 < self.r_in * self.r_in or d2 > self.r_out * self.r_out:
            return False
        dx, dy = gx - self.cx, gy - self.cy
        for s, c in self._normals:
            if abs(-dx * s + dy * c) <= self.half_w:
                return False
        return True

    def point_solid(self, px, py):
        """像素坐标：连续几何点判定（导弹视线 / 采样用）。"""
        gx, gy = px / TILE_SIZE, py / TILE_SIZE
        for (x0, y0, x1, y1), (bx, by, br) in zip(self._bboxes, self.balls):
            if x0 <= gx <= x1 and y0 <= gy <= y1:
                if (gx - bx) ** 2 + (gy - by) ** 2 <= br * br:
                    return True
        return self.point_in_ring(gx, gy)

    # ---------------------------------------------------------- 矩形
    def rect_hit(self, rect):
        """像素矩形是否撞上连续几何（pygame.Rect，左上/右下闭区间近似）。

        顺序：钢球解析解 -> 环带粗筛 -> 环带 2px 采样。
        """
        ts = TILE_SIZE
        x0, y0 = rect.left / ts, rect.top / ts
        x1, y1 = rect.right / ts, rect.bottom / ts

        # --- 钢球：矩形上离球心最近的点，距离 <= 半径即撞 ---
        for (bx0, by0, bx1, by1), (bx, by, br) in zip(self._bboxes, self.balls):
            if x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1:
                continue
            nx = min(max(bx, x0), x1)
            ny = min(max(by, y0), y1)
            if (nx - bx) ** 2 + (ny - by) ** 2 <= br * br:
                return True

        # --- 环带粗筛 1：矩形四角全在内圆盘内 -> 不可能碰环带 ---
        corners = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
        if all((px - self.cx) ** 2 + (py - self.cy) ** 2 < self.r_in * self.r_in
               for px, py in corners):
            return False
        # --- 环带粗筛 2：矩形整体在外圆盘外 -> 不可能碰环带 ---
        ddx = max(x0 - self.cx, 0.0, self.cx - x1)
        ddy = max(y0 - self.cy, 0.0, self.cy - y1)
        if ddx * ddx + ddy * ddy > self.r_out * self.r_out:
            return False

        # --- 环带精判：2px 采样（四角 + 中心 + 网格点） ---
        pts = list(corners)
        pts.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0))
        step = 2.0 / ts
        gy = y0
        while gy <= y1 + 1e-9:
            gx = x0
            while gx <= x1 + 1e-9:
                pts.append((gx, gy))
                gx += step
            gy += step
        for gx, gy in pts:
            if self.point_in_ring(gx, gy):
                return True
        return False


def build_geometry():
    """导出本关的连续几何（供 core/collision.py 与导弹视线使用）。"""
    return RingGeometry()


# ==================================================================
# 碰撞层
# ==================================================================
def build_map_data():
    """生成 25×25 网格。

    ★ 2026-10-23 起，这个网格**不再是物理碰撞层**，只服务两件事：
        1. 出生点初筛（main._pick_random_player_spawn 的 3×3 规则）；
        2. 无形状层时的渲染回退。
      真正的物理碰撞走 `build_geometry()` 的连续几何。
      出生点除本表外还会过一遍几何矩形精查（见 main.py），双保险。

    网格口径：格心落在 `solid_at()` 为真的位置即障碍（中心点判定，无膨胀）。
    """
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    is_dec = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if solid_at(c + 0.5, r + 0.5):
                grid[r][c] = TileType.STEEL if _in_ball(c + 0.5, r + 0.5) \
                    else TileType.BRICK

    pr, pc = PLAYER_SPAWN
    if 0 <= pr < GRID_SIZE and 0 <= pc < GRID_SIZE:
        grid[pr][pc] = TileType.EMPTY
        is_dec[pr][pc] = False

    return grid, is_dec


def build_visual_data():
    """区域配色（逐格回退路径；本关主渲染走形状层 build_shapes）。

    ★ 与 build_map_data 共用 `solid_at()`，保证回退路径下
    「配色」与「碰撞」也完全一致。
    """
    visual = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            px, py = c + 0.5, r + 0.5
            if not solid_at(px, py):
                continue
            if _in_ball(px, py):
                visual[r][c] = BALL_LIGHT
            else:
                # 上半受光、下半背光，贴合手绘稿的黄昏光感
                visual[r][c] = RING_TOP if (py - CY) <= 0 else RING_SIDE
    return visual


def build_decorations():
    """本关无格级装饰覆盖层（沙洲与钢球由形状层绘制）。"""
    return []


# ==================================================================
# 平滑形状层（由 maps/map_renderer.py 的形状钩子绘制，纯视觉）
# ==================================================================
def build_shapes():
    """返回平滑形状描述，供渲染器画真圆环沙洲 / 真圆钢球 / LJR 水印。

    ★ 本函数是 build_map_data 的**镜像**：所有半径、走廊半宽都直接取
      手绘稿尺寸，**不加任何膨胀**，与 `solid_at()` 逐点同源。
      角跨度按「走廊半宽 = NOTCH_HALF_W」反推：
          span(r) = step/2 - asin(NOTCH_HALF_W / r)
      注意 `asin(x/r)` 随 r 增大而减小，所以 **span_out > span_in（内窄外宽）**，
      与手绘稿里「梯形环段、外宽内窄」的形态一致。
    """
    step = 360.0 / NOTCH_COUNT
    half_w = NOTCH_HALF_W
    r_in_v = RING_R_IN
    r_out_v = RING_R_OUT
    half_in = math.degrees(math.asin(min(1.0, half_w / r_in_v)))
    half_out = math.degrees(math.asin(min(1.0, half_w / r_out_v)))

    segments = []
    for deg in arc_segment_angles():
        segments.append({
            "cx": CX, "cy": CY,
            "angle": deg,
            "r_in": r_in_v,
            "r_out": r_out_v,
            # 每段实体的角区间（相对中线，左右对称）；内窄外宽
            "span_in": max(0.0, step / 2.0 - half_in),
            "span_out": max(0.0, step / 2.0 - half_out),
            "top": RING_TOP,
            "side": RING_SIDE,
            "shadow": RING_SHADOW,
        })

    balls = []
    for bx, by, br, big in ball_specs():
        # 绘制半径 = 碰撞半径（像素向上取整，多出的半像素是绘制侧保守量），
        # 连续几何下「看到多大就撞多大」严格成立。
        r_px = int(math.ceil(br * TILE_SIZE))
        balls.append({
            "cx": bx, "cy": by,
            "r": br,                 # 占位半径（格）
            "r_px": r_px,            # 绘制半径（像素，整数）
            "visual_r": br,
            "big": big,
            "light": BALL_LIGHT, "rim": BALL_RIM, "shadow": BALL_BALL_SHADOW,
        })

    return {
        "shapes_only": True,        # 视觉完全交给形状层，不画逐格方块
        "ground": GROUND_COLOR,     # 沙地底色
        "segments": segments,       # 8 段梯形环段（替代旧 fans）
        "balls": balls,
        "watermark": _watermark_spec(),
    }


def _watermark_spec():
    """LJR 水印：以字模点阵描述，渲染时按 scale 逐单元画半透明方块。"""
    cells = []
    cursor = 0
    for pattern in LJR_SEQUENCE:
        for ri, row_str in enumerate(pattern):
            for ci, ch in enumerate(row_str):
                if ch == "1":
                    cells.append((cursor + ci, ri))
        cursor += LETTER_WIDTH + LETTER_GAP
    width = cursor - LETTER_GAP
    height = max(ri for _, ri in cells) + 1
    return {
        "cells": cells,
        "width": width,
        "height": height,
        "scale": LJR_WATERMARK_SCALE,
        "alpha": LJR_WATERMARK_ALPHA,
        "color": LJR_WATERMARK_COLOR,
    }


# ==================================================================
# 自检入口（供 _verify_stage5.py 复用，保证验证与正式数据同源）
# ==================================================================
def notch_clear_width(ang_deg, r_from=None, r_to=None):
    """量某条缺口通道的真实净宽（格）—— **几何口径**。

    沿缺口中线径向扫，每个截面量「垂直于径向」的连续空地宽度，取全程最小。
    这是玩家真正能感受到的通道宽度（应 = 2 × NOTCH_HALF_W = 3.0 格 = 96px）。

    ★ 2026-10-23 改为几何点扫（`RingGeometry.point_solid`）。
      历史坑：早年用「连续点 floor 成格子下标」判空地，在 22.5°/67.5°
      这类非轴向角度上会落到隔壁环段的格心，8 条缺口全被量成 0.00 格；
      后来改格心口径，又因格子只有 32px 粗、采样步长 0.05 格，
      把 96px 的走廊量成 70px（少 26px）。几何点扫才还原真实宽度。
    ★ 量程约定（否则读数无意义）：
      - 只从**环带中段**量到外沿：内沿处缺口是尖角，垂直扫量必读 0，是假读数；
      - **不把钢球算进来**：缺口正前方站着球（小球轨道 11.5 - 半径 0.85
        = 外缘 10.65），球挡路是设计本意，不是「通道窄」。
    """
    geo = RingGeometry()
    ts = TILE_SIZE

    r_from = RING_R_IN - 0.4 if r_from is None else r_from
    r_to = RING_R_OUT + 0.4 if r_to is None else r_to
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    worst = 99.0
    r = max(r_from, (RING_R_IN + RING_R_OUT) / 2.0)
    while r <= min(r_to, RING_R_OUT) + 1e-9:
        bx, by = CX + ux * r, CY + uy * r
        o = 0.0
        while o <= 4.0:
            o += 0.02
            if geo.point_solid((bx - uy * o) * ts, (by + ux * o) * ts):
                break
        worst = min(worst, (o - 0.02) * 2)
        r += 0.05
    return worst
