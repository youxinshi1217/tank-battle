# 敌方 AI 行为层升级（SEARCH 分阶段搜索 + 环绕攻击 + 战斗风格 + 多策略拉扯）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 目标从"战术型坦克 AI"改为——**模拟一个会玩坦克小游戏的人类玩家：会寻找、骚扰、绕圈、拉扯、抓机会，而不是占据固定战略点**。落地四块：SEARCH 分阶段搜索（最高优先级）、环绕攻击（核心）、CHASE 多策略拉扯、战斗风格概率驱动 + 战术点降权为临时利用。

**优先级排序（用户确认）：** Tier1 = SEARCH / CHASE 多策略 / 环绕攻击；Tier2 = 战斗风格概率 / 随机决策；Tier3 = 战术点（降权，从"导航目标"改为"路过临时利用"，不做站桩）。

**Architecture:** 纯数据与纯几何拆到独立模块：`entities/enemy_combat_profile.py`（战斗风格表 + 概率 + SEARCH 配置）。`entities/enemy_tank.py` 消费：新增 `SEARCH` 状态（分阶段搜索记忆）、`_orbit_goal` 环绕数学、CHASE 内按战斗风格概率抽取策略（pursue/orbit/kite/retreat）、战术点降权为巡逻时临时掩体利用。`main.py` 不改（EnemyTank 内部自动抽取战斗风格）。所有阈值/概率进 `xxxConfig` 表，逻辑零硬编码。

**Tech Stack:** Python 3.14 + pygame；沿用 `_verify_XXX.py` headless（SDL dummy）断言脚本验证；改动集中在 `enemy_tank.py` + 一个新模块 + 各验证脚本，冷冻文件一律不动。

**约束（不可破坏）：**
- 冷冻文件（`entities/player_tank.py`、`core/collision.py`、`core/tank_physics.py`、`entities/bullet.py`、`maps/game_map.py` 等）字节级不得改动。
- 炮塔必须跟随车身：任何朝特定角开火的意图都只能通过转车身实现。
- 不新增 GameState；SEARCH 为最高意图层，但 ESCAPE（脱困）/DODGE（生存）仍为硬性安全覆盖（蛇口逃生优先于搜索），不破坏既有脱困/Dodge。
- 战术点系统必须有回退开关（`TACTICAL_SYSTEM_ENABLED`），关闭后仅失去临时掩体利用，SEARCH/多策略/环绕不受影响。
- 转向介入一律带迟滞/死区，避免 ±18° 振荡。

---

## 文件结构

- **Create** `entities/enemy_combat_profile.py`：战斗风格 + 拉取概率 + 风格参数 + SEARCH/交火配置（纯数据，可独立测试）。
- **Modify** `entities/enemy_tank.py`：加 `SEARCH` 状态 + 分阶段搜索；`combat_style` 属性；环绕攻击 `_orbit_goal`；CHASE 多策略分发（pursue/orbit/kite/retreat）；巡逻时临时掩体利用；交火偏向 gating。
- **Create** `_verify_910.py`（风格表）、`_verify_911.py`（SEARCH 分阶段）、`_verify_912.py`（环绕数学）、`_verify_913.py`（多策略 + 集成 + 降权回退）。
- **Modify** `main.py`：无需改（`EnemyTank.__init__` 内部自动抽风格）；仅确认签名兼容。
- **Modify** `_verify_800.py`：无需改（`enemy_tank.py` 已在 `MODIFIED`；新模块不在冻结扫描内）。

> 注：`enemy_tank.py` 已在 `_verify_800.py` 的 `MODIFIED`（第 42 行），本计划不触碰冻结基线。

---

### Task 1: 战斗风格模块 `enemy_combat_profile.py` + 验证脚本

**Files:**
- Create: `entities/enemy_combat_profile.py`
- Create: `_verify_910.py`
- Test: `_verify_910.py`

- [ ] **Step 1: 建验证脚本（TDD，对不存在模块应失败）**

创建 `_verify_910.py`：

```python
# -*- coding: utf-8 -*-
"""Phase 9.1 冒烟验证：战斗风格表 + 概率抽取。
运行方式：python _verify_910.py（headless），ALL PASS 收尾。"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from entities.enemy_combat_profile import (
    COMBAT_STYLES,
    roll_combat_style,
    tactic_weights,
    style_params,
    engagement_allows,
    SEARCH_TIMEOUT,
)

def main():
    # 1. 风格固定四类（内部英文 ID）
    assert COMBAT_STYLES == ("berserker", "mobile", "trickster", "roamer"), COMBAT_STYLES
    print("[PASS] 战斗风格类型")

    # 1b. 每风格含环绕半径窗口 orbit_radius（min<max），稳定提供差异
    for s in COMBAT_STYLES:
        lo, hi = style_params(s)["orbit_radius"]
        assert lo < hi, (s, lo, hi)
    print("[PASS] orbit 半径按风格分层")

    # 2. 抽取结果必在集合内
    for _ in range(300):
        assert roll_combat_style() in COMBAT_STYLES
    print("[PASS] roll_combat_style 输出合法")

    # 3. 每风格战术权重四键齐全、归一化和≈1.0
    for s in COMBAT_STYLES:
        w = tactic_weights(s)
        assert set(w.keys()) == {"pursue", "orbit", "kite", "retreat"}, w.keys()
        assert abs(sum(w.values()) - 1.0) < 1e-6, (s, sum(w.values()))
    print("[PASS] tactic_weights 结构与归一化")

    # 4. 风格参数含 engage / cover_chance / name，且 engage∈(0,1]
    for s in COMBAT_STYLES:
        p = style_params(s)
        assert all(k in p for k in ("engage", "cover_chance", "name")), p
        assert 0.0 < p["engage"] <= 1.0
        assert 0.0 <= p["cover_chance"] <= 1.0
    print("[PASS] style_params 键齐全且取值合法")

    # 5. 交火偏向右：高 roll 对低 engage 者拒绝；低 roll 对高 engage 者接受（确定性）
    assert engagement_allows("roamer", 0.99) is False, "游走型高 roll 不应交火"
    assert engagement_allows("berserker", 0.01) is True, "狂战型低 roll 应交火"
    print("[PASS] engagement_allows 确定性判断")

    # 6. SEARCH 配置存在且合理
    assert 0 < SEARCH_TIMEOUT
    print("[PASS] SEARCH_TIMEOUT")

    print("\nALL PASS")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_910.py`
