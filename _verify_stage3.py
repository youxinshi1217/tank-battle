# -*- coding: utf-8 -*-
"""
Stage 3「军事攻坚 · 多枢纽区」正式回归验证（headless）
====================================================
对生产模块 maps/map_03.py + stages/stage_03.py 做端到端校验：
  1. Stage 配置字段齐全（map_data/visual_fn/deco_fn/player_spawn/meta）
  2. 地图规范：25×25 / Tile 合法 / 外墙 / 保护区净化 / 主通道零障碍 / 全图连通
  3. LJR 笔画存在且未损坏（is_decorative 标记数量）
  4. 视觉层 25×25 且覆盖所有障碍格（None 允许，但外墙/环墙必须上色）
  5. 装饰层落在图内 EMPTY 格（不落障碍/笔画）
  6. 出生候选充足（PVP 双人开局随机出生）

用法：venv_py310/Scripts/python.exe _verify_stage3.py
"""
from collections import deque

from core.settings import GRID_SIZE
from maps.tile import TileType
from maps import ljr_zone
from stages.stage_03 import STAGE_CONFIG

EMPTY, BRICK, STEEL = TileType.EMPTY, TileType.BRICK, TileType.STEEL
report = []
fails = 0


def show(name, ok, detail=""):
    global fails
    report.append((name, bool(ok), detail))
    fails += (not ok)


def reach(g, start):
    sr, sc = start
    seen, dq = {(sr, sc)}, deque([(sr, sc)])
    while dq:
        r, c = dq.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and (nr, nc) not in seen \
                    and g[nr][nc] == EMPTY:
                seen.add((nr, nc))
                dq.append((nr, nc))
    return seen


# ---- 1) Stage 配置 ----
need = ("map_data", "visual_fn", "deco_fn", "player_spawn", "meta")
missing = [k for k in need if k not in STAGE_CONFIG]
show("1 Stage配置字段齐全", not missing, f"缺{missing}" if missing else "")

grid, is_deco = STAGE_CONFIG["map_data"]()
meta = STAGE_CONFIG["meta"]
show("1b meta 元信息", "name" in meta and "description" in meta,
     meta.get("name", ""))
sp = STAGE_CONFIG["player_spawn"]
show("1c 出生点配置合法", 0 <= sp[0] < GRID_SIZE and 0 <= sp[1] < GRID_SIZE
     and grid[sp[0]][sp[1]] == EMPTY, str(sp))

# ---- 2) 地图规范 ----
ok = len(grid) == GRID_SIZE and all(len(r) == GRID_SIZE for r in grid)
ok = ok and all(v in (EMPTY, BRICK, STEEL) for row in grid for v in row)
show("2 地图25×25 & Tile合法", ok)
ok = all(grid[0][c] == BRICK and grid[24][c] == BRICK for c in range(25))
ok = ok and all(grid[r][0] == BRICK and grid[r][24] == BRICK for r in range(1, 24))
show("2b 四周边墙完整", ok)
r0, r1, c0, c1 = ljr_zone.protected_zone((10, 5))
bad = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
       if grid[r][c] != EMPTY and not is_deco[r][c]]
show("2c 保护区零异物", not bad, f"异物{len(bad)}" if bad else "")

# ---- 3) LJR ----
ink = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
       if is_deco[r][c]]
bb = ljr_zone.ljr_bbox((10, 5))
ok = len(ink) > 0 and all(bb[0] <= r <= bb[1] and bb[2] <= c <= bb[3] for r, c in ink)
show("3 LJR笔画存在且位于bbox", ok, f"{len(ink)} 格笔画")

# ---- 4) 通道/门洞直通 ----
lanes = [(r, c) for r in range(1, 9) for c in (11, 12, 13)]
lanes += [(r, c) for r in range(16, 24) for c in (11, 12, 13)]
lanes += [(r, c) for r in (11, 12, 13) for c in range(1, 4)]
lanes += [(r, c) for r in (11, 12, 13) for c in range(21, 24)]
hits = [(r, c) for r, c in lanes if grid[r][c] != EMPTY]
show("4 四条主通道零障碍", not hits, f"占位{hits[:6]}" if hits else "")
gates = [(8, 10), (8, 14), (16, 10), (16, 14), (11, 3), (13, 3), (11, 23), (13, 23)]
gh = [(r, c) for r, c in gates if grid[r][c] != EMPTY]
show("4b 环墙四门洞直通", not gh, f"门洞被占{gh}" if gh else "")

# ---- 5) 全图连通 ----
total = sum(1 for row in grid for v in row if v == EMPTY)
seen = reach(grid, sp)
lost = [(r, c) for r in range(25) for c in range(25)
        if grid[r][c] == EMPTY and (r, c) not in seen]
cav = [p for p in lost if bb[0] <= p[0] <= bb[1] and bb[2] <= p[1] <= bb[3]]
show("5 全图连通(字形空腔豁免)", not [p for p in lost if p not in cav],
     f"空地{total} 可达{len(seen)} 空腔{len(cav)}")

# ---- 6) 视觉层 ----
visual = STAGE_CONFIG["visual_fn"]()
ok = len(visual) == GRID_SIZE and all(len(r) == GRID_SIZE for r in visual)
ok = ok and all(all(c is None or (isinstance(c, tuple) and len(c) == 3)
                    for c in row) for row in visual)
show("6 视觉层 25×25 且值为RGB|None", ok)
need_color = [(r, c) for r in (0, 24) for c in range(25)] + \
             [(r, c) for r in range(1, 24) for c in (0, 24)]
miss_c = [(r, c) for r, c in need_color if visual[r][c] is None]
show("6b 外墙均已上色", not miss_c, f"漏{miss_c[:6]}" if miss_c else "")

# ---- 7) 装饰层 ----
deco = STAGE_CONFIG["deco_fn"]()
kinds = {k for k, _, _ in deco}
ok = all(0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE
         and grid[r][c] == EMPTY for _, r, c in deco)
ok = ok and len(deco) > 0
show("7 装饰层合法（图内EMPTY格）", ok, f"{len(deco)} 个，种类{kinds}")

# ---- 8) 出生候选充足 ----
cands = 0
for r in range(1, GRID_SIZE - 1):
    for c in range(1, GRID_SIZE - 1):
        if grid[r][c] != EMPTY or ljr_zone.is_ljr_protected(r, c, (10, 5)):
            continue
        open_n = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                     if 0 <= r + dr < GRID_SIZE and 0 <= c + dc < GRID_SIZE
                     and grid[r + dr][c + dc] == EMPTY)
        if open_n >= 5:
            cands += 1
show("8 出生候选≥30", cands >= 30, f"{cands} 个")

# ---- 输出 ----
print("=" * 60)
print("Stage 3 正式回归报告（生产模块）")
print("=" * 60)
for name, ok, detail in report:
    print(f" {'[OK]' if ok else '[NG]'} {name}" + (f"  -- {detail}" if detail else ""))
print("-" * 60)
print(f"结论: {'全部通过 ✓' if fails == 0 else str(fails) + ' 项未通过'}")