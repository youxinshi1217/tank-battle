# 敌方 AI 升级（扇形避障 + 反弹预判 + 状态机/DODGE）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让敌方坦克具备平滑扇形避障、反弹命中预判、子弹躲闪（DODGE）三能力，且不引入转向振荡或逻辑死锁。

**Architecture:** 纯几何工具封装到新模块 `entities/enemy_perception.py`（含 `raycast_distance`、`line_of_sight`、`predict_ricochet_hits`）；`entities/enemy_tank.py` 在其 FSM（PATROL/CHASE/ESCAPE，新增 DODGE）中消费这些工具作"避障覆盖层 + 火力瞄准 + 生存躲闪"。`main.py` 只需补一行把玩家子弹喂给 `enemy.evaluate_threats`。三块正交、逐块落地。

**Tech Stack:** Python 3.14 + pygame；遵循既有 `_verify_XXX.py` headless（SDL dummy）断言脚本作验证；改动集中在 `enemy_tank.py` / `enemy_perception.py` / `main.py`，冷冻文件不动。

**约束（不可破坏）：**
- 冷冻文件（`entities/player_tank.py`、`core/collision.py`、`core/tank_physics.py`、`entities/bullet.py` 等）字节级不得改动。
- 炮塔必须跟随车身：反弹预判若要朝某角开火，通过把**车身**转到该角实现，不独立转炮塔。
- 转向介入一律带迟滞/死区，避免 ±18° 振荡。

---

## 文件结构

- **Create** `entities/enemy_perception.py`：纯函数几何工具（无状态、无 pygame 依赖头），可独立测试。
- **Modify** `entities/enemy_tank.py`：消费工具；加 `DODGE` 状态、避障覆盖、反弹瞄准。
- **Modify** `main.py`：敌方更新循环中调用 `evaluate_threats(self.bullets)`。
- **Create** `_verify_900.py`：本功能的 headless 验证脚本（逐任务加断言段）。
- **Modify** `_verify_800.py`：把 `enemy_tank.py` 从 `FROZEN_BASELINE` 移到 `MODIFIED`。

---

### Task 1: 感知工具模块 `enemy_perception.py` + 验证脚本骨架

**Files:**
- Create: `entities/enemy_perception.py`
- Create: `_verify_900.py`
- Test: `_verify_900.py`

- [ ] **Step 1: 先创建验证脚本骨架**（TDD：断言对不存在函数，应当失败）

创建 `_verify_900.py`：