Expected: `ModuleNotFoundError: No module named 'entities.enemy_combat_profile'`

- [ ] **Step 3: 实现 `entities/enemy_combat_profile.py`**

```python
# -*- coding: utf-8 -*-
"""敌方 AI 战斗风格系统（纯数据，无 pygame 依赖）。

目标：模拟会玩坦克小游戏的人类玩家——寻找/骚扰/绕圈/拉扯/抓机会，
而非占据固定战略点。本模块只负责"性格/概率/行为参数"的集中表：
  - 战斗风格决定：战术策略抽取概率、交火偏向、临时掩体利用概率。
  - SEARCH 分阶段搜索参数、交火重判间隔。
所有数值集中在表里，逻辑内不硬编码。
"""
import random

# 战斗风格（固定顺序，供遍历）。内部一律英文 ID（方便扩展），中文名仅供 Debug 展示。
COMBAT_STYLES = ("berserker", "mobile", "trickster", "roamer")

# 出生时风格抽取权重（总和归一化）
_SPAWN_WEIGHTS = (0.25, 0.30, 0.25, 0.20)

# 每风格战术策略概率（pursue直追 / orbit环绕 / kite拉扯 / retreat重新找角度）
# 四者和必须等于 1.0（验证脚本检查）
_TACTIC_WEIGHTS = {
    "berserker": {"pursue": 0.70, "orbit": 0.20, "kite": 0.05, "retreat": 0.05},
    "mobile":    {"pursue": 0.30, "orbit": 0.50, "kite": 0.20, "retreat": 0.00},
    "trickster": {"pursue": 0.20, "orbit": 0.35, "kite": 0.35, "retreat": 0.10},
    "roamer":    {"pursue": 0.25, "orbit": 0.25, "kite": 0.15, "retreat": 0.35},
}

# 风格行为参数
#   engage         : 看到玩家时是否"主动扑上去"的概率（游走型低=常犹豫、抓机会突然攻击）
#   close_trigger  : 游走型"抓机会"：玩家距自己 < 此值(px) 会忽略 engage 直接扑（防躲猫猫）
#   reload_trigger : 游走型"抓机会"：玩家正在换弹(ammo=0 在装填)时直接扑
#   cover_chance   : 巡逻时路过掩体临时停顿/绕一下的概率（战术点降权=临时利用）
#   orbit_radius   : 该风格环绕半径窗口 (px)，避免"换皮 AI"（不同风格半径不同）
#   name           : 中文展示名（Debug 头顶字用）
_STYLE_PARAMS = {
    "berserker": {"engage": 0.95, "close_trigger": 60.0, "reload_trigger": True,
                  "cover_chance": 0.05, "orbit_radius": (180.0, 260.0), "name": "狂战"},
    "mobile":    {"engage": 0.90, "close_trigger": 60.0, "reload_trigger": True,
                  "cover_chance": 0.10, "orbit_radius": (220.0, 320.0), "name": "机动"},
    "trickster": {"engage": 0.80, "close_trigger": 80.0, "reload_trigger": True,
                  "cover_chance": 0.25, "orbit_radius": (140.0, 220.0), "name": "狡猾"},
    "roamer":    {"engage": 0.40, "close_trigger": 110.0, "reload_trigger": True,
                  "cover_chance": 0.40, "orbit_radius": (200.0, 300.0), "name": "游走"},
}

# 游走型等低 engage 风格的"抓机会"幅度：距离非常近时也肯定扑（覆盖 close_trigger 之外的兜底）
# 反馈：游走型若不设攻击触发条件，容易变成"全程躲猫猫"拖慢节奏；故加入距离/换弹触发。
ENGAGE_CLOSE_DIST = 90.0

# ---- SEARCH 分阶段搜索参数 ----
SEARCH_TIMEOUT = 8.0             # 总放弃时限（秒）：超过仍找不到 → 回落 PATROL
SEARCH_NEARBY_POINTS = 3         # 第二阶段：最后位置附近随机点数
SEARCH_NEARBY_RADIUS = 2.5 * 32  # 第二阶段半径（px）
SEARCH_EXPAND_POINTS = 2         # 第三阶段：扩大范围随机点数
SEARCH_EXPAND_RADIUS = 6.0 * 32  # 第三阶段半径（px）
SEARCH_SCAN_TIME = 0.8           # 每个搜索点驻留扫描秒数

# 交火偏向重判间隔（秒）：未交火的人每过此间隔在"看到玩家"时重掷一次是否扑上
ENGAGE_RECHECK_INTERVAL = 1.5

def roll_combat_style() -> str:
    """按 SPAWN_WEIGHTS 随机抽一个战斗风格。"""
    return random.choices(COMBAT_STYLES, weights=_SPAWN_WEIGHTS, k=1)[0]

def tactic_weights(style: str) -> dict:
    """返回该风格战术策略概率 dict（pursue/orbit/kite/retreat）。"""
    return dict(_TACTIC_WEIGHTS.get(style, _TACTIC_WEIGHTS["mobile"]))

def style_params(style: str) -> dict:
    """返回该风格行为参数 dict（engage/cover_chance/name）。"""
    return dict(_STYLE_PARAMS.get(style, _STYLE_PARAMS["mobile"]))

def engagement_allows(style: str, roll: float) -> bool:
    """确定性判断：给定随机数 roll，该风格是否扑上（engage 阈值）。"""
    return roll < _STYLE_PARAMS.get(style, _STYLE_PARAMS["mobile"])["engage"]
```

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_910.py`
Expected: 六行 `[PASS]` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_combat_profile.py _verify_910.py
git commit -m "feat: enemy combat profile module (styles / tactics / SEARCH config)"
```

---

### Task 2: SEARCH 分阶段状态 + 最后位置记忆（enemy_tank）

