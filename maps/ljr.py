# -*- coding: utf-8 -*-
"""
LJR 拼字统一生成辅助（Phase 8.1）

所有地图共享此函数放置 LJR 原创元素，避免每张地图重新手写 / 出现不同版本的字形。

冻结规则：
  - 必须引用 maps/letters.py 的 LJR_SEQUENCE / LETTER_WIDTH / LETTER_HEIGHT / LETTER_GAP。
  - 不改字形、不新增字形（LJR 为原创元素，禁止改动 / 禁止重新设计 / 禁止删除）。
  - 仅允许调整放置位置（start_row / start_col）、替代 tile 顺序、以及放大单元数 block_size。

设计说明（为什么"约70%/~60%"不采用像素级缩小）：
  letters 字模是固定的 5 行高小点阵。对它做真实子分辨率缩小会破坏字形
  （例如 J 的中坚、R 的闭合环都会在降采样中消失），从而违反"不改字形"的强制要求。
  因此本阶段的"约100%/~70%/~60%"通过布局上 LJR 所占地图区域的相对占比来体现，
  而非直接对字模做像素级缩放。block_size>=1 仅用于放大展示，不用于缩小。
"""
from core.settings import GRID_SIZE
from maps.tile import TileType
from maps.letters import LJR_SEQUENCE, LETTER_WIDTH, LETTER_HEIGHT, LETTER_GAP

DEFAULT_TILE_TYPES = (TileType.BRICK, TileType.STEEL, TileType.BRICK)


def _stamp_letter(grid, is_decorative, pattern, start_row, start_col,
                  tile_type, block_size):
    """把单个字母点阵盖到 grid 上，并标记为装饰图案格子。"""
    for r, row_str in enumerate(pattern):
        for c, ch in enumerate(row_str):
            if ch != "1":
                continue
            for dr in range(block_size):
                for dc in range(block_size):
                    grid_row = start_row + r * block_size + dr
                    grid_col = start_col + c * block_size + dc
                    if 0 <= grid_row < GRID_SIZE and 0 <= grid_col < GRID_SIZE:
                        grid[grid_row][grid_col] = tile_type
                        is_decorative[grid_row][grid_col] = True


def place_ljr(grid, is_decorative, *, start_row, start_col,
              block_size=1, tile_types=DEFAULT_TILE_TYPES):
    """在 (start_row, start_col) 处放置 LJR 原创元素。

    Args:
        block_size: 每个字模点阵单元占用的网格数（>=1，仅用于放大；1 即标准字模大小）。
        tile_types: 三个字母依次使用的障碍类型，可用少于/多于 3 项，按序循环。
    """
    letter_tile_types = list(tile_types)
    cursor_col = start_col
    for idx, letter_pattern in enumerate(LJR_SEQUENCE):
        tile_type = letter_tile_types[idx % len(letter_tile_types)]
        _stamp_letter(grid, is_decorative, letter_pattern,
                      start_row, cursor_col, tile_type, block_size)
        cursor_col += (LETTER_WIDTH + LETTER_GAP) * block_size