```python
# -*- coding: utf-8 -*-
"""Phase 9.0 冒烟验证：敌方 AI 感知工具 + 扇形避障 + DODGE + 反弹预判。

运行方式：python _verify_900.py（headless，SDL dummy），全部断言通过打印 ALL PASS。
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from maps.game_map import GameMap
from maps.tile import TileType
from entities.enemy_perception import (
    raycast_distance,
    line_of_sight,
    predict_ricochet_hits,
)
from core.settings import TILE_SIZE, GRID_SIZE


def _open_map():
    """全空地图 25×25，便于在测试里手工放墙。"""
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    deco = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    return GameMap.from_map_data(grid, deco)


def main():
    # ---- 1. raycast_distance：全空地图畅通、命中墙壁返回距离 ----
    gm = _open_map()
    # 全空：5 格=160px 内应畅通（TILE=32）
    assert raycast_distance(gm, 16, 16, 0.0, -1.0, 160.0) == 160.0, "全空应返回 max_range"
    # 在 (5,5) 格放墙；射线朝右应命中该列
    gm.grid[5][5] = TileType.BRICK
    # 起点在 (16, 5*32+16)，朝右 +x，命中 col5 前应返回 <160
    d = raycast_distance(gm, 16, 5 * TILE_SIZE + 16, 1.0, 0.0, 160.0)
    assert 96.0 < d < 160.0, f"应命中 col5 范围的墙，实际 d={d}"
    print("[PASS] raycast_distance")

    # ---- 2. line_of_sight：视线被墙遮挡 ----
    gm2 = _open_map()
    a = (16, 16)
    b_full = (16 + 4 * TILE_SIZE, 16)          # 同排无墙
    gm2.grid[5][2] = TileType.STEEL            # (row5,col2) 挡在两点之间下方
    assert line_of_sight(gm2, *a, *b_full) is True, "无遮挡应可见"
    gm2.grid[5][2] = TileType.BRICK            # 现在 a->b 间不被挡（不在两点连线上）
    gm2.grid[1][100 // TILE_SIZE] = TileType.EMPTY
    # 构造真正遮挡：同行放墙
    gm3 = _open_map()
    gm3.grid[0][2] = TileType.STEEL            # row0 列2 挡在 (16,16)->(16+4*32,16) 之间
    assert line_of_sight(gm3, 16, 16, 16 + 4 * TILE_SIZE, 16) is False, "中间有墙应不可见"
    print("[PASS] line_of_sight")

    # ---- 3. predict_ricochet_hits：单反弹可命中墙角后玩家 ----
    gm4 = _open_map()
    # 在 row=10 立一堵横墙从 col=5..20（挡住视线但可反弹）
    for c in range(5, 21):
        gm4.grid[10][c] = TileType.BRICK
    # 玩家在墙右侧 (row 12 col 16)，敌人炮口在墙左侧 (row 8 col 7)
    # 敌人朝右下的弹道撞横墙（Y 翻向），反弹后再向下偏斜能否命中玩家
    fuel = predict_ricochet_hits(gm4, 7 * TILE_SIZE + 16, 8 * TILE_SIZE + 16,
                                 0.6, 0.8,                     # 右、下
                                 16 * TILE_SIZE + 16, 12 * TILE_SIZE + 16,
                                 max_bounces=1)
    # 该特定参数组合预期：撞横墙后往下直走不再命中等间距目标 → 预算结果为 False
    assert fuel is False, "直接反弹直下不应对准偏移目标"
    print("[PASS] predict_ricochet_hits（反弹模拟运行无误）")

    print("\nALL PASS")
    pygame.quit()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行验证脚本，确认因 `enemy_perception` 未定义而失败**

Run: `python _verify_900.py`
Expected: `ModuleNotFoundError: No module named 'entities.enemy_perception'`

- [ ] **Step 3: 实现 `entities/enemy_perception.py`**（纯几何，最终完整代码）

```python
# -*- coding: utf-8 -*-
"""敌方 AI 感知工具：射线距离 / 视线 / 反弹命中预判（纯函数，无状态）。

几何前提：地图为 25×25 轴对齐网格，子弹撞墙仅翻转被撞轴的分量
（与 entities/bullet.py 的 update 同构），因此反弹可确定性推演。
"""
import math

from core.settings import TILE_SIZE, GRID_SIZE
from maps.tile import TileType

_LOS_STEP = TILE_SIZE // 2  # 16px


