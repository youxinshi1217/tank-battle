# -*- coding: utf-8 -*-
"""
地图数据 - Stage 3「军事攻坚 · 多枢纽区」

设计语言（v5 终稿，与规划脚本 _design_stage3 同构）：
  - 中央指挥广场 = LJR 核心纪念碑 + 保护区本体（r9-15 × c4-22），由"营墙围环"
    围合成可争夺的要塞核心，留四门：北门/南门对主通道，西门/东门对侧道。
  - 四角前沿据点（4×4 STEEL 碉堡，门望中央 90° 旋转对称）+ 四角哨塔。
  - 四象限场景化工事（伪对称）：
      西北·高地堑壕 / 东北·装甲车场 / 西南·军火库房 / 东南·防空炮位。
  - 主通道中段"双柱门廊"，强化纵深与对射支点。

硬约束：只 EMPTY/BRICK/STEEL；LJR 笔画不改变；保护区零异物；无死区全连通。

导出：
  build_map_data()       -> (grid, is_decorative)  25×25 碰撞数据
  build_visual_data()    -> 25×25 RGB|None 区域配色（纯视觉）
  build_decorations()    -> list[(kind, row, col)] 装饰覆盖（纯观感，落 EMPTY）
"""
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.ljr import place_ljr
from maps import ljr_zone

# LJR 放置原点（沿用全系统默认，保护区 = 中央指挥广场本体）
LJR_ORIGIN = (10, 5)
PLAYER_SPAWN = (2, 2)

EMPTY, BRICK, STEEL = TileType.EMPTY, TileType.BRICK, TileType.STEEL

# ---------------- 视觉配色 ----------------
RING_COLOR = (118, 121, 126)        # 营墙围环：混凝土灰
REGION_COLORS = {
    "NW_高地": (84, 112, 52),       # 军绿
    "NE_装甲": (76, 82, 150),       # 钢蓝
    "SW_军火": (168, 150, 80),      # 暗黄（弹药箱）
    "SE_防空": (70, 108, 120),      # 冷青（雷达）
}
WALL_COLOR = (100, 104, 108)        # 外墙混凝土

# 据点 4×4 区域（视觉上色用，避免重复维护 hull 内部坐标）
HULL_BOXES = {
    "NW_高地": ((3, 6), (3, 6)),
    "NE_装甲": ((3, 6), (15, 18)),
    "SW_军火": ((18, 21), (3, 6)),
    "SE_防空": ((18, 21), (15, 18)),
}

# 四角哨塔
CORNER_TOWERS = [(1, 2), (1, 22), (23, 2), (23, 22)]

# 营墙围环（BRICK）：r8/r16 上边与下边（门洞 c10-14 留空），c3/c23 侧边（门洞 r11-13 留空）
def _ring_cells():
    cells = []
    for c in range(4, 10):
        cells += [(8, c), (16, c)]
    for c in range(15, 22):
        cells += [(8, c), (16, c)]
    cells += [(9, 3), (10, 3), (14, 3), (15, 3)]
    cells += [(9, 23), (10, 23), (14, 23), (15, 23)]
    return cells

# 主通道中段双柱门廊（STEEL）
GATE_COLUMNS = [(4, 10), (5, 10), (4, 14), (5, 14),
                (19, 10), (20, 10), (19, 14), (20, 14)]

# 四象限场景构件（各象限一组：BRICK 造型 + STEEL 锚）
QUADRANT = {
    "NW_高地": {
        BRICK: [(2, 3), (2, 4), (2, 5), (7, 4)],
        STEEL: [],
    },
    "NE_装甲": {
        BRICK: [(2, 15), (2, 16), (2, 17), (4, 20), (5, 20), (7, 16)],
        STEEL: [(7, 20)],
    },
    "SW_军火": {
        BRICK: [(22, 3), (22, 4), (22, 5), (22, 6), (17, 7), (17, 8)],
        STEEL: [(21, 6)],
    },
    "SE_防空": {
        BRICK: [(22, 19), (22, 20), (17, 17)],
        STEEL: [(21, 20)],
    },
}


def _put(grid, cells, kind, *, origin=LJR_ORIGIN):
    """放障碍；落在 LJR 保护区内则跳过（保护区只允许 LJR 笔画）。"""
    for r, c in cells:
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            continue
        if ljr_zone.is_ljr_protected(r, c, origin):
            continue
        grid[r][c] = kind