**Files:**
- Modify: `entities/enemy_tank.py`
- Test: `_verify_911.py`

**设计（最高意图层）：**
玩家刚消失（CHASE 失视野）→ 进 `SEARCH`，而非直接回落 PATROL。分四阶段：
1. 最后已知位置；
2. 其附近随机 `SEARCH_NEARBY_POINTS` 个点；
3. 扩大范围再 `SEARCH_EXPAND_POINTS` 个点；
4. 放弃 → PATROL。
搜索点队列进入时构建；每个点 A* 到达后驻留扫描 `SEARCH_SCAN_TIME`；总时长超 `SEARCH_TIMEOUT` 或队列耗尽 → 放弃。重见玩家任何时刻 → 回 CHASE。

- [ ] **Step 1: 建验证脚本**

创建 `_verify_911.py`：

```python
# -*- coding: utf-8 -*-
"""Phase 9.2 冒烟验证：SEARCH 分阶段搜索 + 最后位置记忆。"""
import os, math
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

from maps.game_map import GameMap
from maps.tile import TileType
from core.settings import TILE_SIZE, GRID_SIZE
from entities.enemy_tank import EnemyTank, AIState

def _open():
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    return GameMap.from_map_data(grid, [[False]*GRID_SIZE for _ in range(GRID_SIZE)])

def main():
    gm = _open()
    e = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, gm)
    # 1. 直见保持 CHASE
    e.state = AIState.CHASE
    seen = (12*TILE_SIZE, 8*TILE_SIZE)
    e.update(1/60.0, seen)
    assert e.state == AIState.CHASE
    # 2. 瞬间失视野 → SEARCH 并记住最后位置
    e._last_known_pos = seen
    e.update(1/60.0, None)
    assert e.state == AIState.SEARCH, f"失视野应进 SEARCH，实际 {e.state}"
    assert e._last_known_pos == seen, "应记住最后已知位置"
    # 3. SEARCH 应构建搜索点队列（含最后位置 + 随机点）
    assert e._search_points and e._search_points[0] == seen, "首个搜索点应为最后位置"
    print("[PASS] 失视野进 SEARCH 并建搜索点队列")

    # 4. 搜索中重见玩家 → 回 CHASE
    near = (seen[0] + TILE_SIZE, seen[1])
    e._search_elapsed = 0.0
    e.update(1/60.0, near)
    assert e.state == AIState.CHASE, f"搜索中重见应回 CHASE，实际 {e.state}"
    print("[PASS] 搜索中重见回到 CHASE")

    # 5. 超时未找到 → 回落 PATROL，且释放任何临时占用
    e2 = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, gm)
    e2.state = AIState.SEARCH
    e2._last_known_pos = (14*TILE_SIZE, 14*TILE_SIZE)
    e2._build_search_points()
    e2._search_elapsed = 0.0
    for _ in range(600):
        e2.update(1/60.0, None)
    assert e2.state == AIState.PATROL, f"搜索超时应回落 PATROL，实际 {e2.state}"
    print("[PASS] 搜索超时回落 PATROL")

    print("\nALL PASS")
    pygame.quit()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_911.py`
Expected: `AttributeError: ... has no attribute 'SEARCH'`（或 `_search_points`）

- [ ] **Step 3: 实现**

import 段加风格模块：

```python
from entities import enemy_combat_profile
```

`AIState` 加 `SEARCH`：

```python
class AIState(Enum):
    """AI 行为状态枚举"""
    PATROL = auto()
    CHASE = auto()
    ESCAPE = auto()
    DODGE = auto()
    SEARCH = auto()
```

`__init__` 末尾（`self._aim_jitter` 之后）追加：

```python
        # ---- 战斗风格（出生时自动抽取；表在 enemy_combat_profile）----
        self.combat_style = enemy_combat_profile.roll_combat_style()

        # ---- SEARCH 搜索态：最后位置记忆 / 分阶段搜索队列 ----
        self._last_known_pos = None
        self._search_points = []
        self._search_idx = 0
        self._search_scan = 0.0
        self._search_elapsed = 0.0
        self._search_done = False

        # ---- 交火偏向（看到玩家时按风格决定是否扑上）----
        self._engage_timer = 0.0
        self._player_dist = None          # 玩家距自己（px，用于抓机会触发）
        self._player_reloading = False    # 玩家是否正在换弹

        # ---- 战斗多策略（Task 4 用）：当前战术 & 锁定时长 ----
        self._tactic = "pursue"
        self._tactic_timer = 0.0

        # ---- 战术点临时利用（Task 4 用）----
        self._cover_pause = 0.0
        self._tactical = None
```

新增 SEARCH 方法（`_do_dodge` 之后）：

```python
    def _build_search_points(self) -> None:
        """进入 SEARCH 时构建分阶段搜索点队列。
        阶段1=最后位置 → 阶段2=附近随机 → 阶段3=扩大范围随机。"""
        prof = enemy_combat_profile
        pts = []
        if self._last_known_pos is not None:
            pts.append(self._last_known_pos)
            lx, ly = self._last_known_pos
            for _ in range(prof.SEARCH_NEARBY_POINTS):
                pts.append((lx + random.uniform(-1, 1) * prof.SEARCH_NEARBY_RADIUS,
                            ly + random.uniform(-1, 1) * prof.SEARCH_NEARBY_RADIUS))
            for _ in range(prof.SEARCH_EXPAND_POINTS):
                pts.append((lx + random.uniform(-1, 1) * prof.SEARCH_EXPAND_RADIUS,
                            ly + random.uniform(-1, 1) * prof.SEARCH_EXPAND_RADIUS))
        self._search_points = pts
        self._search_idx = 0
        self._search_scan = 0.0
        self._search_done = False

    def _do_search(self, dt: float) -> tuple:
        """分阶段搜索：沿搜索点队列移动，到点扫描后推进；队列耗尽置 _search_done。"""
        if self._search_done or not self._search_points:
            return 0.0, 0.0
        target = self._search_points[self._search_idx]
        arrive = PatrolConfig["ARRIVE_DIST"] * 1.5
        if math.hypot(target[0] - self.x, target[1] - self.y) > arrive:
            # 前往当前搜索点
            gx, gy = self._move_subgoal(target)
            self._last_subgoal = (gx, gy)
            target_angle = math.atan2(gx - self.x, -(gy - self.y))
        else:
            # 到点扫描：驻留一定时长后推往下一点
            self._search_scan += dt
            swing = math.sin(self._search_scan * 3.0) * math.radians(20)
            target_angle = self.physics.facing_angle + swing
            if self._search_scan >= enemy_combat_profile.SEARCH_SCAN_TIME:
                self._search_idx += 1
                self._search_scan = 0.0
                if self._search_idx >= len(self._search_points):
                    self._search_done = True
                    return 0.0, 0.0
        angle_diff = target_angle - self.physics.facing_angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        steering = self._smooth_steering(angle_diff)
        k = PathConfig["PIVOT_THROTTLE_K"]
        throttle = max(0.0, min(1.0, k * (1.0 - abs(angle_diff) / math.pi)))
        return throttle, steering
```