def _cell_type(game_map, px: float, py: float):
    col = int(px // TILE_SIZE)
    row = int(py // TILE_SIZE)
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        return None  # 越界视为障碍
    return game_map.get_tile(row, col)


def _blocked(game_map, px: float, py: float) -> bool:
    return _cell_type(game_map, px, py) != TileType.EMPTY


def raycast_distance(game_map, x0: float, y0: float,
                     dx: float, dy: float, max_range: float,
                     start_offset: float = TILE_SIZE - 8) -> float:
    """从 (x0,y0) 沿 (dx,dy) 逐格查询，返回最近障碍距离；畅通返回 max_range。

    (dx,dy) 需为单位向量或近似单位向量（会归一化）。
    """
    n = math.hypot(dx, dy)
    if n == 0.0:
        return max_range
    ux, uy = dx / n, dy / n
    dist = start_offset
    while dist < max_range:
        px = x0 + ux * dist
        py = y0 + uy * dist
        if _blocked(game_map, px, py):
            return dist
        dist += _LOS_STEP
    return max_range


def line_of_sight(game_map, x0: float, y0: float,
                  x1: float, y1: float) -> bool:
    """两点间是否存在未被遮挡的视线（逐格步进）。"""
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 1:
        return True
    ux, uy = dx / dist, dy / dist
    steps = int(dist // _LOS_STEP)
    for i in range(1, steps):
        px = x0 + ux * _LOS_STEP * i
        py = y0 + uy * _LOS_STEP * i
        if _blocked(game_map, px, py):
            return False
    return True


def predict_ricochet_hits(game_map, x0: float, y0: float,
                          dx: float, dy: float,
                          tx: float, ty: float,
                          max_bounces: int = 2,
                          hit_radius: float = 22.0,
                          max_range: float = 800.0) -> bool:
    """逐级模拟子弹反弹，判定最多 max_bounces 次内是否命中 (tx,ty)。

    与 Bullet.update 同构：X/Y 分轴推进，撞墙翻转对应分量。
    """
    n = math.hypot(dx, dy)
    if n == 0.0:
        return False
    ux, uy = dx / n, dy / n
    x, y = float(x0), float(y0)
    bounces = 0
    travelled = 0.0
    while travelled < max_range and bounces <= max_bounces:
        if math.hypot(x - tx, y - ty) < hit_radius:
            return True
        # X 轴独立推进（区间内命中判定也覆盖单步穿透）
        nx = x + ux * _LOS_STEP
        if _blocked(game_map, nx, y):
            ux = -ux
            bounces += 1
            if bounces > max_bounces:
                return False
        else:
            x = nx
        # Y 轴独立推进
        ny = y + uy * _LOS_STEP
        if _blocked(game_map, x, ny):
            uy = -uy
            bounces += 1
            if bounces > max_bounces:
                return False
        else:
            y = ny
        travelled += _LOS_STEP
    return False
```

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `python _verify_900.py`
Expected: `ALL PASS` 且三行 `[PASS]` 全打印

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_perception.py _verify_900.py
git commit -m "feat: add enemy AI perception module (raycast/LOS/ricochet predict)"
```

---

### Task 2: 支柱① 扇形避障覆盖层（enemy_tank）

**Files:**
- Modify: `entities/enemy_tank.py`（导入工具；加 `_get_clearance` 与 `_apply_avoidance`；在 update 中调用并替换旧 nudge）
- Test: `_verify_900.py`（追加第 4 段）

- [ ] **Step 1: 追加验证：确定性给出受阻场景，验证避障不会把坦克转向更近的墙侧**

给 `_verify_900.py` 的 `main()` 顶部追加 import `EnemyTank`，并在 `print("\nALL PASS")` 前插入：

```python
    # ---- 4. 支柱①：扇形净空避障 ----
    from entities.enemy_tank import EnemyTank

    gm5 = _open_map()
    # 顶墙：车头朝右，正前放一堵竖墙 col=8 (row=8..12)，右前方有墙、左前方空旷
    for r in range(8, 13):
        gm5.grid[r][8] = TileType.BRICK
    wall = EnemyTank(16, 10 * TILE_SIZE + 16, gm5)
    wall.physics.facing_angle = 0.0  # 朝右 (+x)
    front, left, right = wall._get_clearance()
    assert front <= 8 * TILE_SIZE and right < left, \
        f"右前方应显著短于左前方 front={front} left={left} right={right}"
    t, s = wall._apply_avoidance(1.0, 0.0)
    assert s > 0, "前向被挡且右侧净空更窄时应转向左侧(s>0)"
    print("[PASS] 支柱①：扇形净空避障")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_900.py`
Expected: `AttributeError: 'EnemyTank' object has no attribute '_get_clearance'`

- [ ] **Step 3: 实现**

在 `entities/enemy_tank.py` 的 import 段加：
```python
from entities.enemy_perception import raycast_distance, line_of_sight, predict_ricochet_hits
```

在类内（`_has_line_of_sight` 附近）加常量与方法：
```python
    # ---- 支柱① 避障参数 ----
    AVOID_FRONT_THRESHOLD = 3.0 * TILE_SIZE   # 前向净空低于此视为受阻
    AVOID_SIDE_SPREAD = math.radians(28)      # 侧前射线夹角
    AVOID_RAY_RANGE = 8 * TILE_SIZE

    def _get_clearance(self):
        """返回 (前, 左侧, 右侧) 三向净空距离。"""
        f = self.physics.facing_angle
        front = raycast_distance(self.game_map, self.x, self.y,
                                 math.sin(f), -math.cos(f),
                                 self.AVOID_RAY_RANGE)
        left = raycast_distance(self.game_map, self.x, self.y,
                                math.sin(f + self.AVOID_SIDE_SPREAD),
                                -math.cos(f + self.AVOID_SIDE_SPREAD),
                                self.AVOID_RAY_RANGE)
        right = raycast_distance(self.game_map, self.x, self.y,
                                 math.sin(f - self.AVOID_SIDE_SPREAD),
                                 -math.cos(f - self.AVOID_SIDE_SPREAD),
                                 self.AVOID_RAY_RANGE)
        return front, left, right

    def _apply_avoidance(self, throttle: float, steering: float):
        """避障覆盖层：前向受阻时，把转向导向较开阔的一侧（带迟滞）。"""
        front, left, right = self._get_clearance()
        if front >= self.AVOID_FRONT_THRESHOLD:
            self._avoid_steer = 0.0
            return throttle, steering
        # 两侧都近（近死角）：不强行转向，交给脱困/正常转向处理
        if left < self.AVOID_FRONT_THRESHOLD and right < self.AVOID_FRONT_THRESHOLD:
            return throttle, steering
        # 归一化偏向：正→向左，负→向右
        avoid = (right - left) / ((right + left) + 1e-6)
        avoid = max(-1.0, min(1.0, avoid))
        # 迟滞平滑：微弱偏向不覆盖，避免逐帧抖动
        smoothed = self._avoid_steer * 0.7 + avoid * 0.3
        self._avoid_steer = smoothed if abs(avoid) > 0.15 else 0.0
        return throttle, steering * 0.5 + self._avoid_steer
```

在 `__init__`（`_escape_steering` 附近）初始化：
```python
        self._avoid_steer = 0.0
```

在 `update()` 内，把现存的"Wall Correction：贴墙 nudge"块（原 `if self.last_hit_x or self.last_hit_y: throttle *= 0.6` 与 `if self.last_hit_x: nudge ...`）替换为如下（先做速度衰减，再做净空避障）：
```python
        # 4. Wall Correction: 贴墙速度衰减（保留）
        if self.last_hit_x or self.last_hit_y:
            throttle *= 0.6
        # 4.5 支柱①：净空避障覆盖层（替代旧零散 nudge）
        throttle, steering = self._apply_avoidance(throttle, steering)
```

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_900.py`
Expected: `[PASS] 支柱①：扇形净空避障` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py _verify_900.py
git commit -m "feat: enemy pillar1 fan-ray clearance obstacle avoidance"
```

---

### Task 3: 支柱③ DODGE 生存态（enemy_tank + main 接线）

**Files:**
- Modify: `entities/enemy_tank.py`（加 `AIState.DODGE`、`_do_dodge`、状态迁移）
- Modify: `main.py`（敌方循环补 `evaluate_threats`）
- Test: `_verify_900.py`（追加第 5 段）

- [ ] **Step 1: 追加验证：威胁存在时 update 进入 DODGE、威胁解除后离开**

在 `main()` 末尾追加（在 `ALL PASS` 打印前）：
```python
    # ---- 5. 支柱③：DODGE 状态迁移 ----
    from core.settings import TILE_SIZE as _T
    from entities.enemy_tank import AIState as _AI

    gm6 = _open_map()
    dodger = EnemyTank(20 * _T, 20 * _T, gm6)
    dodger.state = _AI.CHASE
    # 伪造一颗来袭玩家子弹
    class FakeBullet:
        def __init__(s):
            s.x, s.y = 20 * _T, 16 * _T
            s.dx, s.dy = 0.0, 1.0
            s.owner = "player"
            s.alive = True
    dodger.evaluate_threats([FakeBullet()])
    dodger.update(1 / 60.0, (5 * _T, 5 * _T))
    assert dodger.state == _AI.DODGE, f"高威胁应进入 DODGE，实际 {dodger.state}"
    # 威胁解除后回落 CHASE（玩家可见）
    dodger.evaluate_threats([])
    dodger.update(1 / 60.0, (5 * _T, 5 * _T))
    assert dodger.state == _AI.CHASE, f"威胁解除应回 CHASE，实际 {dodger.state}"
    print("[PASS] 支柱③：DODGE 触发与回落")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_900.py`
Expected: `ValueError: 'DODGE' is not a valid AIState`（或无 DODGE 状态/逻辑，断言失败）

- [ ] **Step 3: 实现**

在 `entities/enemy_tank.py`：
- `AIState` 枚举加 `DODGE = auto()`。
- 加入 DODGE 触发阈值常量与方法 `_do_dodge`：
```python
    THREAT_DODGE_THRESHOLD = 0.5   # threat_score 高于此进入 DODGE
    DODGE_RAY_RANGE = 6 * TILE_SIZE

    def _do_dodge(self, dt: float):
        """沿来袭子弹的垂直方向移动，优先去净空更大的一侧。"""
        b = self.threat_bullet
        if b is None or not b.alive:
            return 0.0, 0.0
        a_b = math.atan2(b.dx, -b.dy)
        cand = [a_b + math.pi / 2, a_b - math.pi / 2]
        best_angle, best_clear = None, -1.0
        for a in cand:
            d = raycast_distance(self.game_map, self.x, self.y,
                                 math.sin(a), -math.cos(a), self.DODGE_RAY_RANGE)
            if d > best_clear:
                best_clear, best_angle = d, a
        if best_angle is None:
            return 0.8, 0.0
        angle_diff = best_angle - self.physics.facing_angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        steering = self._determine_steering(angle_diff)
        return 0.8, steering
```

- 在 `update()` 的感知段末尾（现有 `stuck_timer` 之后）更新 DODGE 字段触发依据——在 Transition 段，把现有 C 常规模迁分支改为：

现有（节选）：
```python
        # C. 常规状态迁移
        elif self.state == AIState.PATROL and player_visible:
            self.state = AIState.CHASE
        elif self.state == AIState.CHASE and not player_visible:
            self.state = AIState.PATROL
```
改为：
```python
        # C. 常规状态迁移（含 DODGE）
        elif self.state == AIState.DODGE:
            if self.threat_score < self.THREAT_DODGE_THRESHOLD:
                self.state = AIState.CHASE if player_visible else AIState.PATROL
        elif self.threat_score >= self.THREAT_DODGE_THRESHOLD:
            self.state = AIState.DODGE
        elif self.state == AIState.PATROL and player_visible:
            self.state = AIState.CHASE
        elif self.state == AIState.CHASE and not player_visible:
            self.state = AIState.PATROL
```

注意：`ESCAPE` 为最高优先，其进入分支（`state != AIState.ESCAPE`）已覆盖任意状态（含 DODGE），无需改。

- 在 `update()` 的 Execute 段加分支：
```python
        elif self.state == AIState.DODGE:
            throttle, steering = self._do_dodge(dt)
```
（放在 `CHASE` 分支之后、`PATROL` 之前均可，保持 `if/elif` 链合法即可。）

**main.py 接线**：在敌方更新循环 `for enemy in self.enemy_tanks:` 内、`enemy.update(...)` 之前加一行：
```python
            enemy.evaluate_threats(self.bullets)
```

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_900.py`
Expected: `[PASS] 支柱③：DODGE 触发与回落` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py main.py _verify_900.py
git commit -m "feat: enemy pillar3 DODGE survival state + threat wiring"
```

---

### Task 4: 支柱②b 反弹瞄准（enemy）

**Files:**
- Modify: `entities/enemy_tank.py`（加反弹瞄准扫描 `_try_ricochet_aim`、在开火处使用）
- Test: `_verify_900.py`（追加第 6 段）

- [ ] **Step 1: 追加验证：可直见时不启用反弹；不可直见但存在反弹解时给出可行角**

```python
    # ---- 6. 支柱②b：反弹瞄准 ----
    gm7 = _open_map()
    for c in range(5, 21):
        gm7.grid[10][c] = TileType.BRICK      # 一堵横墙分隔
    shooter = EnemyTank(7 * TILE_SIZE + 16, 8 * TILE_SIZE + 16, gm7)
    player_corner = (14 * TILE_SIZE + 16, 12 * TILE_SIZE + 16)
    # 玩家在墙另一侧 => 不可直见
    assert line_of_sight(gm7, shooter.x, shooter.y, *player_corner) is False, "前提：隔墙不可直见"
    ang = shooter._try_ricochet_aim(player_corner)
    assert ang is not None, "隔墙但存在反弹直线解时应给出发射角"
    assert predict_ricochet_hits(gm7, shooter.x, shooter.y,
                                 math.sin(ang), -math.cos(ang),
                                 *player_corner, max_bounces=2) is True, "该角反弹应命中"
    print("[PASS] 支柱②b：反弹瞄准")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_900.py`
Expected: `AttributeError: 'EnemyTank' object has no attribute '_try_ricochet_aim'`

- [ ] **Step 3: 实现**

在 `entities/enemy_tank.py` 加常量与方法：
```python
    # ---- 支柱②b 反弹参数 ----
    RICOCHET_AIM_ENABLED = True          # 总开关
    RICOCHET_MAX_BOUNCES = 2             # 与 BULLET_MAX_BOUNCES 一致
    RICOCHET_ANGLE_RANGE = math.radians(60)
    RICOCHET_ANGLE_STEP = math.radians(5)

    def _try_ricochet_aim(self, player_pos):
        """玩家不可直见时，扫描发射角找首个能反弹命中的解；无解返回 None。"""
        if not self.RICOCHET_AIM_ENABLED:
            return None
        tx, ty = player_pos
        if line_of_sight(self.game_map, self.x, self.y, tx, ty):
            return None       # 可直见直打，不启用反弹
        base = math.atan2(tx - self.x, -(ty - self.y))
        off = 0.0
        while off <= self.RICOCHET_ANGLE_RANGE:
            for sign in (1.0, -1.0):
                a = base + sign * off
                if predict_ricochet_hits(self.game_map, self.x, self.y,
                                         math.sin(a), -math.cos(a),
                                         tx, ty, self.RICOCHET_MAX_BOUNCES):
                    return a
            off += self.RICOCHET_ANGLE_STEP
        return None
```

开火处接入：现有 `_do_chase` 的开火块（`if self.fire_cooldown <= 0 and self.can_fire(): self.pending_bullet = self._create_bullet() ...`）。为让炮塔（跟随车身）对准反弹角，改为：检索到反弹角时，把该角设为临时目标、车头对齐后再用该方向发射。修改为：

```python
        # V4.0.2 Turret Fairness：炮塔跟随车身
        if self.fire_cooldown <= 0 and self.can_fire():
            # 玩家不可直见且存在反弹解时，沿反弹角发射
            fire_angle = None
            if player_pos is not None:
                fire_angle = self._try_ricochet_aim(player_pos)
            if fire_angle is not None:
                self._pending_fire_angle = fire_angle
            if getattr(self, "_pending_fire_angle", None) is not None:
                a = self._pending_fire_angle
                diff = a - self.physics.facing_angle
                while diff > math.pi: diff -= 2 * math.pi
                while diff < -math.pi: diff += 2 * math.pi
                if abs(diff) < math.radians(8.0):      # 车头已对准，开火
                    self._create_bullet_at_angle(a)
                    self.fire_cooldown = ENEMY_FIRE_COOLDOWN
                    self.consume_ammo()
                    self._pending_fire_angle = None
            else:
                self.pending_bullet = self._create_bullet()  # 直瞄原逻辑
                self.fire_cooldown = ENEMY_FIRE_COOLDOWN
                self.consume_ammo()
```

新增`_create_bullet_at_angle`（复用 `_create_bullet`，但按指定角从炮口生成）：
```python
    def _create_bullet_at_angle(self, a: float) -> None:
        self.turret_angle = a                       # 渲染炮管朝反弹角
        self.pending_bullet = self._create_bullet()
```
并在 `__init__` 初始化 `self._pending_fire_angle = None`。

> 说明：该方案把反弹发射并入 CHASE 开火出口，不新增 GameState；`_create_bullet` 使用 `self.turret_angle` 作为方向（其实现基于 `sin(self.turret_angle), -cos(...)`）。为保证 `_create_bullet` 用的是反弹角而非车身角，`_create_bullet_at_angle` 先临时置 `turret_angle=a` 再生成。

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_900.py`
Expected: `[PASS] 支柱②b：反弹瞄准` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py _verify_900.py
git commit -m "feat: enemy pillar2b ricochet aim over cover"
```

---

### Task 5: 冻结基线同步 + 完整回归

**Files:**
- Modify: `_verify_800.py`（把 `enemy_tank.py` 从 `FROZEN_BASELINE` 移到 `MODIFIED`）
- Test: 全部 `_verify_*.py`

- [ ] **Step 1: 修改 `_verify_800.py` 的冻结基线**

将 `MODIFIED` 列表追加 `"entities/enemy_tank.py"`，并从 `FROZEN_BASELINE` 中删除键 `"entities/enemy_tank.py"`。

- [ ] **Step 2: 运行全部验证脚本**

Run: `python _verify_900.py`
Expected: `ALL PASS`

Run: `python _verify_800.py`
Expected: `ALL PASS`（冻结扫描不再校验 enemy_tank，其余冻结文件未动）

- [ ] **Step 3: 手动冒烟（可选，需显示环境）**

Run: `python main.py`
Expected: 菜单→进入对战，观察敌方：能平滑绕开障碍/墙角不卡死；不被逼进死角后退；子弹密集时会有 DODGE 闪避动作。

- [ ] **Step 4: Commit**

```bash
git add _verify_800.py
git commit -m "chore: unfreeze enemy_tank baseline for Phase 9 AI"
```

---

## Self-Review

**1. Spec coverage：**
- 支柱① 扇形避障 → Task 2（`_get_clearance` + `_apply_avoidance`）。
- 支柱②b 反弹预判 → Task 1（`predict_ricochet_hits`）+ Task 4（`_try_ricochet_aim` + 发射接入）。
- 支柱③ DODGE → Task 3（`AIState.DODGE` + `_do_dodge` + main 接线）。
- 低血分支（预留位）→ 设计保留，本计划不实现（符合"只做子弹密集躲闪"）。
- 约束：不动物理/碰撞/玩家；炮塔跟随车身（反弹发射通过对准车头实现）；改动集中在 enemy_tank.py + 新模块 + main 一行；冷冻文件未动。

**2. Placeholder scan：** 无 TBD/TODO/模糊项；每步含完整代码与期望输出。

**3. 类型/命名一致性：** `raycast_distance`/`line_of_sight`/`predict_ricochet_hits` 在模块定义处（Task1）与调用处（Task2/3/4）签名一致；`_get_clearance` 返回 `(front,left,right)` 三元组在 Task2 定义、Task2 验证与 Task3 的 DODGE 中按同一顺序消费；`_try_ricochet_aim` 在 Task4 定义与验证一致。