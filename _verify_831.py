# -*- coding: utf-8 -*-
"""Phase 8.3-F 验证：Stage 1 Showcase（未来战争废墟竞技场）。

覆盖：LJR 完整性 / 四区域结构 / 障碍合法 / 无死区连通 / 随机出生安全 /
Enemy·Item 不入侵保护区 / 开放区域比例合理。

运行：python _verify_831.py（headless，SDL dummy），全部断言通过打印 ALL PASS。
"""
import os
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from core.settings import GRID_SIZE, ENEMY_SPAWN_SAFE_DISTANCE
from maps.map_01 import build_map_data
from maps import ljr_zone
from core import spawn_rules
from maps.tile import TileType

A = GRID_SIZE - 1  # 24

# 四区域判定矩形（含边界）
REGIONS = {
    "A_废墟": (9, 23, 1, 4),
    "B_狙击": (1, 8, 9, 23),
    "C_堡垒": (16, 23, 8, 23),
    "D_机动": (1, 8, 1, 10),
}


def flood_open(grid, src):
    reach = {src}
    dq = deque([src])
    while dq:
        r, c = dq.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                if grid[nr][nc] == TileType.EMPTY and (nr, nc) not in reach:
                    reach.add((nr, nc))
                    dq.append((nr, nc))
    return reach


def main():
    grid, deco = build_map_data()
    assert len(grid) == GRID_SIZE and len(deco) == GRID_SIZE, "应 25×25"

    # ---- 1. LJR 完整性 ----
    bbox = ljr_zone.ljr_bbox((10, 5))
    r0, r1, c0, c1 = bbox
    assert grid[10][6] == TileType.BRICK, "L 命中"
    assert grid[10][11] == TileType.STEEL, "J 命中"
    assert grid[10][16] == TileType.BRICK, "R 命中"
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if deco[r][c]:
                assert r0 <= r <= r1 and c0 <= c <= c1, f"deco({r},{c}) 超出 LJR bbox"
                assert grid[r][c] in (TileType.BRICK, TileType.STEEL), f"deco({r},{c}) 应笔画"
    print("[PASS] LJR：三锚点完整，is_decorative 仅标笔画，未损坏")

    # ---- 2. 四区域结构：每区域至少有一个非 LJR 障碍 ----
    for name, (rr0, rr1, cc0, cc1) in REGIONS.items():
        found = any(
            deco[r][c] == False and grid[r][c] in (TileType.BRICK, TileType.STEEL)
            for r in range(rr0, rr1 + 1)
            for c in range(cc0, cc1 + 1)
        )
        assert found, f"区域 {name} 缺少障碍"
    print("[PASS] 四区域（废墟/狙击/堡垒/机动）均有独立障碍结构")

    # ---- 3. 障碍合法 + 保护区洁净 ----
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            t = grid[r][c]
            assert t in (TileType.EMPTY, TileType.BRICK, TileType.STEEL), f"非法 Tile({r},{c})"
            if t == TileType.EMPTY:
                continue
            if r == 0 or r == A or c == 0 or c == A:
                assert t == TileType.BRICK, f"外墙({r},{c}) 应为 BRICK"
            elif not deco[r][c]:
                assert not ljr_zone.is_ljr_protected(r, c), f"障碍({r},{c}) 入侵保护区"
    print("[PASS] 障碍合法，保护区洁净（仅 LJR/EMPTY）")

    # ---- 4. 无封闭死区：所有非保护开放格彼此连通 ----
    # 参考点取出生合法候选 (2,2)
    assert grid[2][2] == TileType.EMPTY and not ljr_zone.is_ljr_protected(2, 2), "(2,2) 应为开放参考点"
    reach = flood_open(grid, (2, 2))
    dead = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == TileType.EMPTY and not ljr_zone.is_ljr_protected(r, c):
                if (r, c) not in reach:
                    dead.append((r, c))
    assert not dead, f"存在封闭死区：{dead[:10]}"
    print("[PASS] 无封闭死区：所有非保护开放格可互通")

    # ---- 5. 随机出生候选 ----
    need_move = 5
    spawn_cands = []
    for r in range(1, A):
        for c in range(1, A):
            if grid[r][c] != TileType.EMPTY:
                continue
            if ljr_zone.is_ljr_protected(r, c):
                continue
            open_n = sum(
                1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if 0 <= r + dr < GRID_SIZE and 0 <= c + dc < GRID_SIZE
                and grid[r + dr][c + dc] == TileType.EMPTY
            )
            if open_n >= need_move:
                spawn_cands.append((r, c))
    assert len(spawn_cands) >= 20, f"随机出生候选过少：{len(spawn_cands)}"
    # (3,3) 仍为合法候选（兼容回归）
    assert (3, 3) in spawn_cands or (
        grid[3][3] == TileType.EMPTY and not ljr_zone.is_ljr_protected(3, 3)
    ), "(3,3) 应保留为合法出生候选"
    print(f"[PASS] 随机出生候选 {len(spawn_cands)}：均合法 EMPTY/非保护区/有移动空间")

    # ---- 6. Enemy / Item 候选（过滤保护区 + 距离）----
    e_cands = 0
    i_cands = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != TileType.EMPTY:
                continue
            if ljr_zone.is_ljr_protected(r, c):
                continue
            i_cands += 1
            if abs(r - 3) + abs(c - 3) >= ENEMY_SPAWN_SAFE_DISTANCE:
                e_cands += 1
    assert e_cands >= 20, f"敌人候选过少：{e_cands}"
    assert i_cands > 0, "道具候选为空"
    print(f"[PASS] Enemy 候选 {e_cands}，Item 候选 {i_cands}：不入侵保护区/不可达区")

    # ---- 7. 开放区域比例合理：有空间也不空旷 ----
    open_count = sum(
        1 for r in range(GRID_SIZE) for c in range(GRID_SIZE)
        if grid[r][c] == TileType.EMPTY and not ljr_zone.is_ljr_protected(r, c)
    )
    assert 150 <= open_count <= 460, f"开放格 {open_count} 超出合理区间"
    print(f"[PASS] 开放区域 {open_count} 格：比例合理")

    # ---- 8. spawn_rules 统一判定 ----
    assert spawn_rules.is_spawn_blocked(11, 17) is True, "R 空腔被拦截"
    assert spawn_rules.is_spawn_blocked(2, 2) is False, "(2,2) 放行"
    print("[PASS] spawn_rules：保护区拦截、开放区放行")

    print("\nALL PASS")
    pygame.quit()


if __name__ == "__main__":
    main()