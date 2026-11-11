# -*- coding: utf-8 -*-
"""
地图数据 - Stage 1「钢铁废墟」：中央争夺 + 左右包抄的主题化战略地图

关卡设计（非"障碍摆放"，而是设计语言）：
  - 中央控制核心：LJR 为不可破坏核心，外层"核心环"（带 4 个门）
    围出可争夺的控制区 -> 让玩家有"往中间打"的目标。
  - 四条主题区域（可一眼辨认）：
      D 山地前哨（左上·灰）：孤立巨石 + 前哨，开阔驻防
      B 丛林基地（右上·绿）：破碎不规则掩体 + 哨塔（留射击窗口）
      A 工业废墟（左下·橙）：铁路/机械长条 + 瓦砾残骸
      C 军事基地（右下·蓝）：规整厚重防御工事（带门、可进出）
  - 四角 STEEL 哨塔：视觉防御锚点，稀疏不连续。
  - 三条战略路线：
      左路 = 工业废墟：掩体多、节奏慢，适合偷袭；
      右路 = 军事基地：空间大、火力交战；
      中路 = 核心争夺：高风险。

硬约束：只 EMPTY/BRICK/STEEL；LJR 保护区 rows9-15 × cols4-21 内无任何非 LJR 障碍；
建筑均带开口（不死区）；栋与栋/环与墙之间留街道与逃生落点。

导出：
  build_map_data()    -> (grid, is_decorative)  25×25（碰撞数据，接口兼容）
  build_visual_data() -> 25×25 RGB|None（视觉配色，纯视觉层）
"""
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.ljr import place_ljr

LJR_START_ROW = 10
LJR_START_COL = 5

# 视觉配色（参照「建筑材质参考.png」的现代军事/混凝土色调）
REGION_COLORS = {
    "D_山地前哨": (152, 156, 160),   # 灰
    "B_丛林基地": (84, 112, 52),     # 橄榄军绿
    "A_工业废墟": (178, 116, 62),    # 锈橙
    "C_军事基地": (76, 82, 150),     # 钢蓝
}
CORE_COLOR = (210, 160, 70)      # 中央控制环：琥珀/能量
WALL_COLOR = (118, 121, 126)     # 基地围墙：混凝土灰

# 四角 STEEL 哨塔（稀疏，纯视觉+防御，避开出生/验证锚点）
CORNER_TOWERS = [(1, 3, "S"), (1, 20, "S"), (23, 3, "S"), (23, 20, "S")]

# 中央核心环（BRICK）带 4 门：顶门(12..13)、底门(12..13)、左门(12)、右门(12)
_RING_GATES = {(8, 12), (8, 13), (16, 12), (16, 13), (12, 3), (12, 22)}


def _core_ring_cells():
    cells = []
    for c in range(3, 23):
        if (8, c) not in _RING_GATES:
            cells.append((8, c))
        if (16, c) not in _RING_GATES:
            cells.append((16, c))
    for r in range(8, 17):
        if (r, 3) not in _RING_GATES:
            cells.append((r, 3))
        if (r, 22) not in _RING_GATES:
            cells.append((r, 22))
    return cells


# 四主题区域建筑群（BRICK=B / STEEL=S）
_REGIONS = {
    "D_山地前哨": [   # 孤立巨石 + 前哨
        (1, 4), (1, 5), (2, 6), (2, 7), (2, 8), (3, 6), (4, 6), (4, 8),   # 前哨
        (5, 2), (5, 3), (6, 3), (5, 7), (6, 7), (6, 8), (7, 8),           # 巨石
    ],
    "B_丛林基地": [   # 破碎不规则掩体 + 哨塔 + 射击窗口（互不围合；让开上辐条门道）
        (3, 15), (3, 16), (3, 17),
        (5, 15), (5, 16),
        (3, 20), (3, 21), (3, 22),
        (5, 19), (5, 20),
        (6, 21), (6, 22),
        (7, 15), (7, 16),
        (2, 22, "S"), (6, 19, "S"),
    ],
    "A_工业废墟": [   # 铁路/机械长条 + 瓦砾（互不围合）
        (19, 3),
        (20, 2), (20, 3), (20, 4), (20, 5),
        (22, 2), (22, 3),
        (17, 3), (17, 4), (17, 5),
        (18, 5), (18, 6),
        (18, 7),
        (19, 6), (19, 7),
    ],
    "C_军事基地": [   # 主堡+前哨+钢柱（带上下门，可进出；去掉封闭右翼，保持联通）
        (18, 8), (18, 9), (19, 9),                                           # 前哨掩体
        (17, 11), (17, 14), (17, 15), (17, 16),
        (17, 17), (17, 18), (17, 19), (17, 20),                             # 主堡顶（留 12..13 门）
        (18, 11), (18, 20), (19, 11), (19, 20),
        (20, 11), (20, 12), (20, 13), (20, 14), (20, 15),
        (20, 18), (20, 19), (20, 20),                                       # 底（留门 16..17）
        (22, 11), (22, 12), (22, 13), (23, 12),                             # 防御柱
        (21, 20, "S"),                                                       # 钢柱
    ],
}


def _tile(kind):
    return TileType.STEEL if kind == "S" else TileType.BRICK


def _place(cells, grid):
    for cell in cells:
        r, c = cell[0], cell[1]
        kind = cell[2] if len(cell) > 2 else "B"
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            grid[r][c] = _tile(kind)


def build_map_data():
    """构建 Stage 1「钢铁废墟」碰撞数据。

    Returns:
        (grid, is_decorative)：两张 25×25。is_decorative 仅标记 LJR 笔画。
    """
    grid = [
        [TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)
    ]
    is_decorative = [
        [False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)
    ]
    # 围墙
    for c in range(GRID_SIZE):
        grid[0][c] = TileType.BRICK
        grid[GRID_SIZE - 1][c] = TileType.BRICK
    for r in range(1, GRID_SIZE - 1):
        grid[r][0] = TileType.BRICK
        grid[r][GRID_SIZE - 1] = TileType.BRICK
    # LJR 核心
    place_ljr(grid, is_decorative,
              start_row=LJR_START_ROW, start_col=LJR_START_COL)
    # 中央核心环
    _place(_core_ring_cells(), grid)
    # 四角 STEEL 哨塔
    _place(CORNER_TOWERS, grid)
    # 四主题区域
    for cells in _REGIONS.values():
        _place(cells, grid)
    return grid, is_decorative


def build_visual_data():
    """构建视觉配色（纯视觉层，不改碰撞）。

    Returns:
        25×25 的 list[list[RGB|None]]；None = 沿用 Tile 默认色。
    """
    visual = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for c in range(GRID_SIZE):
        visual[0][c] = WALL_COLOR
        visual[GRID_SIZE - 1][c] = WALL_COLOR
    for r in range(1, GRID_SIZE - 1):
        visual[r][0] = WALL_COLOR
        visual[r][GRID_SIZE - 1] = WALL_COLOR
    for (r, c) in _core_ring_cells():
        visual[r][c] = CORE_COLOR
    for name, cells in _REGIONS.items():
        color = REGION_COLORS[name]
        for cell in cells:
            r, c = cell[0], cell[1]
            visual[r][c] = color
    # 四角哨塔保持默认 STEEL 色（None）
    return visual