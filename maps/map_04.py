# -*- coding: utf-8 -*-
"""
地图数据 - Stage 4「决战要塞」（高密度 + STEEL 核心，高强度正面硬刚）

关卡设计（设计语言：攻城死斗 / 正面对轰）：
  - 中央 STEEL 钢铁要塞环：四向 3 宽大门直通核心大厅，LJR 指挥核心（全 BRICK 暖色）
    被冷钢壳合围 → 「可争夺的控制核心区域」。
  - 四条主攻大道：北/南 3 宽正面大道 + 西/东侧翼出击走廊，全部直通核心，四区联通无孤岛。
  - 四角野战工事（高密度 BRICK + STEEL 锚点）：统一"错位锯齿"布局，相邻行不同列、
    无对齐缝；南半区 row 23 全空作贴墙通道，不制造贴墙死角。
  - 要塞内卫掩体（row 8/16 各 6 格，BRICK 暖铜橙）：填实 LJR 正上/下方的空旷带，
    墙边留 ≥2 宽空隙、不夹死角；row 9/15 保持全空作 1~2 宽环形通行走廊。
  - 广场火力走廊（BRICK 沙漠砂）：北广场中场火力点 + 南广场大道双侧火力点，
    正面大道两侧对轰互射，进一步压实密度至约 37.6%（235/625 格）。

硬约束：只 EMPTY/BRICK/STEEL；LJR 保护区 rows9-15 × cols4-21 内无任何外来障碍；
要塞环与 LJR 笔画不重叠；大道≥3 宽、无封闭死区、全连通。

导出：
  build_map_data()    -> (grid, is_decorative)  25×25（碰撞数据，接口兼容）
  build_visual_data() -> 25×25 RGB|None（区域配色，纯视觉层）
  build_decorations() -> list[(kind, row, col)] 装饰覆盖层（纯观感）
"""
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.ljr import place_ljr
from maps.map_themes import edge_pipe_decorations

LJR_START_ROW = 10
LJR_START_COL = 5

# 玩家出生点（随机出生候选之一，main 随机；此处留作回归参考点）
PLAYER_SPAWN = (2, 2)

# ---------------------------------------------------------------
# 中央钢铁要塞环（STEEL）
#   顶/底墙：row 7 / row 17，cols 4-22；南北门 cols 11-13
#   左/右墙：col 3 / col 22，rows 8-16；东西门 rows 11-13
# ---------------------------------------------------------------
_FORTRESS_TOP = 7
_FORTRESS_BOTTOM = 17
_FORTRESS_LEFT = 3
_FORTRESS_RIGHT = 22
_NORTH_GATE_COLS = (11, 12, 13)
_SOUTH_GATE_COLS = (11, 12, 13)
_WEST_GATE_ROWS = (11, 12, 13)
_EAST_GATE_ROWS = (11, 12, 13)

# ---------------------------------------------------------------
# 四角野战工事（错位锯齿；B=BRICK，带 "S" 尾格 = STEEL 锚点）
# ---------------------------------------------------------------
_REGIONS = {
    "NW_突击工事": [
        (1, 5), (1, 6), (3, 5), (3, 6), (4, 7),
        (5, 2), (5, 3), (6, 5), (6, 6), (6, 7),
    ],
    "NE_火力阵地": [
        (1, 18), (1, 19), (3, 20), (3, 21, "S"), (3, 22),
        (4, 22), (5, 18), (5, 19),
    ],
    "SW_残骸防御区": [
        (18, 4), (18, 5), (19, 3), (19, 4), (20, 6), (20, 7),
        (21, 5), (21, 6), (22, 3), (22, 4),
    ],
    "SE_弹药仓库": [
        (18, 17), (18, 18), (19, 21), (19, 22),
        (20, 18), (20, 19, "S"), (20, 20),
        (22, 18), (22, 19),
    ],
}

# ---------------------------------------------------------------
# 要塞内卫掩体（BRICK，保护区外 row 8 / row 16）
#   顶/底带各 6 格：内卫哨位 (6,7) + 门侧单点 (10)(14) + 内卫哨位 (18,19)
#   墙边留 ≥2 宽空隙、不夹死角；row 9/15 保持全空作环形通行走廊
# ---------------------------------------------------------------
_INNER_GUARD = [
    (8, 6), (8, 7), (8, 10), (8, 14), (8, 18), (8, 19),
    (16, 6), (16, 7), (16, 10), (16, 14), (16, 18), (16, 19),
]

# ---------------------------------------------------------------
# 广场火力走廊（BRICK）：北广场中场火力点 + 南广场大道双侧火力点
# ---------------------------------------------------------------
_PLAZA_COVER = [
    (2, 8), (2, 9), (2, 14), (2, 15),       # 北广场中场
    (4, 16), (4, 17),                       # 北广场 NE 侧
    (19, 9), (19, 10), (19, 14), (19, 15),  # 南广场大道西/东侧
    (21, 9), (21, 10), (21, 14), (21, 15),  # 南广场大道西/东侧
]

# 要塞环外围警示灯装饰位（均须落在 EMPTY、保护区外）
_WARNING_LIGHTS = [
    (5, 12), (6, 12),          # 北门进场
    (18, 12), (19, 12),        # 南门进场
    (12, 1), (12, 2),          # 西门侧廊
    (12, 23),                  # 东门侧廊
    (4, 2), (4, 23),           # 上侧两角
    (22, 6), (22, 21),         # 下侧两角
]