def _hull(grid, r, c, *, door="S", origin=LJR_ORIGIN):
    """4×4 前沿据点：STEEL 壳 + 内部 1 个 STEEL 掩体 + 单面 2 宽门。

    door: 开口所在边。门望中央：西北=东、东北=南、西南=北、东南=西。
    """
    shell = [(r, c), (r, c + 1), (r, c + 2), (r, c + 3),
             (r + 1, c), (r + 1, c + 3),
             (r + 2, c), (r + 2, c + 3),
             (r + 3, c), (r + 3, c + 3)]
    if door == "S":
        door_cells, walk, pillar = [(r + 3, c + 1), (r + 3, c + 2)], \
            [(r + 1, c + 1), (r + 2, c + 1), (r + 2, c + 2)], (r + 1, c + 2)
    elif door == "N":
        door_cells, walk, pillar = [(r, c + 1), (r, c + 2)], \
            [(r + 1, c + 1), (r + 2, c + 1), (r + 2, c + 2)], (r + 1, c + 2)
    elif door == "W":
        door_cells, walk, pillar = [(r + 1, c), (r + 2, c)], \
            [(r + 1, c + 1), (r + 2, c + 1), (r + 1, c + 2)], (r + 2, c + 2)
    else:  # E
        door_cells, walk, pillar = [(r + 1, c + 3), (r + 2, c + 3)], \
            [(r + 1, c + 1), (r + 2, c + 1), (r + 1, c + 2)], (r + 2, c + 2)
    _put(grid, shell, STEEL, origin=origin)
    for ir, ic in door_cells + walk:
        if 0 <= ir < GRID_SIZE and 0 <= ic < GRID_SIZE:
            grid[ir][ic] = EMPTY
    _put(grid, [pillar], STEEL, origin=origin)


def build_map_data():
    """构建 Stage 3「军事攻坚 · 多枢纽区」碰撞数据。返回 (grid, is_decorative)。"""
    grid = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    is_deco = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    # 外墙
    for c in range(GRID_SIZE):
        grid[0][c] = grid[GRID_SIZE - 1][c] = BRICK
    for r in range(1, GRID_SIZE - 1):
        grid[r][0] = grid[r][GRID_SIZE - 1] = BRICK
    # 中央指挥广场（保护区先清空 → 放 LJR 核心纪念碑）
    r0, r1, c0, c1 = ljr_zone.protected_zone(LJR_ORIGIN)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            grid[r][c] = EMPTY
    place_ljr(grid, is_deco, start_row=LJR_ORIGIN[0], start_col=LJR_ORIGIN[1])
    # 四角前沿据点（门望中央）
    _hull(grid, 3, 3, door="E")
    _hull(grid, 3, 15, door="S")
    _hull(grid, 18, 3, door="N")
    _hull(grid, 18, 15, door="W")
    # 四角哨塔 + 营墙围环 + 门廊双柱
    _put(grid, CORNER_TOWERS, STEEL)
    _put(grid, _ring_cells(), BRICK)
    _put(grid, GATE_COLUMNS, STEEL)
    # 四象限场景构件
    for cells_map in QUADRANT.values():
        _put(grid, cells_map[BRICK], BRICK)
        _put(grid, cells_map[STEEL], STEEL)
    # 出生点保障空地
    grid[PLAYER_SPAWN[0]][PLAYER_SPAWN[1]] = EMPTY
    is_deco[PLAYER_SPAWN[0]][PLAYER_SPAWN[1]] = False
    return grid, is_deco


def build_visual_data():
    """区域配色（纯视觉，不改碰撞）：环墙统一混凝土灰，象限/据点按身份上色。"""
    grid, _ = build_map_data()
    visual = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    # 外墙
    for c in range(GRID_SIZE):
        visual[0][c] = visual[GRID_SIZE - 1][c] = WALL_COLOR
    for r in range(1, GRID_SIZE - 1):
        visual[r][0] = visual[r][GRID_SIZE - 1] = WALL_COLOR
    # 营墙围环
    for (r, c) in _ring_cells():
        visual[r][c] = RING_COLOR
    # 四角据点 + 象限构件
    for name, ((r_lo, r_hi), (c_lo, c_hi)) in HULL_BOXES.items():
        color = REGION_COLORS[name]
        for r in range(r_lo, r_hi + 1):
            for c in range(c_lo, c_hi + 1):
                if grid[r][c] in (BRICK, STEEL):
                    visual[r][c] = color
    for name, cells_map in QUADRANT.items():
        color = REGION_COLORS[name]
        for kind in (BRICK, STEEL):
            for (r, c) in cells_map[kind]:
                if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                    visual[r][c] = color
    # 四角哨塔、门廊柱、LJR 笔画保持默认色（None）
    return visual


def build_decorations():
    """装饰覆盖层（纯观感，绝不落障碍/笔画）：四门警戒灯 + 通道氛围灯 + 路边警戒横杆。"""
    grid, _ = build_map_data()
    deco = []
    cands = [
        ("wl", 8, 12), ("wl", 16, 12),   # 北/南门洞警戒灯
        ("wl", 12, 3), ("wl", 12, 23),   # 西/东门洞警戒灯
        ("wl", 9, 20), ("wl", 15, 20),   # 广场东侧角氛围灯
        ("wl", 9, 5), ("wl", 15, 5),     # 广场西侧角氛围灯
        ("wl", 3, 10), ("wl", 20, 14),   # 主通道中段门廊点灯
        ("pipe", 1, 7), ("pipe", 1, 18),  # 北外墙内侧警戒横杆
        ("pipe", 23, 7), ("pipe", 23, 18),  # 南外墙内侧警戒横杆
    ]
    for kind, r, c in cands:
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and grid[r][c] == EMPTY:
            deco.append((kind, r, c))
    return deco