`update(self, dt, player_pos=None, player_reloading=False)` 感知段追加记忆（`player_visible` 计算之后）：

```python
        if player_pos is not None:
            self._player_dist = math.hypot(player_pos[0] - self.x,
                                           player_pos[1] - self.y)
            self._player_reloading = bool(player_reloading)
            if player_visible:
                self._last_known_pos = (player_pos[0], player_pos[1])
```
> `player_reloading` 由 main 在每帧调 `enemy.update` 时传入（玩家 `reload_remaining>0`）；缺省 False 保持签名向后兼容。

Transition 段 `C. 常规状态迁移` 整体替换（原为 `elif self.state in (AIState.PATROL, AIState.CHASE)` 三段 + DODGE 段）：

```python
        # C. 常规状态迁移（含 SEARCH 最高意图 / DODGE）；ESCAPE 由 B 管理且最高优先，此处不触碰
        elif self.state == AIState.DODGE:
            if self.threat_score < DODGEConfig["THREAT_THRESHOLD"]:
                self.state = AIState.CHASE if player_visible else AIState.PATROL
                self._engage_timer = 0.0
        elif self.threat_score >= DODGEConfig["THREAT_THRESHOLD"]:
            self.state = AIState.DODGE
        elif self.state == AIState.SEARCH:
            if player_visible:
                self.state = AIState.CHASE
                self._engage_timer = 0.0
            else:
                self._search_elapsed += dt
                if self._search_done or self._search_elapsed > enemy_combat_profile.SEARCH_TIMEOUT:
                    self.state = AIState.PATROL
        elif self.state == AIState.CHASE and not player_visible:
            # 失视野：进最高意图 SEARCH（而非立刻回 PATROL）
            self.state = AIState.SEARCH
            self._search_elapsed = 0.0
            self._build_search_points()
        elif self.state == AIState.PATROL and player_visible:
            if self._try_engage():
                self.state = AIState.CHASE
                self._engage_timer = 0.0
```

> `_try_engage()` 在 Task 4 实现；为避免 Task 2 期间 PATROL→CHASE 分支触发到未定义方法，先在本 Task 加最小占位（行为=总是扑上，Task 4 覆盖为按风格概率判断）：
>
> ```python
>     def _try_engage(self) -> bool:
>         """占位：本 Task 先总是扑上，Task 4 覆盖为按战斗风格概率 + 抓机会触发。"""
>         return True
> ```

Execute 段加分支：

```python
        elif self.state == AIState.SEARCH:
            throttle, steering = self._do_search(dt)
```

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_911.py`
Expected: 三行 `[PASS]` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py _verify_911.py
git commit -m "feat: enemy SEARCH staged state with last-position memory"
```

---

### Task 3: 环绕攻击 `_orbit_goal`（enemy_tank）+ 验证脚本

**Files:**
- Modify: `entities/enemy_tank.py`
- Test: `_verify_912.py`

**设计（Tier1 核心）：** AI 不直线追玩家，而是绕一个随机半径（150~250px）、随机角速度、随机顺逆时针环绕；定期翻转方向/重抽半径。行为=对玩家做"切向环绕 + 径向纠偏"，目标点永远在玩家外圈上，配合 A* 移动即实现绕圈拉扯。

- [ ] **Step 1: 建验证脚本**

创建 `_verify_912.py`：

```python
# -*- coding: utf-8 -*-
"""Phase 9.3 冒烟验证：环绕攻击数学模型（纯几何，不依赖更新循环）。"""
import os, math
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from maps.game_map import GameMap
from maps.tile import TileType
from core.settings import TILE_SIZE, GRID_SIZE
from entities.enemy_tank import EnemyTank
from entities.enemy_combat_profile import style_params

def _open():
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    return GameMap.from_map_data(grid, [[False]*GRID_SIZE for _ in range(GRID_SIZE)])

def main():
    gm = _open()
    player = (12*TILE_SIZE, 12*TILE_SIZE)
    enemy = EnemyTank(8*TILE_SIZE, 12*TILE_SIZE, gm)     # 玩家正右方
    enemy.combat_style = "roamer"                        # 用已知风格固定半径窗口
    rlo, rhi = style_params(enemy.combat_style)["orbit_radius"]
    enemy._init_orbit()
    # 1. 环绕目标到玩家距离应落在该风格半径窗口内（含纠偏裕量）
    for _ in range(30):
        gx, gy = enemy._orbit_goal(player)
        d = math.hypot(gx - player[0], gy - player[1])
        assert rlo * 0.6 <= d <= rhi * 1.4, (d, rlo, rhi)
    print("[PASS] 环绕距离落在目标半径窗口")

    # 2. 环绕目标绝不当玩家正前方（有切向分量），否则就不是"绕"而是"冲"
    forward_dot = 0.0
    gx, gy = enemy._orbit_goal(player)
    # 方向：坦克→玩家 单位向量 与 坦克→目标 单位向量 的点积（越小→越侧向）
    px, py = player
    to_player = (px - enemy.x, py - enemy.y)
    lp = math.hypot(*to_player) or 1
    to_goal = (gx - enemy.x, gy - enemy.y)
    lg = math.hypot(*to_goal) or 1
    dot = (to_player[0]/lp)*(to_goal[0]/lg) + (to_player[1]/lp)*(to_goal[1]/lg)
    assert dot < 0.85, f"环绕目标不应几乎正对玩家 dot={dot:.2f}"
    print("[PASS] 环绕目标带切向分量（非直线冲撞）")

    # 3. 翻转方向会改变环绕旋向（_flip_orbit 内部已取反 _orbit_dir，调用方不要再手动翻）
    enemy2 = EnemyTank(8*TILE_SIZE, 12*TILE_SIZE, gm)
    enemy2._init_orbit()
    a1 = math.atan2(enemy2._orbit_goal(player)[1] - player[1],
                    enemy2._orbit_goal(player)[0] - player[0])
    enemy2._flip_orbit()
    a2 = math.atan2(enemy2._orbit_goal(player)[1] - player[1],
                    enemy2._orbit_goal(player)[0] - player[0])
    assert abs(a1 - a2) > 0.5, "翻转后环绕角变化应明显"
    print("[PASS] 翻转改变环绕方向")

    print("\nALL PASS")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_912.py`
