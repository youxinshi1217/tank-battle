# -*- coding: utf-8 -*-
"""
地图数据 - Stage 2「工业迷宫」（未来钢铁废墟 / 活着的工厂）

设计（落实「单向深入四区 + 迷宫走廊 + 复用模块×损坏档 + 边缘管网」）：
  - 主体 = 确定性「迷宫」：宽 3 格走廊 + 环路 + 转角岔路，中央 LJR「机械核心」
    保护区被清为开阔广场（可通行枢纽）。
  - 四区：入口厂区（上·暗黄）/ 仓库迷宫（右上·灰绿）/ 机械核心（中·冷蓝）/ 废墟出口（下·破败）。
  - 四边内圈 = 边缘管网（pipe 装饰，纯观感）；核心外围红警示灯；出口泄漏/蒸汽。
  - 全程通道 >=3；无死区、全连通；LJR 结构不变（保护层逻辑可复用）。

确定性：build_labyrinth 使用固定 seed → 同图产出恒定，可回归验证（非随机题图）。

导出：
  build_map_data()       -> (grid, is_decorative)        25×25 碰撞数据
  build_visual_data()    -> 25×25 RGB|None 区域配色（纯视觉）
  build_decorations()    -> list[(kind, row, col)] 装饰覆盖层（纯观感）
"""
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.ljr import place_ljr
from maps import ljr_zone as _lz
from maps.map_themes import (
    build_labyrinth, coarse_color, edge_pipe_decorations,
    core_decorations, debris_decorations,
    REGION_COLORS_INDUSTRIAL, WALL_COLOR_INDUSTRIAL, LJR_ORIGIN,
)

LJR_START_ROW, LJR_START_COL = LJR_ORIGIN

# 玩家出生区（main 随机出生；此处留作回归参考点）
PLAYER_SPAWN = (2, 2)

# 迷宫已密，边带较窄；不再额外放机台（保持走廊 2 宽），机台语汇交给装饰层。
MACHINES = []


def build_map_data():
    """构建 Stage 2「工业迷宫」碰撞数据。
    Returns: (grid, is_decorative) 25×25。
    """
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    is_decorative = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    # 外墙
    for c in range(GRID_SIZE):
        grid[0][c] = grid[GRID_SIZE - 1][c] = TileType.BRICK
    for r in range(1, GRID_SIZE - 1):
        grid[r][0] = grid[r][GRID_SIZE - 1] = TileType.BRICK
    # 迷宫主体（确定性，窄巷：2×2 转身室 + 1 宽窄门）
    build_labyrinth(grid, origin=LJR_ORIGIN, dw=1, loop_extra=4, steel_count=26)
    # LJR 机械核心
    place_ljr(grid, is_decorative,
              start_row=LJR_START_ROW, start_col=LJR_START_COL)
    # 工业机台点缀（避开保护区内格）
    for (r, c) in MACHINES:
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            continue
        if _lz.is_ljr_protected(r, c, LJR_ORIGIN):
            continue
        if grid[r][c] == TileType.EMPTY:
            grid[r][c] = TileType.BRICK
    # 出生点保证空地
    pr, pc = PLAYER_SPAWN
    if 0 <= pr < GRID_SIZE and 0 <= pc < GRID_SIZE:
        grid[pr][pc] = TileType.EMPTY
        is_decorative[pr][pc] = False
    return grid, is_decorative


def build_visual_data():
    """区域配色（纯视觉，不改碰撞）；按迷宫块位置分层，LJR 保持默认焦点。"""
    visual = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for c in range(GRID_SIZE):
        visual[0][c] = WALL_COLOR_INDUSTRIAL
        visual[GRID_SIZE - 1][c] = WALL_COLOR_INDUSTRIAL
    for r in range(1, GRID_SIZE - 1):
        visual[r][0] = WALL_COLOR_INDUSTRIAL
        visual[r][GRID_SIZE - 1] = WALL_COLOR_INDUSTRIAL
    grid, _ = build_map_data()
    for r in range(1, GRID_SIZE - 1):
        for c in range(1, GRID_SIZE - 1):
            if visual[r][c] is not None:
                continue
            if grid[r][c] not in (TileType.BRICK, TileType.STEEL):
                continue
            cr, cc = min((r - 1) // 4, 4), min((c - 1) // 4, 4)
            key = coarse_color(cr, cc)
            visual[r][c] = REGION_COLORS_INDUSTRIAL.get(key)
    # 机台与 LJR 保持默认色（None）
    return visual


def build_decorations():
    """装饰覆盖层（纯观感）：边缘管网 + 核心警示灯 + 废墟泄漏/蒸汽。"""
    grid, _ = build_map_data()
    deco = edge_pipe_decorations(grid, step=2)
    deco += core_decorations(grid)
    deco += debris_decorations(grid, (16, 23))
    return deco