# -*- coding: utf-8 -*-
"""
Phase 8.4 - 工业迷宫主题工具（maps/map_themes.py）

职责：
  - 提供「工业模块 × 损坏档」复用模板（同一工厂、不同破损 → 叙事一致而非复制粘贴）。
  - 提供四边「边缘管网」装饰覆盖数据（纯观感，不参与碰撞）。
  - 提供工业区域配色常量。
  - 提供装饰覆盖数据生成器（红警示灯 / 化学泄漏 / 蒸汽喷口 / 管线）。

约束：
  - 不修改 letters.py / 不新增 Tile / 装饰格一律落在 EMPTY（不落墙，不碰碰撞）。
"""
import random

from core.settings import GRID_SIZE
from maps.tile import TileType
from maps import ljr_zone

# 地图默认：LJR 放置原点（与 Stage 1 一致，保护层逻辑可复用）
LJR_ORIGIN = (10, 5)


def build_labyrinth(grid, *, origin=LJR_ORIGIN, seed=20260823,
                    loop_extra=4, steel_count=24, cw=2, sw=1, dw=None):
    """确定性「迷宫」生成（Phase 8.4 迷宫优化）。

    7×7 密网格，每格 2×2 开放"转身室"，格与格之间为窄门（dw：1=只开 1 格窄巷，
    2=2 宽开阔门），递归回溯生成生成树 + 额外打墙成环路（去小巷），再把中央 LJR
    保护区清为开阔广场。

    - dw=1 → 极窄巷：狭窄 1 宽隧道 + 2×2 转身室（坦克 25.6px 可直行 1 宽、在 2×2 内转向）
    - 全连通（生成树 + 广场枢纽），无孤立死区；固定 seed → 确定性。
    """
    rng = random.Random(seed)
    step = cw + sw
    n = (GRID_SIZE - 3) // step            # 25x25 内可容纳的粗格数（7）
    if dw is None:
        dw = cw
    # ① 内部全填墙
    for r in range(1, GRID_SIZE - 1):
        for c in range(1, GRID_SIZE - 1):
            grid[r][c] = TileType.BRICK
    # ② 雕粗网格转身室（每块 cw×cw）
    for cr in range(n):
        for cc in range(n):
            r0, c0 = cr * step + 1, cc * step + 1
            for dr in range(cw):
                for dc in range(cw):
                    grid[r0 + dr][c0 + dc] = TileType.EMPTY

    def open_door(cr, cc, nr, nc):
        # 墙带坐标：cr/cr+1 之间墙在行 cr*step+cw+1；cc/cc+1 之间墙在列 cc*step+cw+1
        # 门宽 dw，居中并偏向墙角雕刻 → 制造视线死角（窄巷）
        mid = (cw - dw) // 2
        span = range(mid, mid + dw)
        if nr == cr + 1:          # 向下
            wr = cr * step + cw + 1
            for k in span:
                grid[wr][cc * step + 1 + k] = TileType.EMPTY
        elif nr == cr - 1:        # 向上
            wr = nr * step + cw + 1
            for k in span:
                grid[wr][cc * step + 1 + k] = TileType.EMPTY
        elif nc == cc + 1:        # 向右
            wc = cc * step + cw + 1
            for k in span:
                grid[cr * step + 1 + k][wc] = TileType.EMPTY
        else:                     # 向左
            wc = nc * step + cw + 1
            for k in span:
                grid[cr * step + 1 + k][wc] = TileType.EMPTY

    # ③ 生成树（递归回溯/迭代栈）
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    visited = [[False] * n for _ in range(n)]
    visited[0][0] = True
    stack = [(0, 0)]
    tree = set()
    while stack:
        cr, cc = stack[-1]
        opts = [(dr, dc) for dr, dc in dirs
                if 0 <= cr + dr < n and 0 <= cc + dc < n
                and not visited[cr + dr][cc + dc]]
        if not opts:
            stack.pop()
            continue
        dr, dc = rng.choice(opts)
        nr, nc = cr + dr, cc + dc
        visited[nr][nc] = True
        tree.add(((cr, cc), (nr, nc)))
        open_door(cr, cc, nr, nc)
        stack.append((nr, nc))

    # ④ 额外打墙 → 环路（去死巷）
    for _ in range(loop_extra):
        cr, cc = rng.randrange(n), rng.randrange(n)
        dr, dc = rng.choice(dirs)
        nr, nc = cr + dr, cc + dc
        if not (0 <= nr < n and 0 <= nc < n):
            continue
        if ((cr, cc), (nr, nc)) in tree or ((nr, nc), (cr, cc)) in tree:
            continue
        open_door(cr, cc, nr, nc)

    # ⑤ 中央 LJR 保护区清为开阔广场
    r0, r1, c0, c1 = ljr_zone.protected_zone(origin)
    for r in range(max(1, r0), min(GRID_SIZE - 1, r1 + 1)):
        for c in range(max(1, c0), min(GRID_SIZE - 1, c1 + 1)):
            grid[r][c] = TileType.EMPTY

    # ⑤b 清空迷宫未覆盖的周边留白带，作为边缘通道
    lo = n * step + 1
    for r in range(lo, GRID_SIZE - 1):
        for c in range(1, GRID_SIZE - 1):
            grid[r][c] = TileType.EMPTY
    for c in range(lo, GRID_SIZE - 1):
        for r in range(1, GRID_SIZE - 1):
            grid[r][c] = TileType.EMPTY

    # ⑥ 少量墙格转 STEEL（机械/重物锚点，保持静谧工业感）
    walls = [(r, c) for r in range(1, GRID_SIZE - 1)
             for c in range(1, GRID_SIZE - 1) if grid[r][c] == TileType.BRICK]
    for r, c in rng.sample(walls, min(steel_count, len(walls))):
        grid[r][c] = TileType.STEEL