Expected: `ImportError: cannot import name 'OrbitConfig'`

- [ ] **Step 3: 实现**

在 `DODGEConfig` 之后加环绕配置表（半径按战斗风格分层，见 `enemy_combat_profile` 的 `orbit_radius`）：

```python
# 模块④：环绕攻击配置（Tier1 核心：不直线追，改绕圈拉扯）
OrbitConfig = {
    "RADIAL_CORRECT_SCALE": 0.25,    # 径向纠偏系数（距差 * 系数 → 走向半径）
    "TANGENT_PX_RANGE": (45.0, 90.0),# 每次切向采样长度范围（px，决定角速度）
    "FLIP_MIN": 2.0,                 # 随机翻转方向的最短间隔
    "FLIP_MAX": 4.0,                 # 随机翻转方向的最长间隔
}
# radius 窗口不在此表：改由 combat_style 决定（style_params()["orbit_radius"]），
# 不同风格半径不同，避免"换皮 AI"。后续若加敌人类型，可再按类型细分。
```

新增方法（`_smooth_steering` 之前）：

```python
    def _init_orbit(self) -> None:
        """初始化环绕状态：半径 / 旋向 / 切向采样长。"""
        lo, hi = style_params(self.combat_style)["orbit_radius"]
        self._orbit_radius = random.uniform(lo, hi)
        self._orbit_dir = random.choice([-1.0, 1.0])
        lo, hi = OrbitConfig["TANGENT_PX_RANGE"]
        self._orbit_tangent = random.uniform(lo, hi)
        self._orbit_flip_timer = random.uniform(OrbitConfig["FLIP_MIN"],
                                                OrbitConfig["FLIP_MAX"])

    def _flip_orbit(self) -> None:
        """翻转环绕方向 / 重抽半径 / 重抽切向采样（打破固定轨迹）。"""
        self._orbit_dir *= -1
        self._orbit_radius = random.uniform(OrbitConfig["RADIUS_MIN"],
                                            OrbitConfig["RADIUS_MAX"])
        lo, hi = OrbitConfig["TANGENT_PX_RANGE"]
        self._orbit_tangent = random.uniform(lo, hi)
        self._orbit_flip_timer = random.uniform(OrbitConfig["FLIP_MIN"],
                                                OrbitConfig["FLIP_MAX"])

    def _orbit_goal(self, player_pos) -> tuple:
        """返回一个"环绕玩家外圈"的目标像素点（含径向纠偏 + 切向采样）。

        数学：目标点 = 玩家中心 + 径向纠偏分量(把距离拉向 _orbit_radius)
               + 切向分量(沿玩家外圈切线走，旋向由 _orbit_dir 决定)。
        目标点在玩家周圈上，配合 A* 移动即形成绕圈拉扯，而非直线追。
        """
        px, py = player_pos
        udx, udy = self.x - px, self.y - py     # 玩家→坦克 方向
        d = math.hypot(udx, udy) or 1.0
        ux, uy = udx / d, udy / d
        tx, ty = -uy, ux                        # 切向单位（与半径垂直）
        radial_err = self._orbit_radius - d      # 当前距离与目标半径之差
        radial_push = radial_err * OrbitConfig["RADIAL_CORRECT_SCALE"]
        radial_push = max(-OrbitConfig["RADIAL_CORRECT_SCALE"] * 250.0,
                          min(OrbitConfig["RADIAL_CORRECT_SCALE"] * 250.0,
                              radial_push))
        gx = px + ux * radial_push + tx * self._orbit_dir * self._orbit_tangent
        gy = py + uy * radial_push + ty * self._orbit_dir * self._orbit_tangent
        return gx, gy
```

> 说明：`_orbit_goal` 逆参考系约定——调用方把 (gx,gy) 交给 `_move_subgoal` 走 A*，再按既有方式算 `target_angle`（与其它分支统一），无需在本方法内处理角度约定。`_do_chase` 的 orbit 分支在 Task 4 接入，并推进 `_orbit_flip_timer` 定期翻转。

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_912.py`
Expected: 三行 `[PASS]` 且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py _verify_912.py
git commit -m "feat: enemy orbit attack math (tangential + radial correction)"
```

---

### Task 4: CHASE 多策略分发 + 交火偏向 + 临时掩体利用（enemy_tank）

**Files:**
- Modify: `entities/enemy_tank.py`
- Test: `_verify_913.py`

**设计：** CHASE 内按风格 `_pick_tactic` 抽取并锁定战术；`_do_chase` 按 `_tactic` 分发：
- `pursue`：直追（玩家远/暴露）。
- `orbit`：环绕攻击——`_init_orbit` 后逐帧 `_orbit_goal`，定期翻转。
- `kite`：拉扯——开炮后退开再接近（贴太近走退避，正常走环绕）。
- `retreat`：重新找角度——走 `_retreat_goal`，不逃跑而是换位。
交火偏向 `_try_engage`（游走型不主动追、突然攻击）。战术点降权为巡逻时临时掩体停顿（`cover_chance`），不做站桩导航。