# ---------------------------------------------------------------
# 区域配色（纯视觉）
# ---------------------------------------------------------------
REGION_COLORS = {
    "NW_突击工事": (140, 116, 74),     # 橄榄褐
    "NE_火力阵地": (150, 84, 66),      # 铁锈红
    "SW_残骸防御区": (108, 112, 118),  # 炭灰钢
    "SE_弹药仓库": (96, 122, 84),      # 军绿
}
CORE_COLOR = (96, 110, 130)            # 要塞环：冷钢蓝灰
WALL_COLOR = (118, 121, 126)           # 外墙：混凝土灰
INNER_GUARD_COLOR = (172, 128, 72)     # 要塞内卫：暖铜橙（区别于冷钢环）
PLAZA_COLOR = (152, 128, 90)           # 广场火力点：沙漠砂


def _tile(kind):
    return TileType.STEEL if kind == "S" else TileType.BRICK


def _place(cells, grid):
    for cell in cells:
        r, c = cell[0], cell[1]
        kind = cell[2] if len(cell) > 2 else "B"
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            grid[r][c] = _tile(kind)


def build_map_data():
    """构建 Stage 4「决战要塞」碰撞数据。

    Returns:
        (grid, is_decorative)：两张 25×25。is_decorative 仅标记 LJR 笔画。
    """
    grid = [
        [TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)
    ]
    is_decorative = [
        [False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)
    ]
    # 外墙
    for c in range(GRID_SIZE):
        grid[0][c] = TileType.BRICK
        grid[GRID_SIZE - 1][c] = TileType.BRICK
    for r in range(1, GRID_SIZE - 1):
        grid[r][0] = TileType.BRICK
        grid[r][GRID_SIZE - 1] = TileType.BRICK
    # LJR 指挥核心（全 BRICK 暖色，突显于冷钢要塞环内；字形零改动）
    place_ljr(grid, is_decorative,
              start_row=LJR_START_ROW, start_col=LJR_START_COL,
              tile_types=(TileType.BRICK,))
    # 中央钢铁要塞环（STEEL）+ 四门
    for c in range(_FORTRESS_LEFT + 1, _FORTRESS_RIGHT + 1):
        if c not in _NORTH_GATE_COLS:
            grid[_FORTRESS_TOP][c] = TileType.STEEL
        if c not in _SOUTH_GATE_COLS:
            grid[_FORTRESS_BOTTOM][c] = TileType.STEEL
    for r in range(_FORTRESS_TOP + 1, _FORTRESS_BOTTOM):
        if r not in _WEST_GATE_ROWS:
            grid[r][_FORTRESS_LEFT] = TileType.STEEL
        if r not in _EAST_GATE_ROWS:
            grid[r][_FORTRESS_RIGHT] = TileType.STEEL
    # 四角野战工事（错位锯齿，BRICK + STEEL 锚点）
    for cells in _REGIONS.values():
        _place(cells, grid)
    # 要塞内卫 + 广场火力走廊（BRICK，保护区外；墙边留 ≥2 宽，无死角）
    _place(_INNER_GUARD, grid)
    _place(_PLAZA_COVER, grid)
    # 出生点强制空地（防御性，保证可通）
    pr, pc = PLAYER_SPAWN
    if 0 <= pr < GRID_SIZE and 0 <= pc < GRID_SIZE:
        grid[pr][pc] = TileType.EMPTY
        is_decorative[pr][pc] = False
    return grid, is_decorative


def build_visual_data():
    """区域配色（纯视觉，不改碰撞）；LJR 保持默认聚焦（None）。"""
    visual = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for c in range(GRID_SIZE):
        visual[0][c] = WALL_COLOR
        visual[GRID_SIZE - 1][c] = WALL_COLOR
    for r in range(1, GRID_SIZE - 1):
        visual[r][0] = WALL_COLOR
        visual[r][GRID_SIZE - 1] = WALL_COLOR
    # 要塞环
    for c in range(_FORTRESS_LEFT + 1, _FORTRESS_RIGHT + 1):
        if c not in _NORTH_GATE_COLS:
            visual[_FORTRESS_TOP][c] = CORE_COLOR
        if c not in _SOUTH_GATE_COLS:
            visual[_FORTRESS_BOTTOM][c] = CORE_COLOR
    for r in range(_FORTRESS_TOP + 1, _FORTRESS_BOTTOM):
        if r not in _WEST_GATE_ROWS:
            visual[r][_FORTRESS_LEFT] = CORE_COLOR
        if r not in _EAST_GATE_ROWS:
            visual[r][_FORTRESS_RIGHT] = CORE_COLOR
    # 四角掩体
    for name, cells in _REGIONS.items():
        color = REGION_COLORS[name]
        for cell in cells:
            r, c = cell[0], cell[1]
            visual[r][c] = color
    # 要塞内卫 / 广场火力点
    for r, c in _INNER_GUARD:
        visual[r][c] = INNER_GUARD_COLOR
    for r, c in _PLAZA_COVER:
        visual[r][c] = PLAZA_COLOR
    return visual


def build_decorations():
    """装饰覆盖层（纯观感）：外墙管网 + 要塞外围警示灯。"""
    grid, _ = build_map_data()
    deco = edge_pipe_decorations(grid, step=2)
    for r, c in _WARNING_LIGHTS:
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            if grid[r][c] == TileType.EMPTY:
                deco.append(("wl", r, c))
    return deco
