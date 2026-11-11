# -*- coding: utf-8 -*-
"""Phase 8.3 验证：固定 Stage 1（LJR Arena）——外墙/LJR/保护区/对称/出生/flood/Enemy/Item。

运行方式：python _verify_830.py（headless，SDL dummy），全部断言通过打印 ALL PASS。
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

PLAYER_SPAWN = (3, 3)   # (row, col)
LJR_ORIGIN = (10, 5)


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

    # ---- 1. 外墙：整圈 BRICK ----
    for c in range(GRID_SIZE):
        assert grid[0][c] == TileType.BRICK, f"row0 col{c} 应为 BRICK"
        assert grid[GRID_SIZE - 1][c] == TileType.BRICK, f"row24 col{c} 应为 BRICK"
    for r in range(GRID_SIZE):
        assert grid[r][0] == TileType.BRICK, f"row{r} col0 应为 BRICK"
        assert grid[r][GRID_SIZE - 1] == TileType.BRICK, f"row{r} col24 应为 BRICK"
    print("[PASS] 外墙：row0/row24/col0/col24 全部 BRICK")

    # ---- 2. LJR 存在 + is_decorative 只标 LJR 笔画 ----
    bbox = ljr_zone.ljr_bbox(LJR_ORIGIN)
    assert grid[10][6] == TileType.BRICK, "L 命中"
    assert grid[10][11] == TileType.STEEL, "J 命中"
    assert grid[10][16] == TileType.BRICK, "R 命中"
    r0, r1, c0, c1 = bbox
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if deco[r][c]:
                assert r0 <= r <= r1 and c0 <= c <= c1, f"deco({r},{c}) 超出 LJR bbox"
                assert grid[r][c] in (TileType.BRICK, TileType.STEEL), f"deco({r},{c}) 应笔画"
    print("[PASS] LJR：bbox 命中三锚点；is_decorative 仅标笔画格")

    # ---- 3. Protected Zone ----
    pz = ljr_zone.protected_zone(LJR_ORIGIN)
    assert pz == (9, 15, 4, 21), f"Protected Zone 应为 (9,15,4,21)，实际 {pz}"
    pr0, pr1, pc0, pc1 = pz
    for r in range(pr0, pr1 + 1):
        for c in range(pc0, pc1 + 1):
            # 只允许：EMPTY（含 R 空腔）或 LJR 笔画（deco=True）
            if not (grid[r][c] == TileType.EMPTY or deco[r][c]):
                assert False, f"保护区({r},{c}) 出现非 LJR 障碍"
    # R 空腔：EMPTY + deco=False + protected=True（R 上环内腔 (11,17)）
    assert grid[11][17] == TileType.EMPTY, "R 空腔应为 EMPTY"
    assert not deco[11][17], "R 空腔 is_decorative=False"
    assert ljr_zone.is_ljr_protected(11, 17), "R 空腔应 protected=True"
    print("[PASS] Protected Zone：(9,15,4,21)；内部仅 LJR/EMPTY；R 空腔三属性正确")

    # ---- 4. 障碍合法性：非外墙、非 LJR 的障碍均为 BRICK/STEEL，且全在保护区外 ----
    A = GRID_SIZE - 1  # 24
    outer_count = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            t = grid[r][c]
            if t == TileType.EMPTY:
                continue
            if r == 0 or r == A or c == 0 or c == A:
                assert t == TileType.BRICK, f"外墙({r},{c}) 应为 BRICK"
                outer_count += 1
                continue
            if deco[r][c]:
                continue
            assert t in (TileType.BRICK, TileType.STEEL), f"障碍({r},{c}) 非法类型"
            assert not ljr_zone.is_ljr_protected(r, c), f"障碍({r},{c}) 入侵保护区"
    has_brick = any(grid[r][c] == TileType.BRICK and not deco[r][c]
                    for r in range(GRID_SIZE) for c in range(GRID_SIZE))
    has_steel = any(grid[r][c] == TileType.STEEL and not deco[r][c]
                    for r in range(GRID_SIZE) for c in range(GRID_SIZE))
    assert has_brick and has_steel, "障碍应同时含 BRICK 与 STEEL"
    print("[PASS] 障碍：BRICK+STEEL 存在，全部位于保护区外，无非法 Tile")

    # ---- 5. 玩家出生 (3,3) ----
    pr, pc = PLAYER_SPAWN
    assert grid[pr][pc] == TileType.EMPTY, "出生点应为空地"
    assert not ljr_zone.is_ljr_protected(pr, pc), "出生点不应在 Protected Zone"
    print("[PASS] 玩家出生 (3,3)：空地、非保护区")

    # ---- 6. Flood-fill：出生点可达所有非保护开放区 ----
    reach = flood_open(grid, PLAYER_SPAWN)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == TileType.EMPTY and not ljr_zone.is_ljr_protected(r, c):
                assert (r, c) in reach, f"非保护开放格({r},{c}) 不可达出生点"
    print("[PASS] Flood-fill：出生点可达全部非保护开放战斗区")

    # ---- 7. Enemy Spawn 候选：过滤保护区后仍足够 ----
    e_candidates = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != TileType.EMPTY:
                continue
            if ljr_zone.is_ljr_protected(r, c):
                continue
            if abs(r - pr) + abs(c - pc) < ENEMY_SPAWN_SAFE_DISTANCE:
                continue
            e_candidates += 1
    assert e_candidates >= 20, f"敌人合法候选过少：{e_candidates}"
    print(f"[PASS] Enemy 候选（过滤保护区+距离后）：{e_candidates} >= 20")

    # ---- 8. Item Spawn 候选 ----
    i_candidates = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != TileType.EMPTY:
                continue
            if ljr_zone.is_ljr_protected(r, c):
                continue
            if (r, c) == PLAYER_SPAWN:
                continue
            i_candidates += 1
    assert i_candidates > 0, "道具合法候选为空"
    print(f"[PASS] Item 候选：{i_candidates} -> 不会生成进保护区/R 空腔")

    # ---- 9. spawn_rules 统一接口 ----
    assert spawn_rules.is_spawn_blocked(11, 17) is True, "R 空腔应被 spawn_rules 拦截"
    assert spawn_rules.is_spawn_blocked(PLAYER_SPAWN[0], PLAYER_SPAWN[1]) is False, "出生点不应拦截"
    print("[PASS] spawn_rules 统一判定：保护区拦截、出生点放行")

    print("\nALL PASS")
    pygame.quit()


if __name__ == "__main__":
    main()