- [ ] **Step 1: 建验证脚本**

创建 `_verify_913.py`：

```python
# -*- coding: utf-8 -*-
"""Phase 9.4 冒烟验证：CHASE 多策略分发 + 交火偏向 + 临时掩体利用（降权回退）。"""
import os, math
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

from maps.game_map import GameMap
from maps.tile import TileType
from core.settings import TILE_SIZE, GRID_SIZE
from entities.enemy_tank import EnemyTank, AIState
from entities import enemy_combat_profile as prof

def _open():
    grid = [[TileType.EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    return GameMap.from_map_data(grid, [[False]*GRID_SIZE for _ in range(GRID_SIZE)])

def main():
    # 1. 敌人自动获取战斗风格
    e = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, _open())
    assert e.combat_style in ("berserker", "mobile", "sly", "roamer"), e.combat_style
    print("[PASS] 敌人自动获取战斗风格")

    # 2. 进入 CHASE 会抽取并锁定一种战术（必然四选一）
    e2 = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, _open())
    e2.state = AIState.CHASE
    e2._tactic_timer = 0.0          # 强制触发兜底重抽
    e2.update(1/60.0, (10*TILE_SIZE, 8*TILE_SIZE))
    assert e2._tactic in ("pursue", "orbit", "kite", "retreat"), e2._tactic
    assert e2._tactic_timer > 0.0, "重抽后应锁定一段时间"
    print("[PASS] CHASE 内抽取并锁定战术")

    # 3. orbit 战术：目标点保持环绕窗口（模拟多帧不崩）
    e3 = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, _open())
    e3._init_orbit()
    for _ in range(20):
        gx, gy = e3._orbit_goal((12*TILE_SIZE, 12*TILE_SIZE))
        d = math.hypot(gx - 12*TILE_SIZE, gy - 12*TILE_SIZE)
        assert 60.0 <= d <= 420.0, d
    print("[PASS] orbit 多帧目标稳定")

    # 4. 交火偏向确定性：狂战立即扑、游走常犹豫
    assert prof.engagement_allows("berserker", 0.05) is True
    assert prof.engagement_allows("roamer", 0.95) is False
    print("[PASS] 交火偏向确定性")

    # 5. 临时掩体利用：游走型 cover_chance 最高，狂战型最低
    assert prof.style_params("roamer")["cover_chance"] > prof.style_params("berserker")["cover_chance"]
    print("[PASS] 风格掩体利用概率差异化")

    # 6. ESCAPE 仍能覆盖 CHASE（SEARCH 不破坏脱困兜底）
    e4 = EnemyTank(8*TILE_SIZE, 8*TILE_SIZE, _open())
    e4.state = AIState.CHASE
    e4.last_hit_x = True
    e4.last_hit_y = True
    e4.stuck_timer = 2.0
    e4.update(1/60.0, (12*TILE_SIZE, 8*TILE_SIZE))
    assert e4.state == AIState.ESCAPE, f"卡死应进 ESCAPE，实际 {e4.state}"
    print("[PASS] ESCAPE 仍覆盖 CHASE")

    print("\nALL PASS")
    pygame.quit()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_913.py`
Expected: `AssertionError`（`_tactic` 未初始化 / 未抽取等）

- [ ] **Step 3: 实现**

新增战术方法（`_next_waypoint` 附近）：

```python
    def _pick_tactic(self) -> None:
        """按战斗风格概率权重抽取一个战斗战术并锁定。"""
        w = prof_pick_tactic_weights()      # 见下方 helper
        options = list(w.keys())
        probs = [w[k] for k in options]
        self._tactic = random.choices(options, weights=probs, k=1)[0]
        self._tactic_timer = random.uniform(1.5, 2.8)

    def _try_engage(self) -> bool:
        """交火偏向：看到玩家时按风格 engage 概率决定是否扑上（节流重判）。"""
        self._engage_timer -= 0.0
        if self._engage_timer > 0.0:
            return False
        self._engage_timer = prof.ENGAGE_RECHECK_INTERVAL
        return prof.engagement_allows(self.combat_style, random.random())
```

> 为避免与 `enemy_combat_profile.tactic_weights` 重名冲突，改在顶部做别名导入，并令 `_pick_tactic` 只调它：
> 在 import 段加 `from entities.enemy_combat_profile import tactic_weights as profile_tactic_weights`，并定义
> `def prof_pick_tactic_weights(): return profile_tactic_weights(self.combat_style)`——实际实现如下更简单：
> 直接在 `_pick_tactic` 内联 `profile_tactic_weights(self.combat_style)`，不引入 helper。为可读性，实现采用内联：

```python
    def _pick_tactic(self) -> None:
        """按战斗风格概率权重抽取一个战斗战术并锁定。"""
        w = profile_tactic_weights(self.combat_style)
        options = list(w.keys())
        probs = [w[k] for k in options]
        self._tactic = random.choices(options, weights=probs, k=1)[0]
        self._tactic_timer = random.uniform(1.5, 2.8)

    def _try_engage(self) -> bool:
        """交火偏向：看到玩家时按风格 engage 概率决定是否扑上（节流重判）。

        低 engage 风格（游走）在满足"抓机会"条件时忽略概率直接扑：
          - 玩家距自己 < close_trigger（或全局 ENGAGE_CLOSE_DIST）
          - 玩家正在换弹（player_reloading）
        否则游走型容易变成全程躲猫猫、拖慢节奏。
        """
        self._engage_timer -= 0.0
        if self._engage_timer > 0.0:
            return False
        self._engage_timer = prof.ENGAGE_RECHECK_INTERVAL
        if engagement_allows(self.combat_style, random.random()):
            return True
        # 抓机会：近身 或 玩家在换弹 → 直接扑
        close = (self._player_dist is not None)
        if close and self._player_dist < ENGAGE_CLOSE_DIST:
            return True
        sp = prof.style_params(self.combat_style)
        if sp["close_trigger"] and close and self._player_dist < sp["close_trigger"]:
            return True
        if sp.get("reload_trigger") and self._player_reloading:
            return True
        return False
```

