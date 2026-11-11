# -*- coding: utf-8 -*-
"""
地图碰撞检测
提供"给定一个像素矩形区域，是否与地图上的障碍物（砖墙/钢墙）重叠"的
通用检测函数。当前只区分"可通行 / 不可通行"，不区分墙体类型——
后续如果引入子弹摧毁砖墙等机制，可以在这里扩展。
"""
import pygame
from core.settings import TILE_SIZE, GRID_SIZE
from maps.tile import TileType
from maps.game_map import GameMap

def rect_hits_obstacle(rect: pygame.Rect, game_map: GameMap) -> bool:
    """检测给定矩形是否与地图上任意一个障碍物重叠。

    ★ 2026-10-23：Stage 5「戈壁环岛」起支持**连续几何碰撞**。
      若 game_map.geometry 非 None（本关特有），直接对「圆 + 圆环」浮点几何
      做判定，不经格子 —— 圆就是圆，不再是放大 2 倍的方块团。
      老关卡没有 geometry，走下面的格子路径，行为零变化。
    """
    geometry = getattr(game_map, "geometry", None)
    if geometry is not None:
        return geometry.rect_hit(rect)

    # 矩形覆盖到的格子列/行范围（左闭右开），并裁剪到地图边界内
    col_start = max(0, rect.left // TILE_SIZE)
    col_end = min(GRID_SIZE - 1, (rect.right - 1) // TILE_SIZE)
    row_start = max(0, rect.top // TILE_SIZE)
    row_end = min(GRID_SIZE - 1, (rect.bottom - 1) // TILE_SIZE)

    for row in range(row_start, row_end + 1):
        for col in range(col_start, col_end + 1):
            if game_map.get_tile(row, col) != TileType.EMPTY:
                return True
    return False