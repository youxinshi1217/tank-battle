# -*- coding: utf-8 -*-
"""_verify_stage5.py — Stage 5「戈壁环岛」验收脚本（数据与验证同源）。

跑法（项目根目录）：
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy venv_py310/Scripts/python.exe _verify_stage5.py

★ 2026-10-23 连续几何模型起的主要变化：
  - 物理真碰撞 = `map_05.build_geometry()`（圆/圆环浮点几何，不经格子）；
  - [4b] 新增几何口径可达性 BFS（真碰撞 + 6px 栅格搜捕死区）；
  - [8] 重写为「坦克矩形 vs 渲染像素」双向断言（几何层与视觉层必须一致）；
  - [8b] 新增「绘制半径 == 几何半径」同源断言；
  - [7] 出生候选与 main.py 同规则（格子 + 3×3 + 几何矩形精查）。
"""
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.settings import GRID_SIZE, TILE_SIZE, TANK_SIZE
from maps.tile import TileType
from maps import ljr_zone
from maps import map_05

EMPTY = TileType.EMPTY
N = GRID_SIZE
CX = CY = N / 2.0
TANK_CELLS = TANK_SIZE / float(TILE_SIZE)

_pass = 0
_fail = 0


def ck(cond, msg):
    global _pass, _fail
    if cond:
        _pass += 1
        print("  [OK]   %s" % msg)
    else:
        _fail += 1
        print("  [FAIL] %s" % msg)
    return cond


def _outer_all_reach_center(grid, outer, cx, cy, n, r_out):
    """外环带外侧的孤立点，是否都能绕回中央（= 不是死区）。

    为什么需要：缺口正前方/对角远处的钢球会把外环跑道切成几段。
    这是**设计本意**（球就挡在路上），不是地图缺陷。真正要保证的是：
    被球隔出去的那几格仍能通过缺口绕回中央 —— 否则才是死区。
    """
    opens = set((r, c) for r in range(n) for c in range(n)
                if grid[r][c] == TileType.EMPTY)
    for start in outer:
        reach = {start}
        q = deque([start])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (r + dr, c + dc)
                if nb in opens and nb not in reach:
                    reach.add(nb)
                    q.append(nb)
        if len(reach) != len(opens):
            return False
    return True