> 顶部 import 相应加：
> `from entities import enemy_combat_profile as prof`
> `from entities.enemy_combat_profile import (tactic_weights as profile_tactic_weights, style_params, engagement_allows, ENGAGE_CLOSE_DIST)`.
> `_pick_tactic` 内联用 `profile_tactic_weights`；`_try_engage` 用 `prof.*` / `engagement_allows` / `ENGAGE_CLOSE_DIST`。

`_do_chase` 替换"追/退二分"整段（开火逻辑保留在其顶部不动），改为按 `_tactic` 分发：

```python
        # 战术周期推进：到时重抽
        self._tactic_timer -= dt
        if self._tactic_timer <= 0.0:
            self._pick_tactic()

        dist = math.hypot(dx_to, dy_to)
        if self._tactic == "retreat":
            # 重新找角度：向安全撤离侧换位（非逃跑）
            retreat = self._retreat_goal((tx, ty))
            gx, gy = self._move_subgoal(retreat)
            self._last_subgoal = (gx, gy)
            target_angle = math.atan2(gx - self.x, -(gy - self.y))
        elif self._tactic == "kite":
            # 拉扯：贴太近→退避，否则中距环绕（counter 态保距离）
            if dist < PatrolConfig["CHASE_RETREAT_DIST"] * 1.1:
                retreat = self._retreat_goal((tx, ty))
                gx, gy = self._move_subgoal(retreat)
            else:
                gx, gy = self._move_subgoal(self._orbit_goal((tx, ty)))
            self._last_subgoal = (gx, gy)
            target_angle = math.atan2(gx - self.x, -(gy - self.y))
        elif self._tactic == "orbit":
            # 环绕攻击：绕玩家外圈移动，定期翻转方向/重抽半径
            if not getattr(self, "_orbit_radius", None):
                self._init_orbit()          # 首次进入 orbit 才初始化（半径按风格）
            self._orbit_flip_timer -= dt
            if self._orbit_flip_timer <= 0.0:
                self._flip_orbit()
            gx, gy = self._move_subgoal(self._orbit_goal((tx, ty)))
            self._last_subgoal = (gx, gy)
            target_angle = math.atan2(gx - self.x, -(gy - self.y))
        else:
            # pursue：直追（玩家远/暴露）
            gx, gy = self._move_subgoal((tx, ty))
            self._last_subgoal = (gx, gy)
            target_angle = math.atan2(gx - self.x, -(gy - self.y))
```

公共尾部（拟人偏移 + 避障修正 + 平滑转向 + 急弯枢转）保持原样不动。

`update()` Execute 段最前加 CHASE 战术兜底：

```python
        # 兜底：进入 CHASE 且未初始化战术时抽取
        if self.state == AIState.CHASE and self._tactic_timer <= 0.0:
            self._pick_tactic()
```

`update()` 中，`_try_engage` 已被 Task 2 的 PATROL→CHASE 分支调用（占位已写出此处实现）。

**临时掩体利用（战术点降权）：** 在 `_do_patrol` 中做轻量接入——巡逻选下一个普通航点前，按风格 `cover_chance` 抽一次"临时绕到附近掩体停顿"：

在 `_do_patrol` 开头（`if self._humanize_pause > 0.0` 分支后）追加：

```python
        # 战术点降权：临时掩体利用（不是导航目标，仅路过时偶尔绕一下）
        if self._cover_pause > 0.0:
            self._cover_pause -= dt
            return 0.0, 0.0
```

在 `_do_patrol` 换航点处（`math.hypot(dx, dy) < PatrolConfig["ARRIVE_DIST"]` 块内），在 `self._current_wp = wp` 前注入临时掩体逻辑：

```python
            # （换下一个普通航点前）按风格概率临时绕到掩体点停顿一下
            if style_params(self.combat_style)["cover_chance"] > 0.0 and \
                    random.random() < style_params(self.combat_style)["cover_chance"]:
                self._cover_pause = random.uniform(0.4, 0.9)
                wp = self._nearest_cover_point()
                self._current_wp = wp
                dx = wp[0] - self.x
                dy = wp[1] - self.y
```

新增 `_nearest_cover_point`（环视取最近非墙斜前掩体位，简单实现为沿当前前进方向取一个隐蔽点，无则返回原 wp）：

```python
    def _nearest_cover_point(self) -> tuple:
        """临时掩体位：在当前航点附近取一个空地格（拟"借掩体"。降权用，非占点导航）。"""
        import core.tactical_map as _tm
        tm = _tm.get_tactical_map(self.game_map)
        best, bd = None, None
        for pt in tm.points.get("cover", []):
            d = math.hypot(pt[0] - self.x, pt[1] - self.y)
            if bd is None or d < bd:
                best, bd = pt, d
        return best if best is not None else self._current_wp
```

> 战术点降权要点：不做 `claim/release` 站桩占用，仅作为巡逻时的随机临时停靠；关闭 `TACTICAL_SYSTEM_ENABLED=false` 即完全恢复到普通航点巡逻。这符合用户"从导航目标 → 临时选择"的降权要求。

- [ ] **Step 4: 运行确认通过**

Run: `python _verify_913.py`
Expected: 六组断言全过且 `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add entities/enemy_tank.py _verify_913.py
git commit -m "feat: enemy multi-tactic combat (pursue/orbit/kite/retreat) + engage gating + opportunistic cover"
```

---

### Task 5: main 接线（玩家换弹感知）+ 全量回归 + 行为观察验收

**Files:**
- Modify: `main.py:388`
- Test: `python _verify_910.py` / `_verify_911.py` / `_verify_912.py` / `_verify_913.py` / `_verify_800.py`

- [ ] **Step 1: main 传入玩家换弹状态（供"游走型抓机会"触发）**