def coarse_color(cr, cc):
    """给粗格(迷宫块)分配区域配色（供迷宫视觉分层）。"""
    if cc >= 3:
        return "B_仓库迷宫"
    if cr <= 1:
        return "A_入口厂区"
    if cr >= 3:
        return "D_废墟出口"
    return "C_机械核心"

# ---------------------------------------------------------------
# 工业模块 × 损坏档（相对坐标列表，BRICK）
#   一个模块 = 一小簇“机器/台架/墙”，不同损坏档改变形状与密度，
#   让玩家感觉“同一个厂越来越破”而非“贴图复制”。
# ---------------------------------------------------------------
MODULE_VARIANTS = {
    # 正常生产线：完整的两机 + 排架
    "normal": [(0, 0), (0, 1), (1, 0), (2, 0), (2, 1)],
    # 轻微损坏：一台机倾倒（右上移，右下留空）
    "light": [(0, 0), (0, 1), (1, 0), (2, 1)],
    # 严重损坏：断墙 + 堆料（更密、更碎）
    "heavy": [(0, 0), (0, 1), (1, 1), (2, 0), (2, 1), (1, 2)],
    # 异常区：断电/高饱和（保留一台，再叠加一个 STEEL 锚）
    "abnormal": [(0, 0), (1, 0), (1, 1)],
}


def stamp_module(grid, r0, c0, variant="normal", *, anchor=None,
                 origin=LJR_ORIGIN):
    """在 (r0, c0) 起始处盖一个工业模块（BRICK）。

    Returns: 实际盖入的 (row, col) 列表。
    - 跳过落在 LJR 保护区内的格。
    - anchor: 可选 ("S"|"B", dr, dc)，在模块内额外盖一个钢/砖锚点。
    """
    cells = MODULE_VARIANTS.get(variant, MODULE_VARIANTS["normal"])
    placed = []
    for dr, dc in cells:
        r, c = r0 + dr, c0 + dc
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            continue
        if ljr_zone.is_ljr_protected(r, c, origin):
            continue
        grid[r][c] = TileType.BRICK
        placed.append((r, c))
    if anchor is not None and anchor[0] in ("S", "B"):
        kind, adr, adc = anchor
        r, c = r0 + adr, c0 + adc
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            if not ljr_zone.is_ljr_protected(r, c, origin):
                grid[r][c] = TileType.STEEL if kind == "S" else TileType.BRICK
                placed.append((r, c))
    return placed