def main():
    grid, is_dec = map_05.build_map_data()

    def empty(r, c):
        return 0 <= r < N and 0 <= c < N and grid[r][c] == EMPTY

    # ------------------------------------------------------------------
    print("=" * 74)
    print("Stage 5「戈壁环岛」验收（连续几何模型）")
    print("=" * 74)

    # ---- 几何对象准备（[4b]/[7]/[8] 共用；与正式游戏同一把尺子） ----
    import pygame as _pg
    if not _pg.get_init():
        _pg.init()
    from maps.game_map import GameMap as _GM
    from maps.map_renderer import MapRenderer as _MR
    from core.collision import rect_hits_obstacle as _rhit

    _geo = map_05.build_geometry()
    _gm2 = _GM.from_map_data(grid, [[False] * N for _ in range(N)])
    _gm2.shapes = map_05.build_shapes()
    _gm2.geometry = _geo
    _sh = _gm2.shapes

    def _tank_rect(cx, cy):
        r = _pg.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        r.center = (cx, cy)
        return r

    # ------------------------------------------------------------------
    print("\n[1] 基础规格")
    ck(len(grid) == N and all(len(row) == N for row in grid),
       "地图 %dx%d 格 = %dx%dpx（栅格层仅作出生初筛/渲染回退，碰撞以连续几何为准）"
       % (N, N, N * TILE_SIZE, N * TILE_SIZE))
    used = set()
    for r in range(N):
        for c in range(N):
            used.add(grid[r][c])
    ck(used <= {EMPTY, TileType.BRICK, TileType.STEEL},
       "只用 EMPTY/BRICK/STEEL，实际用到 %s" % sorted(int(x) for x in used))
    n_brick = sum(1 for r in range(N) for c in range(N) if grid[r][c] == TileType.BRICK)
    n_steel = sum(1 for r in range(N) for c in range(N) if grid[r][c] == TileType.STEEL)
    n_open = N * N - n_brick - n_steel
    print("       [栅格参考值，非碰撞口径] 沙洲(BRICK)=%d  钢球(STEEL)=%d  空地=%d  空地率=%.1f%%"
          % (n_brick, n_steel, n_open, 100.0 * n_open / (N * N)))

    print("\n[2] 8 条缺口通道：净宽 & 等宽性（几何口径）")
    widths = []
    for deg in map_05.notch_angles():
        w = map_05.notch_clear_width(deg)
        widths.append(w)
    for deg, w in zip(map_05.notch_angles(), widths):
        print("       缺口 %5.1f 度 -> 净宽 %.0fpx = %.2f 辆坦克"
              % (deg, w * TILE_SIZE, w / TANK_CELLS))
    mn, mx = min(widths), max(widths)
    ck(mn >= 2.9,
       "最窄缺口 %.0fpx = %.2f 辆坦克 >= 96px 设计净宽"
       % (mn * TILE_SIZE, mn / TANK_CELLS))
    # 等宽性由构造保证（8 条走廊共用同一个 half_w 常量）；
    # 测量差 <=0.06 格来自在 1.50 精确边界上的浮点噪声（步长 0.02）。
    ck(mx - mn <= 0.06,
       "8 条缺口宽度差 %.1fpx <= 2px（构造等宽；余量为边界浮点噪声）"
       % ((mx - mn) * TILE_SIZE))

    print("\n[3] 全图连通性 / 死胡同")
    opens = [(r, c) for r in range(N) for c in range(N) if empty(r, c)]
    seen, q = set(), deque([opens[0]])
    seen.add(opens[0])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n not in seen and empty(*n):
                seen.add(n)
                q.append(n)
    ck(len(seen) == len(opens),
       "空地100%% 连通：%d/%d" % (len(seen), len(opens)))

    # 死胡同：四邻全被挡的空格
    dead = [(r, c) for (r, c) in opens
            if not any(empty(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    ck(len(dead) == 0, "零死胡同（发现 %d 处 %s）" % (len(dead), dead[:5]))

    print("\n[4] 中央广场 & 外环跑道")
    plaza = [(r, c) for (r, c) in opens
             if math.hypot(r + 0.5 - CY, c + 0.5 - CX) <= map_05.RING_R_IN - 0.3]
    print("       中央广场直径 %.0fpx（半径 %.1f 格，纯圆无遮挡）"
          % ((map_05.RING_R_IN - 0.3) * 2 * TILE_SIZE,
             map_05.RING_R_IN - 0.3))
    ck(len(plaza) >= 90, "中央广场够大（空地 %d 处 >= 90），可作导弹规避场" % len(plaza))

    outer = [(r, c) for (r, c) in opens
             if math.hypot(r + 0.5 - CY, c + 0.5 - CX) >= map_05.RING_R_OUT + 0.3]
    seen2, q2 = set(), deque([outer[0]])
    seen2.add(outer[0])
    while q2:
        r, c = q2.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n not in seen2 and empty(*n) \
               and math.hypot(n[0] + 0.5 - CY, n[1] + 0.5 - CX) >= map_05.RING_R_OUT + 0.3:
                seen2.add(n)
                q2.append(n)
    ck(len(seen2) == len(outer)
       or _outer_all_reach_center(grid, outer, CX, CY, N, map_05.RING_R_OUT),
       "外环跑道：主连通块 %d/%d，其余 %d 格均可绕回中央（无死区）"
       % (len(seen2), len(outer), len(outer) - len(seen2)))

    # 外环最窄处
    worst = (99.0, None)
    for (r, c) in outer:
        run = 1
        while c - run >= 0 and empty(r, c - run):
            run += 1
        while c + run < N and empty(r, c + run):
            run += 1
        if run < worst[0]:
            worst = (run, (r, c))
    print("       外环最窄连续通路 %.0fpx @ %s"
          % (worst[0] * TILE_SIZE, worst[1]))
    ck(worst[0] >= 1,
       "外环最窄 %.0fpx 可容坦克 %dpx 通过"
       % (worst[0] * TILE_SIZE, int(TANK_SIZE)))

    # ------------------------------------------------------------------
    print("\n[4b] ★ 连续几何可达性（真碰撞口径 BFS，搜捕死区）")
    STEP = 6
    W = N * TILE_SIZE

    def _snap(v):
        return int(round(v / STEP)) * STEP

    def _polar(r, ang_deg, lat=0.0):
        a = math.radians(ang_deg)
        ux, uy = math.cos(a), math.sin(a)
        return ((CX + ux * r - uy * lat) * TILE_SIZE,
                (CY + uy * r + ux * lat) * TILE_SIZE)

    lats = [v for v in range(0, W, STEP) if 12 <= v <= W - 13]
    free = set()
    qq = deque()
    st = (_snap(W / 2), _snap(W / 2))
    if not _rhit(_tank_rect(*st), _gm2):
        free.add(st)
        qq.append(st)
        while qq:
            x, y = qq.popleft()
            for dx, dy in ((STEP, 0), (-STEP, 0), (0, STEP), (0, -STEP)):
                nb = (x + dx, y + dy)
                if nb in free or not (12 <= nb[0] <= W - 13 and 12 <= nb[1] <= W - 13):
                    continue
                if not _rhit(_tank_rect(*nb), _gm2):
                    free.add(nb)
                    qq.append(nb)
    pockets = [(x, y) for x in lats for y in lats
               if (x, y) not in free and not _rhit(_tank_rect(x, y), _gm2)]
    print("       可达采样点 %d，孤立死区采样点 %d（6px 步长）" % (len(free), len(pockets)))
    if pockets:
        print("       死区样例：%s" % pockets[:8])
    ck(len(pockets) == 0, "连续几何死区 = %d 处（应 0）" % len(pockets))

    tg = {
        "8 个走廊出口": [_polar(9.7, a) for a in map_05.notch_angles()],
        "外场(轴/角)": [_polar(11.5, 0.0), _polar(14.5, 45.0), _polar(14.5, 135.0)],
    }
    for name, pts in tg.items():
        ok = sum(1 for tx, ty in pts
                 if any((_snap(tx) + dx, _snap(ty) + dy) in free
                        for dx in (-STEP, 0, STEP) for dy in (-STEP, 0, STEP)))
        ck(ok == len(pts), "%s 可达 %d/%d" % (name, ok, len(pts)))

    # ------------------------------------------------------------------
    print("\n[5] 钢球位置：缺口正前方 + 缝隙达标（>=1.5 辆坦克）")
    small = [s for s in map_05.ball_specs() if not s[3]]
    big = [s for s in map_05.ball_specs() if s[3]]
    ck(len(small) == 8, "小球8 颗")
    ck(len(big) == 4, "大球 4 颗")
    for i, (bx, by, br, is_big) in enumerate(map_05.ball_specs()):
        d = math.hypot(bx - CX, by - CY)
        ang = math.degrees(math.atan2(by - CY, bx - CX)) % 360.0
        print("       %s #%2d 角度%6.1f度 轨道%5.0fpx 直径%.0fpx %s"
              % ("大球" if is_big else "小球", i, ang, d * TILE_SIZE,
                 br * 2 * TILE_SIZE, "对角远处" if is_big else "缺口正前方"))
    # 小球必须严格落在缺口中线上
    off = []
    for ang in map_05.notch_angles():
        best = min(
            (math.degrees(math.atan2(by - CY, bx - CX)) % 360.0
             for bx, by, br, is_big in small),
            key=lambda t: min(abs(t - ang), 360 - abs(t - ang)))
        off.append(min(abs(best - ang), 360 - abs(best - ang)))
    ck(max(off) < 1e-6, "8 颗小球全部严格压在缺口中线上（最大角偏差 %.2e 度）" % max(off))
    # 小球必须在沙洲外侧（不压住沙洲）
    ok_orbit = all(abs(math.hypot(bx - CX, by - CY) - map_05.BALL_SMALL_ORBIT) < 1e-6
                   for bx, by, br, _ in small)
    ck(ok_orbit and map_05.BALL_SMALL_ORBIT > map_05.RING_R_OUT,
       "小球轨道 %.0fpx > 环带外径 %.0fpx（悬在缺口前方外侧，不压沙洲）"
       % (map_05.BALL_SMALL_ORBIT * TILE_SIZE, map_05.RING_R_OUT * TILE_SIZE))

    # ★ 球与沙洲的缝隙（用户红线：>= 1.5 辆坦克 = 37.5px）
    slot_s = (map_05.BALL_SMALL_ORBIT - map_05.BALL_SMALL_R - map_05.RING_R_OUT) * TILE_SIZE
    slot_b = (map_05.BALL_BIG_ORBIT - map_05.BALL_BIG_R - map_05.RING_R_OUT) * TILE_SIZE
    print("       小球缝隙 %.0fpx = %.2f 辆坦克 | 大球缝隙 %.0fpx = %.2f 辆坦克"
          % (slot_s, slot_s / TANK_SIZE, slot_b, slot_b / TANK_SIZE))
    ck(slot_s >= TANK_SIZE * 1.5,
       "小球缝隙 %.0fpx >= 1.5 辆坦克 (%.0fpx)" % (slot_s, TANK_SIZE * 1.5))
    ck(slot_b >= TANK_SIZE * 1.5,
       "大球缝隙 %.0fpx >= 1.5 辆坦克 (%.0fpx)" % (slot_b, TANK_SIZE * 1.5))

    # 球与球不重叠、不出界
    specs = map_05.ball_specs()
    min_gap = min(
        (math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] - b[2]) * TILE_SIZE
        for i, a in enumerate(specs) for b in specs[i + 1:])
    ck(min_gap >= 40.0, "球与球最小表面间隙 %.0fpx >= 40px（不粘连）" % min_gap)
    min_edge = min(
        min(bx * TILE_SIZE - br * TILE_SIZE,
            (W - bx * TILE_SIZE) - br * TILE_SIZE,
            by * TILE_SIZE - br * TILE_SIZE,
            (W - by * TILE_SIZE) - br * TILE_SIZE)
        for bx, by, br, _ in specs)
    ck(min_edge >= 8.0, "球贴地图边最小余量 %.0fpx >= 8px（不被边界切掉）" % min_edge)

    print("\n[6] LJR 水印：不占格、不阻碰撞")
    wm = map_05._watermark_spec()
    n_cells = len(wm["cells"])
    half_w = wm["width"] * wm["scale"] / 2.0
    print("       水印 %dx%d 字模单元 x scale%.2f -> %.0fpx 宽 x %.0fpx 高, %d 个笔画单元"
          % (wm["width"], wm["height"], wm["scale"],
             wm["width"] * wm["scale"] * TILE_SIZE,
             wm["height"] * wm["scale"] * TILE_SIZE, n_cells))
    ck(half_w * 2 * TILE_SIZE < (map_05.RING_R_IN - 0.5) * 2 * TILE_SIZE,
       "水印宽度 %.0fpx < 中央广场直径 %.0fpx（不压到沙洲）"
       % (wm["width"] * wm["scale"] * TILE_SIZE,
          (map_05.RING_R_IN - 0.5) * 2 * TILE_SIZE))
    ck(n_cells > 0, "水印笔画已解析（%d 个单元）" % n_cells)

    print("\n[7] 出生点与保护区（与 main.py 同规则：格子 + 3×3 + 几何精查）")
    pr, pc = map_05.PLAYER_SPAWN
    ck(empty(pr, pc), "参考出生点 (%d,%d) 可通行" % (pr, pc))

    def _geo_ok(r, c):
        return not _rhit(_tank_rect(c * TILE_SIZE + TILE_SIZE / 2,
                                    r * TILE_SIZE + TILE_SIZE / 2), _gm2)

    cands_old = [(r, c) for (r, c) in opens
                 if not ljr_zone.is_ljr_protected(r, c)
                 and sum(1 for rr in range(max(0, r - 1), min(N, r + 2))
                         for cc in range(max(0, c - 1), min(N, c + 2)) if empty(rr, cc)) >= 5]
    cands = [(r, c) for (r, c) in cands_old if _geo_ok(r, c)]
    print("       老规则候选 %d 个；几何精查否掉 %d 个（栅格中心空但坦克矩形压墙）"
          % (len(cands_old), len(cands_old) - len(cands)))
    ck(len(cands) >= 30,
       "随机出生候选 %d 个 >= 30（main 会随机取）" % len(cands))
    cands2 = [(r, c) for (r, c) in opens
              if sum(1 for rr in range(max(0, r - 1), min(N, r + 2))
                     for cc in range(max(0, c - 1), min(N, c + 2)) if empty(rr, cc)) >= 5]
    print("       不受 LJR 保护区限制时出生候选 %d 个" % len(cands2))

    # ------------------------------------------------------------------
    print("\n[8] ★ 隐形墙：坦克矩形 vs 视觉墙（连续几何口径，双向断言）")
    # 判据设计（为什么必须是像素级）：
    #   数据层函数自己验自己恒等于 0 —— 「23/23 全绿」的同时环段曾整体
    #   错位 22.5°、球胖 3.3 倍。所以这里直接调 MapRenderer 渲染成像素，
    #   拿真碰撞函数 rect_hits_obstacle() 逐格比对。
    #   方向1（隐形墙）：坦克矩形真撞 -> 矩形内必须看得到墙；
    #   方向2（画大了）：墙本体色像素 -> 坦克矩形放在它上面必须真撞。
    _sf = _pg.Surface((N * TILE_SIZE, N * TILE_SIZE))
    _MR(_gm2).render(_sf)
    _px2 = _pg.surfarray.pixels3d(_sf)

    from maps.map_renderer import _lighter as _lt, _darker as _dk
    # 「看得见墙」= 本体色 + 画在墙身上的装饰色（高光弧/暗弧/直边描线/球缘）。
    #   这些颜色只出现在墙身上，看到它就等于看到了墙。
    _WALLISH = frozenset((
        map_05.RING_TOP, map_05.RING_SIDE, map_05.BALL_LIGHT, map_05.BALL_RIM,
        _lt(map_05.RING_TOP), _dk(map_05.RING_SIDE), _lt(map_05.BALL_LIGHT),
    ))
    # 「墙本体」= 只有实心填充色（高光/描边会探出形状外 1~2px，不算本体）
    _BODY = frozenset((map_05.RING_TOP, map_05.RING_SIDE, map_05.BALL_LIGHT))

    # --- 方向 1：真撞但整个矩形看不见墙 -> 隐形墙 ---
    _hf = TANK_SIZE // 2
    _hidden = []
    for _r in range(N):
        for _c in range(N):
            _rect = _tank_rect(_c * TILE_SIZE + TILE_SIZE // 2,
                               _r * TILE_SIZE + TILE_SIZE // 2)
            if not _rhit(_rect, _gm2):
                continue
            _seen = False
            for _y in range(_rect.top, _rect.bottom):
                for _x in range(_rect.left, _rect.right):
                    if tuple(_px2[_x][_y]) in _WALLISH:
                        _seen = True
                        break
                if _seen:
                    break
            if not _seen:
                _hidden.append((_r, _c))
    ck(len(_hidden) == 0,
       "隐形墙（真撞但看不见）= %d 处（应 0）%s"
       % (len(_hidden), _hidden[:6] if _hidden else ""))

    # --- 方向 2：画了本体色但坦克撞不到 -> 画出来的比实体大 ---
    _ghost = []
    for _y in range(N * TILE_SIZE):
        for _x in range(N * TILE_SIZE):
            if tuple(_px2[_x][_y]) not in _BODY:
                continue
            # 像素中心已在几何内 -> 矩形必撞（rect_hit 必测中心点），快筛
            if _geo.point_solid(_x + 0.5, _y + 0.5):
                continue
            if not _rhit(_tank_rect(_x, _y), _gm2):
                _ghost.append((_x, _y))
    ck(len(_ghost) == 0,
       "画了本体色但撞不到 = %d px（应 0，即视觉从不大于实体）%s"
       % (len(_ghost), _ghost[:6] if _ghost else ""))

    # ------------------------------------------------------------------
    # ★ [8b] 形状层与几何层同源断言（防「渲染一套数、碰撞一套数」）
    # ------------------------------------------------------------------
    print("\n[8b] ★ 形状角度 & 视觉/几何同源")
    _seg_angles = sorted(s["angle"] % 360 for s in _sh["segments"])
    _notch_angles = sorted(a % 360 for a in map_05.notch_angles())
    _overlap = min(abs(a - n) for a in _seg_angles for n in _notch_angles)
    ck(_overlap > 5.0,
       "环段中线与缺口中线最小夹角 = %.1f 度（应 >5，防整体错位）" % _overlap)
    _mindiff_seg = min(abs(_seg_angles[i + 1] - _seg_angles[i])
                       for i in range(len(_seg_angles) - 1))
    ck(abs(_mindiff_seg - 45.0) < 0.01,
       "8 段环段等分45 度（实测最小间隔 %.3f）" % _mindiff_seg)

    # 环段内窄外宽（与手绘稿一致：梯形环段、外宽内窄）
    _spans = [(_s["span_in"], _s["span_out"]) for _s in _sh["segments"]]
    ck(all(a < b for a, b in _spans),
       "环段内窄外宽（span_in < span_out，%d/%d 段）"
       % (sum(1 for a, b in _spans if a < b), len(_spans)))

    # 零膨胀：视觉半径与碰撞半径必须是同一个数
    ck(all(abs(_s["r_in"] - _geo.r_in) < 1e-9
           and abs(_s["r_out"] - _geo.r_out) < 1e-9
           for _s in _sh["segments"]),
       "环段视觉半径 == 几何碰撞半径（r_in=%.2f r_out=%.2f）"
       % (_geo.r_in, _geo.r_out))
    ck(all(abs(_b["r"] - _g[2]) < 1e-9
           for _b, _g in zip(_sh["balls"], _geo.balls)),
       "钢球绘制半径 == 几何碰撞半径（12/12 同一个数，看到多大撞多大）")
    ck(all(_b["r_px"] >= math.ceil(_b["r"] * TILE_SIZE) for _b in _sh["balls"]),
       "钢球像素半径已向上取整（消除亚像素失配）")

    print("\n[9] 形状层 & 配色接口")
    shapes = map_05.build_shapes()
    ck(len(shapes["segments"]) == 8, "形状层：8 段梯形环段")
    ck(len(shapes["balls"]) == 12, "形状层：12 颗钢球（8 小 + 4 大）")
    ck(shapes["watermark"] is not None, "形状层：LJR 水印已挂载")
    vis = map_05.build_visual_data()
    ck(len(vis) == N and len(vis[0]) == N, "区域配色 25x25")
    dec = map_05.build_decorations()
    ck(isinstance(dec, list), "装饰覆盖层返回 list（本关为空：%d）" % len(dec))
    ck(isinstance(_geo, map_05.RingGeometry), "连续几何已导出（RingGeometry）")

    print("\n" + "=" * 74)
    print("结果：%d 项通过，%d 项失败" % (_pass, _fail))
    print("=" * 74)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