现有（节选）：
```python
        for enemy in self.enemy_tanks:
            enemy.evaluate_threats(self.bullets)  # 威胁感知 → DODGE 传感
            enemy.update(dt, self.player_tank.rect.center)
```
改为：
```python
        for enemy in self.enemy_tanks:
            enemy.evaluate_threats(self.bullets)  # 威胁感知 → DODGE 传感
            enemy.update(
                dt,
                self.player_tank.rect.center,
                player_reloading=(self.player_tank.reload_remaining > 0),
            )
```
> `update` 缺省 `player_reloading=False`，兼容其它调用点；此处仅新传该可选参数，不改其余逻辑。

- [ ] **Step 2: 运行单位验证**

Run: `python _verify_910.py` → `ALL PASS`
Run: `python _verify_911.py` → `ALL PASS`
Run: `python _verify_912.py` → `ALL PASS`
Run: `python _verify_913.py` → `ALL PASS`
Expected: 四脚本各自 `ALL PASS`

- [ ] **Step 3: 全量回归**

Run: `python _verify_800.py`
Expected: `ALL PASS`（冻结扫描通过；`enemy_tank.py` 在 `MODIFIED` 白名单，新模块不在冻结内）

- [ ] **Step 4: 行为观察指标（不只验代码状态，验"像不像人"）**

Run: `python main.py`，逐条目测并确认：
1. **SEARCH（最高意图）**：你藏墙后敌人不立刻掉头巡逻，先赶往最后露头位、附近绕、扩大范围找，找不到才回——且整段不超过 SEARCH_TIMEOUT。
2. **orbit 不过冲**：敌人绕圈时 2~4 秒必切换一次顺/逆时针（靠 `_orbit_flip_timer`），不会"朝一个方向无限绕"或"贴着玩家疯狂转圈"。半径因风格不同而变化（狂战近、机动远），不会显得"换皮"。
3. **kite 不无限逃跑**："打一炮退开"后退避会被中距环绕/再接近取代，不会一路退到地图角落消极挂机。
4. **roam 仍会接战**：游走型多数时间在巡逻，但当你靠近（<close_trigger）或换弹时会突然扑上打一下——不会变成全程躲猫猫拖慢节奏。
5. **多人格同局差异明显**：同一局里能凭打法认出"狂战在冲、机动在绕、狡猾在偷枪、游走在游荡"，风格不可混为一谈。
6. **humanize 保留**：敌人仍会到点停顿、瞄偏再修正、偶尔绕远——不做"全程满速+瞬转"的机器人。
7. **临时掩体（降权）**：敌人偶尔躲墙后顿一下再走，而非站桩守点；`TACTICAL_SYSTEM_ENABLED=False` 后该临时利用消失，其余行为照常。

若第 2~4 条观察不达标，调 `OrbitConfig`（FLIP/半径/切向）与 `enemy_combat_profile.py` 的 `engage/close_trigger/orbit_radius`，无需改逻辑。

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: wire player reloading into enemy engage trigger"
```

---

## Self-Review

**1. 新目标覆盖（模拟人类玩家）逐条查：**
- SEARCH（Tier1）→ Task 2（`SEARCH` 状态、`_build_search_points` 分阶段、最高意图、超时放弃）。
- 环绕攻击（Tier1）→ Task 3（`_orbit_goal` / `_init_orbit` / `_flip_orbit`，半径按风格分层）+ Task 4 orbit 分支。
- CHASE 多策略（Tier1）→ Task 4（`_pick_tactic` + `_do_chase` pursue/orbit/kite/retreat 分发）。
- 战斗风格概率（Tier2）→ Task 1（`_TACTIC_WEIGHTS` / `style_params`，英文 ID=berserker/mobile/trickster/roamer）+ Task 4。
- 随机决策（Tier2）→ 环绕随机翻转/半径/切向 + 战术锁定 + 交火偏向重判。
- 战术点降权（Tier3）→ Task 4 `_cover_pause` 临时掩体利用 + `TACTICAL_SYSTEM_ENABLED` 回退（非站桩导航）。
- 游走型"抓机会"触发（防躲猫猫）→ Task 1（`close_trigger`/`reload_trigger`/`ENGAGE_CLOSE_DIST`）+ Task 4 `_try_engage` + Task 5 main 接线玩家换弹。
- humanize 保留（不做满速瞬转机器人）→ 既有 `HumanizeConfig` 不破坏，Task 5 Step 4 纳入观察指标。
- 团队协作（Tier3 预留）→ 本计划不实现，符合"不做战术型"的取舍。
- 既有卡死检测 / LOS 视野 / 急弯枢转 / 外扩 → 保留不破坏（ESCAPE/DODGE 仍硬性覆盖，验证 Task 4 Step 6）。

**2. Placeholder scan：** 每 Task 含完整代码、验证脚本、命令与期望输出；`prof_pick_tactic_weights` 等过渡命名已收敛为内联实现，无未定义引用（顶部别名为 `profile_tactic_weights`，Task 4 已补齐）。

**3. 类型/命名一致性：** `roll_combat_style/tactic_weights/style_params/engagement_allows` 在 Task1 定义、验证与 Task4 调用签名一致；`_orbit_goal/_init_orbit/_flip_orbit` 与 `OrbitConfig` 在 Task3 定义、Task4 orbit/kite 分支消费一致；`_pick_tactic` 在 Task4 定义并被 Task4 兜底调用；`_tactic ∈ {pursue,orbit,kite,retreat}` 常量串在 Task1 权重键、Task4 分支、_verify_913 断言三处一致。

**已确认的存量事实（本计划依赖，勿破坏）：**
- `enemy_tank.py` 已在 `_verify_800.py` 的 `MODIFIED`（无需解冻）。
- `enemy_tank` 现有 import 含 `from core.pathfinding import find_grid_path, cell_center_px, px_to_cell`，`_do_chase` 可直接复用。
- `_move_subgoal/_retreat_goal/_smooth_steering/_avoidance_heading_offset/_nearest_empty_cell` 等既有方法直接复用，不需重写。
- 炮塔跟随车身约束由既有 `update` 末端 `self.turret_angle = self.physics.facing_angle` 保证，本计划不触碰。