def edge_pipe_decorations(grid, *, step=1):
    """沿四边内圈（col=1 / row=1 / col=A-1 / row=A-1 的空格）生成“边缘管网”装饰。
    Returns: list[(kind, row, col)]，kind 固定 "pipe"。纯观感。
    """
    dec = []
    A = GRID_SIZE - 1
    sample = []
    for r in range(1, A):
        sample.append((r, 1))
        sample.append((r, A - 1))
    for c in range(1, A):
        sample.append((1, c))
        sample.append((A - 1, c))
    for i, (r, c) in enumerate(sample):
        if i % step != 0:
            continue
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            if grid[r][c] == TileType.EMPTY:
                dec.append(("pipe", r, c))
    return dec


def core_decorations(grid, *, origin=LJR_ORIGIN, max_n=14):
    """在“机械核心”外围 EMPTY 格放红色警示灯，强化核心高危感。
    取保护区外扩 2 格的外围条带上的空地，周期性放置。
    Returns: list[(kind, row, col)]，kind == "wl"。
    """
    dec = []
    r0, r1, c0, c1 = ljr_zone.protected_zone(origin)
    cands = []
    for r in (r0 - 2, r0 - 1, r1 + 1, r1 + 2):
        if 0 <= r < GRID_SIZE:
            for c in range(max(0, c0 - 2), min(GRID_SIZE, c1 + 3)):
                if grid[r][c] == TileType.EMPTY:
                    cands.append((r, c))
    for c in (c0 - 2, c0 - 1, c1 + 1, c1 + 2):
        if 0 <= c < GRID_SIZE:
            for r in range(max(0, r0 - 1), min(GRID_SIZE, r1 + 2)):
                if grid[r][c] == TileType.EMPTY:
                    cands.append((r, c))
    seen = set()
    for r, c in cands:
        if (r, c) in seen:
            continue
        seen.add((r, c))
    for i, (r, c) in enumerate(sorted(seen)):
        if i % 3 == 0 and len(dec) < max_n:
            dec.append(("wl", r, c))
    return dec


def debris_decorations(grid, row_range, *, origin=LJR_ORIGIN):
    """在废墟出口区（row_range = (lo, hi)）的 EMPTY 格放化学泄漏/蒸汽。
    Returns: list[(kind, row, col)]。
    """
    dec = []
    r_lo, r_hi = row_range
    for r in range(r_lo, r_hi + 1):
        for c in range(1, GRID_SIZE - 1):
            if grid[r][c] != TileType.EMPTY:
                continue
            if ljr_zone.is_ljr_protected(r, c, origin):
                continue
            if (r + c) % 7 == 0:
                dec.append(("lk", r, c))
            if (r + c) % 11 == 0:
                dec.append(("st", r, c))
    return dec


# 工业区域配色（由 map_02 用于区域差异化 → 建立空间认知）
REGION_COLORS_INDUSTRIAL = {
    "A_入口厂区": (168, 150, 80),    # 暗黄（锈蚀钢架）
    "B_仓库迷宫": (110, 120, 80),    # 灰绿（仓储）
    "C_机械核心": (70, 90, 140),     # 冷蓝（+红警示为装饰）
    "D_废墟出口": (120, 100, 90),    # 破败棕灰（泄漏/坍塌）
}
WALL_COLOR_INDUSTRIAL = (100, 104, 108)   # 混凝土墙