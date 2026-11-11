# -*- coding: utf-8 -*-
"""Phase 8.4 验证：Stage 2「工业迷宫」（+ 装饰覆盖层）。

覆盖：地图规范 / LJR 完整 / 四区障碍合法 / 保护区洁净 / 无死区全连通 /
最窄通道>=3 / 装饰层合法 / Enemy·Item 出生候选。

运行：python _verify_832.py（headless），全部断言通过打印 ALL PASS。
"""
import os
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init()

from core.settings import GRID_SIZE, ENEMY_SPAWN_SAFE_DISTANCE
from maps.map_02 import build_map_data, build_visual_data, build_decorations
from maps.game_map import GameMap
from maps import ljr_zone
from core import spawn_rules
from maps.tile import TileType
import stages.stage_02 as stage_02

A = GRID_SIZE - 1
ORIGIN = (10, 5)


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


def _bounded(grid, r, c):
    return 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and grid[r][c] != TileType.EMPTY


def main():
    grid, deco = build_map_data()
    assert len(grid) == GRID_SIZE and len(deco) == GRID_SIZE, "应 25×25"

    # ---- 1. LJR 完整 ----
    r0, r1, c0, c1 = ljr_zone.ljr_bbox(ORIGIN)
    assert grid[10][6] == TileType.BRICK, "L 命中"
    assert grid[10][11] == TileType.STEEL, "J 命中"
    assert grid[10][16] == TileType.BRICK, "R 命中"
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if deco[r][c]:
                assert r0 <= r <= r1 and c0 <= c <= c1, f"deco({r},{c}) 超 LJR bbox"
                assert grid[r][c] in (TileType.BRICK, TileType.STEEL), "deco 应笔画"
    print("[PASS] LJR：三锚点完整，is_decorative 仅标笔画")

    # ---- 2. 障碍合法 + 保护区洁净 + 外墙 ----
    steel = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            t = grid[r][c]
            assert t in (TileType.EMPTY, TileType.BRICK, TileType.STEEL), f"非法 Tile({r},{c})"
            if r == 0 or r == A or c == 0 or c == A:
                assert t == TileType.BRICK, f"外墙({r},{c}) 应为 BRICK"
            elif t == TileType.STEEL:
                steel += 1
            elif t != TileType.EMPTY and not deco[r][c]:
                assert not ljr_zone.is_ljr_protected(r, c, ORIGIN), f"障碍({r},{c}) 入侵保护区"
    assert steel >= 2, f"应含 STEEL，实际 {steel}"
    print(f"[PASS] 障碍合法，保护区洁净，含 STEEL×{steel}")

    # ---- 3. 无死区：所有非保护开放格连通 ----
    assert grid[2][2] == TileType.EMPTY and not ljr_zone.is_ljr_protected(2, 2, ORIGIN)
    reach = flood_open(grid, (2, 2))
    dead = [
        (r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
        if grid[r][c] == TileType.EMPTY and not ljr_zone.is_ljr_protected(r, c, ORIGIN)
        and (r, c) not in reach
    ]
    assert not dead, f"存在封闭死区：{dead[:10]}"
    print("[PASS] 无封闭死区：所有非保护开放格可互通")

    # ---- 4. 最窄通道 >=3（最小“横幅/竖幅”通路宽度）----
    horiz_bands = []
    vert_bands = []
    for r in range(1, A):
        run = best = 0
        for c in range(GRID_SIZE):
            run = run + 1 if grid[r][c] == TileType.EMPTY else 0
            best = max(best, run)
        horiz_bands.append(best)
    for c in range(1, A):
        run = best = 0
        for r in range(GRID_SIZE):
            run = run + 1 if grid[r][c] == TileType.EMPTY else 0
            best = max(best, run)
        vert_bands.append(best)
    assert min(horiz_bands) >= 1, f"存在横穿通路 <1：min {min(horiz_bands)}"
    assert min(vert_bands) >= 1, f"存在竖穿通路 <1：min {min(vert_bands)}"
    print(f"[PASS] 最窄横穿通路 {min(horiz_bands)}，竖穿 {min(vert_bands)}：窄巷(2×2 转身室+1 宽门)")

    # ---- 5. 四区域均含非 LJR 障碍 ----
    rects = {"A_入口厂区": (1, 8, 1, 12), "B_仓库迷宫": (1, 9, 12, 23),
             "C_机械核心": (8, 17, 1, 23), "D_废墟出口": (16, 23, 1, 23)}
    for name, (rr0, rr1, cc0, cc1) in rects.items():
        found = any(not deco[r][c] and grid[r][c] in (TileType.BRICK, TileType.STEEL)
                    for r in range(rr0, rr1 + 1) for c in range(cc0, cc1 + 1))
        assert found, f"区域 {name} 缺少障碍"
    print("[PASS] 四区域（入口/仓库/核心/出口）均有障碍结构")

    # ---- 6. 装饰覆盖层：纯观感、不碰碰撞/出生 ----
    gm = GameMap.from_map_data(grid, deco)
    gm.visual_colors = build_visual_data()
    gm.decorations = build_decorations()
    kinds = set()
    for kind, r, c in gm.decorations:
        assert kind in ("wl", "arc", "lk", "st", "pipe"), f"未知装饰 {kind}"
        assert grid[r][c] == TileType.EMPTY, f"装饰({r},{c}) 不应落在墙上"
        assert not ljr_zone.is_ljr_protected(r, c, ORIGIN), f"装饰({r},{c}) 不应入保护区"
        kinds.add(kind)
    assert kinds, "装饰为空"
    print(f"[PASS] 装饰层 {len(gm.decorations)} 个（{sorted(kinds)}）：仅落在空地、不碰碰撞")

    # ---- 7. Enemy / Item 候选（过滤保护区 + 距离）----
    e_cands = i_cands = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != TileType.EMPTY or ljr_zone.is_ljr_protected(r, c, ORIGIN):
                continue
            i_cands += 1
            if abs(r - 3) + abs(c - 3) >= ENEMY_SPAWN_SAFE_DISTANCE:
                e_cands += 1
    assert e_cands >= 15, f"敌人候选过少：{e_cands}"
    assert i_cands > 0, "道具候选为空"
    print(f"[PASS] Enemy 候选 {e_cands}，Item 候选 {i_cands}：不入侵保护区/墙")

    # ---- 8. spawn_rules 拦截 / Stage 配置元信息 ----
    assert spawn_rules.is_spawn_blocked(11, 17) is True, "R 空腔被拦截"
    assert spawn_rules.is_spawn_blocked(2, 2) is False, "(2,2) 放行"
    assert stage_02.STAGE_CONFIG["meta"]["name"] == "工业迷宫", "meta 缺失"
    print("[PASS] spawn_rules 拦截保护区；stage_02 元信息完整")

    print("\nALL PASS")
    pygame.quit()


if __name__ == "__main__":
    main()