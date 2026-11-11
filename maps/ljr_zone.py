# -*- coding: utf-8 -*-
"""
Phase 8.3 - LJR Protected Zone 公共规则

职责：
  提供 LJR 原创图标的几何公共规则，供 Enemy/Item/Player 出生限制共用单一数据源。

区隔三概念（勿混淆）：
  - Tile 障碍      : 碰撞层（LJR 笔画、掩体、外墙，不可通行）
  - LJR Protected Zone : 生成限制层（禁 spawn / item / player），但仍可通行（R 空腔可走）
  - 道路区域       : 移动层（保护区内其余空格 + 外部战斗区）

本模块不复制硬编码坐标：LJR 包围盒由 maps/letters.py 的点阵尺寸 + 放置原点计算，
Protected Zone = LJR bbox ± 1 圈。将来某 Stage 的 LJR 位置不同，只改 origin，不动系统。
"""
from maps.letters import LJR_SEQUENCE, LETTER_WIDTH, LETTER_HEIGHT, LETTER_GAP

# Stage 1：LJR 放置原点（row, col）
DEFAULT_ORIGIN = (10, 5)


def _ljr_span():
    """计算 LJR 整体宽度（含 6 宽字母 J/R 的溢出）与高度，均取自 letters.py。"""
    width = 0
    cursor = 0
    for pattern in LJR_SEQUENCE:
        bounds = len(pattern[0])          # 该字母实际点阵宽度
        width = max(width, cursor + bounds)
        cursor += LETTER_WIDTH + LETTER_GAP
    return width, LETTER_HEIGHT


def ljr_bbox(origin=DEFAULT_ORIGIN):
    """LJR 包围盒（含边界，inclusive）(r0, r1, c0, c1)。"""
    o_r, o_c = origin
    w, h = _ljr_span()
    return o_r, o_r + h - 1, o_c, o_c + w - 1


def protected_zone(origin=DEFAULT_ORIGIN):
    """LJR Protected Zone = bbox ± 1 圈（含边界，inclusive）。(r0, r1, c0, c1)"""
    r0, r1, c0, c1 = ljr_bbox(origin)
    return r0 - 1, r1 + 1, c0 - 1, c1 + 1


def in_ljr_bbox(r, c, origin=DEFAULT_ORIGIN):
    r0, r1, c0, c1 = ljr_bbox(origin)
    return r0 <= r <= r1 and c0 <= c <= c1


def is_ljr_protected(r, c, origin=DEFAULT_ORIGIN):
    """是否处于 LJR Protected Zone（生成限制层）。"""
    r0, r1, c0, c1 = protected_zone(origin)
    return r0 <= r <= r1 and c0 <= c <= c1