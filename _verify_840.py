# -*- coding: utf-8 -*-
"""Phase 8.5 验证：Stage 4「决战要塞」。

覆盖：地图规范 / LJR 完整 / 要塞环+四门 / 保护区洁净 / 无死区全连通 /
四角掩体合法 / 装饰层合法 / 出生点合法 / 多 Stage 流程接入。

运行：python _verify_840.py（headless），全部断言通过打印 ALL PASS。
"""
import os
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init()

from core.settings import GRID_SIZE
from maps.map_04 import (
    build_map_data, build_visual_data, build_decorations,
    _REGIONS, _FORTRESS_TOP, _FORTRESS_BOTTOM,
    _FORTRESS_LEFT, _FORTRESS_RIGHT,
    _NORTH_GATE_COLS, _SOUTH_GATE_COLS, _WEST_GATE_ROWS, _EAST_GATE_ROWS,
    _INNER_GUARD, _PLAZA_COVER,
)
from maps import ljr_zone
from maps.letters import LJR_SEQUENCE
from maps.tile import TileType
import stages.stage_04 as stage_04
import main as main_mod

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


def main():
    grid, deco = build_map_data()
    assert len(grid) == GRID_SIZE and len(deco) == GRID_SIZE, "应 25×25"

    # ---- 1. 瓦片合法性 ----
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            assert grid[r][c] in (TileType.EMPTY, TileType.BRICK,
                                  TileType.STEEL), f"非法瓦片 r{r}c{c}"

    # ---- 2. LJR 完整（逐位比对 letters.py）----
    for li, pattern in enumerate(LJR_SEQUENCE):
        start_col = ORIGIN[1] + li * 5
        for dr, row_str in enumerate(pattern):
            for dc, ch in enumerate(row_str):
                r, c = ORIGIN[0] + dr, start_col + dc
                expect = ch == "1"
                actual = grid[r][c] == TileType.BRICK
                assert expect == actual, f"LJR 不符 r{r}c{c}"
                if expect:
                    assert deco[r][c], f"LJR 笔画应标记 deco r{r}c{c}"
    # 全 BRICK（暖色核心）
    assert grid[10][6] == TileType.BRICK, "L 应为 BRICK"
    assert grid[10][11] == TileType.BRICK, "J 应为 BRICK"
    assert grid[10][16] == TileType.BRICK, "R 应为 BRICK"

    # ---- 3. 要塞环 + 四门 ----
    for c in range(_FORTRESS_LEFT + 1, _FORTRESS_RIGHT + 1):
        for g in (_FORTRESS_TOP, _FORTRESS_BOTTOM):
            expect = (c in _NORTH_GATE_COLS) if g == _FORTRESS_TOP \
                else (c in _SOUTH_GATE_COLS)
            if expect:
                assert grid[g][c] == TileType.EMPTY, f"门应空 ({g},{c})"
            else:
                assert grid[g][c] == TileType.STEEL, f"要塞墙应 STEEL ({g},{c})"
    for r in range(_FORTRESS_TOP + 1, _FORTRESS_BOTTOM):
        for wc in (_FORTRESS_LEFT, _FORTRESS_RIGHT):
            expect = (r in _WEST_GATE_ROWS) if wc == _FORTRESS_LEFT \
                else (r in _EAST_GATE_ROWS)
            if expect:
                assert grid[r][wc] == TileType.EMPTY, f"门应空 ({r},{wc})"
            else:
                assert grid[r][wc] == TileType.STEEL, f"要塞墙应 STEEL ({r},{wc})"

    # ---- 4. 保护区洁净（区内无非 LJR 障碍）----
    r0, r1, c0, c1 = ljr_zone.protected_zone(ORIGIN)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if not deco[r][c]:
                assert grid[r][c] == TileType.EMPTY, f"保护区含外来障碍 r{r}c{c}"

    # ---- 5. 四角掩体合法（不落保护区/不重叠）----
    seen = set()
    for name, cells in _REGIONS.items():
        for cell in cells:
            r, c = cell[0], cell[1]
            assert 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE, f"{name} 越界"
            assert not ljr_zone.is_ljr_protected(r, c, ORIGIN), f"{name} 入保护区"
            assert (r, c) not in seen, f"掩体重叠 {name} ({r},{c})"
            seen.add((r, c))
            kind = cell[2] if len(cell) > 2 else "B"
            want = TileType.STEEL if kind == "S" else TileType.BRICK
            assert grid[r][c] == want, f"{name} ({r},{c}) 类型不符"
    assert len(seen) == sum(len(v) for v in _REGIONS.values()), "掩体数量不符"

    # ---- 6. 无死区、全连通（以玩家出生候选 (2,2) 为源）----
    total_empty = sum(1 for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                      if grid[r][c] == TileType.EMPTY)
    reach = flood_open(grid, (2, 2))
    assert (2, 2) in reach, "出生点 (2,2) 应可通"
    # 允许的不可达格 = LJR 字形固有封闭腔（R 上环 2 格），其余必须可达
    assert len(reach) == total_empty - 2, \
        f"不可达格异常：总空{total_empty} 可达{len(reach)}"
    # 死胡同（>=3 面墙）仅允许字形腔内支路（R/J 空腔），不允许地图设计死区
    dead = []
    for r in range(1, A):
        for c in range(1, A):
            if grid[r][c] != TileType.EMPTY:
                continue
            walls = sum(1 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if grid[r + dr][c + dc] != TileType.EMPTY)
            if walls >= 3:
                dead.append((r, c))
    allowed_dead = {(11, 17), (11, 18), (13, 12), (13, 17), (13, 19)}
    assert set(dead) <= allowed_dead, f"意外死胡同: {set(dead) - allowed_dead}"
    assert set(dead) == allowed_dead, f"预期字形腔支路缺失: {allowed_dead - set(dead)}"

    # ---- 6b. 新增掩体合法（要塞内卫 + 广场火力走廊，共 26 格）----
    added = _INNER_GUARD + _PLAZA_COVER
    assert len(added) == 26, f"新增掩体应 26 格, 实得 {len(added)}"
    seen2 = set()
    for r, c in added:
        assert 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE, f"新增越界 ({r},{c})"
        assert not ljr_zone.is_ljr_protected(r, c, ORIGIN), f"新增入保护区 ({r},{c})"
        assert (r, c) not in seen2, f"新增内部重叠 ({r},{c})"
        seen2.add((r, c))
        assert grid[r][c] == TileType.BRICK, f"新增应 BRICK ({r},{c})"
    assert len(seen2 & seen) == 0, f"新增与四角掩体重叠: {seen2 & seen}"
    # 密度 37.6%（235 障碍格 / 625）
    assert total_empty == 625 - 235, f"EMPTY 应 390, 实得 {total_empty}"

    # ---- 7. 出生点合法 ----
    pr, pc = 2, 2
    assert grid[pr][pc] == TileType.EMPTY, "出生点应 EMPTY"
    assert not ljr_zone.is_ljr_protected(pr, pc, ORIGIN), "出生点不应在保护区"
    open_n = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                 if 0 <= pr + dr < GRID_SIZE and 0 <= pc + dc < GRID_SIZE
                 and grid[pr + dr][pc + dc] == TileType.EMPTY)
    assert open_n >= 5, "出生点周围应有移动空间"

    # ---- 8. 视觉 / 装饰层合法 ----
    visual = build_visual_data()
    assert len(visual) == GRID_SIZE and len(visual[0]) == GRID_SIZE, "视觉应 25×25"
    assert visual[0][0] is not None and visual[0][0][0] >= 0, "外墙应有配色"
    deco_list = build_decorations()
    for kind, r, c in deco_list:
        assert grid[r][c] == TileType.EMPTY, f"装饰应落 EMPTY ({r},{c})"
        assert kind in ("pipe", "wl", "arc", "lk", "st"), f"未知装饰类型 {kind}"

    # ---- 9. 多 Stage 流程接入 ----
    cfg = stage_04.STAGE_CONFIG
    assert cfg["map_data"] is build_map_data, "map_data 引用一致"
    assert cfg["player_spawn"] == (2, 2), "出生参考点"
    assert main_mod.STAGES[-1] is cfg, "main.STAGES 应含 Stage 4 且为末关"
    assert len(main_mod.STAGES) == 4, "应共 4 关"

    print("ALL PASS: Stage 4 决战要塞 验证通过")


if __name__ == "__main__":
    main()
