# 多人模式（PVP / PvPvE）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:executing-plans 依任务逐项实施。步骤用 `- [ ]` 复选框跟踪进度。

**Goal:** 在既有单人波次玩法之上新增双人 PvPvE 与双人对战（PVP）两大模式，并为单人/PVP/PvPvE 引入统一的"系列赛(N局, 先赢⌈N/2⌉) → 每局 → 局内积分"对局模型。

**Architecture:** 全部改动集中在 Game 层（main.py）与新增纯逻辑模块（core/match_config.py、core/round_manager.py）、P2 子类（entities/player2_tank.py）。不新增 GameState 枚举；局间流转用 Game 层子状态变量。P2 输入通过子类覆写 `handle_input`，不改冻结的 player_tank.py。子弹 owner 取值扩展为 `"p1"/"p2"/"enemy"`，复用既有 Bullet 的 owner 机制（非 `"enemy"` 一律走玩家弹速，零改动 bullet.py）。

**范围修订（评审定稿，2026-08-24）**：
- **PVP 移除"可选中立 AI"**：PVP 为纯 P1 vs P2 对抗，对局数由玩家在菜单选择（5/7/9/11/13，先赢 ⌈N/2⌉），无 AI 生成、无 AI 难度配置。
- **开发顺序：先做 PvPvE（本 plan Task 5），后做 PVP（Task 6）。**
- **PVP 局数口径（复核修正）**：`match_config.PVP_ROUNDS_CHOICES` / `get_win_rounds_from_n` / `RoundManager(rounds=)` 为**通用基础能力**（执行会话已实现并被既有 `_verify_multimode_t5.py` 依赖），**予以保留**；PVP 支持 5/7/9/11/13 局可选（`start_pvp(rounds=5)` 等），菜单展示"打 5 局（三局两胜）"等按钮。

**Tech Stack:** Python 3.14 / pygame。验证用项目既有的 `_verify_*.py` 断言脚本（headless 模式 `SDL_VIDEODRIVER=dummy`），不引入 pytest。

**Spec:** `docs/superpowers/specs/2026-08-23-multiplayer-modes-design.md`

---

## 文件结构

- **新增 `core/match_config.py`**：三模式 × 难度的局数/胜局/友军伤害配置表 + 纯函数推导胜局数。
- **新增 `core/round_manager.py`**：系列赛局次与胜负记账（纯逻辑，无 pygame）。
- **新增 `entities/player2_tank.py`**：`Player2Tank(PlayerTank)`，仅覆写键位。
- **新增 `_verify_multimode_t*.py`**：每任务一个 headless 验证脚本（项目惯例）。
- **修改 `main.py`**：双玩家战斗框架、局制流程、模式分流、子弹归因与碰撞扩展、菜单启用。
- **修改 `core/settings.py`**（可选最小）：补充 P2 键位常量（不强制）。

---

### Task 1: 对局配置表 + 局次管理（纯逻辑层）

**Files:**
- Create: `core/match_config.py`
- Create: `core/round_manager.py`
- Test: `_verify_multimode_t1.py`

- [ ] **Step 1: 写失败验证脚本 `_verify_multimode_t1.py`**

```python
# -*- coding: utf-8 -*-
"""Task1 验证：match_config + round_manager 纯逻辑正确性。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.match_config import get_rounds, get_win_rounds, friendly_fire_enabled
from core.round_manager import RoundManager

# 1) 局数表
assert get_rounds("solo", "简单") == 5
assert get_rounds("solo", "普通") == 5
assert get_rounds("solo", "中等") == 7
assert get_rounds("solo", "困难") == 9
assert get_rounds("pvp", "普通") == 9          # PVP 与难度无关
assert get_rounds("pvpe", "简单") == 5
assert get_rounds("pvpe", "困难") == 9

# 2) 胜局数 = ceil(N/2)
assert get_win_rounds("solo", "简单") == 3
assert get_win_rounds("solo", "中等") == 4
assert get_win_rounds("solo", "困难") == 5
assert get_win_rounds("pvp", "普通") == 5

# 3) 友军伤害仅 PvPvE 开启
assert not friendly_fire_enabled("solo")
assert not friendly_fire_enabled("pvp")
assert friendly_fire_enabled("pvpe")

# RoundManager 记账
rm = RoundManager("pvp", "普通")
assert rm.rounds_total == 9 and rm.win_needed == 5 and rm.current_round == 1
assert not rm.round_over and not rm.match_over
rm.record_round(side_a_win=True)          # P1 赢第 1 局
assert rm.current_round == 2 and rm.side_a_wins == 1
assert not rm.match_over
for _ in range(4):                        # P1 再赢 4 局 -> 5 局达胜局到顶
    rm.record_round(side_a_win=True)
assert rm.match_over and rm.side_a_wins == 5
assert rm.current_round == 5              # 系列在第 5 局提前结束（不需要打到第 9 局）
assert rm.a_win

print("T1 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_multimode_t1.py`
Expected: `ModuleNotFoundError: No module named 'core.match_config'`

- [ ] **Step 3: 实现 `core/match_config.py`**

```python
# -*- coding: utf-8 -*-
"""
多人模式统一对局配置表（纯逻辑层，不依赖 pygame）。

职责：三模式 × 难度的系列赛参数集中于此，杜绝魔法数字散落 Game 层。
  - 系列赛局数 rounds（N）
  - 胜局数 win_rounds = ceil(N/2)（先赢 ⌈N/2⌉ 局者胜全部）
  - 友军伤害开关 friendly_fire（仅 PvPvE 开启）
"""

# 模式 → 难度 → {rounds}
# solo/pvpe 按难度定局数；PVP 局数由玩家在菜单选择（PVP_ROUNDS_CHOICES），
# 下表 pvp 块的 9 仅为兜底默认。
_MATCH_ROUNDS = {
    "solo": {
        "简单": 5,
        "普通": 5,
        "中等": 7,
        "困难": 9,
    },
    "pvp": {
        "简单": 9,
        "普通": 9,
        "中等": 9,
        "困难": 9,
    },
    "pvpe": {
        "简单": 5,
        "普通": 5,
        "中等": 7,
        "困难": 9,
    },
}

_DEFAULT_DIFFICULTY = "普通"

# 各模式 AI 数量上限（锤定：PVP 无中立 AI，均 0；敌方由波次提供）
AI_CAP = {"solo": 0, "pvp": 0, "pvpe": 0}   # PvPvE 的"敌方阵营"由波次流程提供


def get_rounds(mode: str, difficulty: str = None) -> int:
    """系列赛总局数 N。未知难度回退默认档。"""
    table = _MATCH_ROUNDS.get(mode, _MATCH_ROUNDS["solo"])
    return table.get(difficulty or _DEFAULT_DIFFICULTY,
                     table[_DEFAULT_DIFFICULTY])


def get_win_rounds(mode: str, difficulty: str = None) -> int:
    """胜局数 W = ceil(N/2)。先赢 W 局者胜全部。"""
    n = get_rounds(mode, difficulty)
    return (n + 1) // 2


def friendly_fire_enabled(mode: str) -> bool:
    """友军伤害仅 PvPvE 开启。"""
    return mode == "pvpe"


def ai_cap(mode: str) -> int:
    """该模式可加入的 AI 数量上限。"""
    return AI_CAP.get(mode, 0)
```

- [ ] **Step 4: 实现 `core/round_manager.py`**

```python
# -*- coding: utf-8 -*-
"""
系列赛局次管理（纯逻辑层，不依赖 pygame）。

职责（只记账，不做胜负判定）：
  - 当前局号 current_round
  - A/B 两方胜局计数（side_a_wins / side_b_wins）
  - 本局是否已结束 round_over
  - 系列赛是否决出胜负 match_over
  - 单局归属由 Game 层判定后调用 record_round(side_a_win) 记账

判定边界（在 Game 层执行，此处只存账）：
  - match_over = side_a_wins == win_needed 或 side_b_wins == win_needed
"""
from core.match_config import get_rounds, get_win_rounds


class RoundManager:
    """系列赛(N局, 先赢W局)局次记账。"""

    def __init__(self, mode: str, difficulty: str = None):
        self.mode = mode
        self.rounds_total = get_rounds(mode, difficulty)
        self.win_needed = get_win_rounds(mode, difficulty)
        self.current_round = 1
        self.side_a_wins = 0        # solo=玩家 / pvp=P1 / pvpe=友方
        self.side_b_wins = 0        # solo=敌方 / pvp=P2 / pvpe=敌方
        self.round_over = False
        self.match_over = False

    def record_round(self, side_a_win: bool) -> None:
        """结算本局：计入胜方胜局数；若已达胜局数则系列赛结束。

        Args:
            side_a_win: True=side_a 赢本局，False=side_b 赢本局。
        """
        if self.match_over or self.round_over:
            return                      # 幂等：已结算则忽略
        if side_a_win:
            self.side_a_wins += 1
        else:
            self.side_b_wins += 1
        self.round_over = True
        if (self.side_a_wins >= self.win_needed
                or self.side_b_wins >= self.win_needed):
            self.match_over = True
        else:
            self.current_round += 1     # 系列未结束，进入下一局

    @property
    def a_win(self) -> bool:
        """系列赛最终是否由 side_a 获胜（match_over 时才有意义）。"""
        return self.side_a_wins >= self.win_needed

    def reset_for_round(self) -> None:
        """进入下一局前的战场复位（不清胜局账）。Game 层据此重载战场。"""
        self.round_over = False
```

- [ ] **Step 5: 运行验证脚本确认通过**

Run: `python _verify_multimode_t1.py`
Expected: `T1 OK`

- [ ] **Step 6: 提交**（若目录已 `git init` 则执行；否则跳过）

```bash
git add core/match_config.py core/round_manager.py _verify_multimode_t1.py
git commit -m "feat: 多人模式对局配置表与局次记账（纯逻辑层）"
```

---

### Task 2: P2 玩家坦克子类（键位覆写）

**Files:**
- Create: `entities/player2_tank.py`
- Test: `_verify_multimode_t2.py`

- [ ] **Step 1: 写失败验证脚本 `_verify_multimode_t2.py`**

```python
# -*- coding: utf-8 -*-
"""Task2 验证：Player2Tank 方向键+空格映射；继承 P1 基础能力。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame

pygame.init()
from entities.player2_tank import Player2Tank
from maps.game_map import GameMap
from maps import tile as T

# 空地图
g = [[T.TileType.EMPTY for _ in range(25)] for _ in range(25)]
gm = GameMap.from_map_data(g, [[False]*25 for _ in range(25)])

p2 = Player2Tank(100, 100, gm)
assert p2.ammo == 5 and p2.can_fire()

# 方向键：上=前进
keys = pygame.key.get_pressed()
import pygame as _p
class _Keys(dict):
    def __getitem__(self, k): return dict.get(self, k, False)
    def __setitem__(self, k, v): dict.__setitem__(self, k, v)
k = _Keys()
k[pygame.K_UP] = True
p2.handle_input(k, 1/60)
assert p2.physics.vx != 0 or p2.physics.vy != 0, "方向键上应产生位移"

# 左转
p2.physics.vx = 0.0; p2.physics.vy = 0.0
k2 = _Keys(); k2[pygame.K_LEFT] = True
old_a = p2.physics.facing_angle
p2.handle_input(k2, 1/60)
assert p2.physics.facing_angle != old_a, "方向键左应转向"

# 继承能力：弹药消耗
p2.consume_ammo()
assert p2.ammo == 4
# 继承护盾
p2.apply_shield()
assert p2.is_shielded

print("T2 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_multimode_t2.py`
Expected: `ModuleNotFoundError: No module named 'entities.player2_tank'`

- [ ] **Step 3: 实现 `entities/player2_tank.py`**

```python
# -*- coding: utf-8 -*-
"""
玩家 2 坦克（车控模式）—— PVP / PvPvE 的第二位玩家。

仅覆写键位映射：方向键(↑↓=前后油门, ←→=转向) + 空格键(开火由 main 层处理)。
其余（物理/碰撞/弹药/道具/渲染/护盾/尾焰）全部继承 PlayerTank，不触碰冻结文件
player_tank.py。
"""
import pygame
from core.settings import COLOR_PLAYER_OUTLINE
from entities.player_tank import PlayerTank
from maps.game_map import GameMap


# P2 车身主色（区别于 P1 的 COLOR_PLAYER_TANK 红），渲染时轻微偏蓝便于区分
COLOR_P2_TANK = (60, 90, 210)
COLOR_P2_OUTLINE = (10, 10, 60)


class Player2Tank(PlayerTank):
    """P2 坦克：方向键控制，继承 P1 全部能力。"""

    def handle_input(self, keys, dt: float) -> None:
        """车控模式：方向键 ↑↓=油门，←→=转向（与 P1 的 WASD 对称）。"""
        throttle = 0.0
        if keys[pygame.K_UP]:
            throttle = 1.0
        elif keys[pygame.K_DOWN]:
            throttle = -1.0

        steering = 0.0
        if keys[pygame.K_LEFT]:
            steering = -1.0
        if keys[pygame.K_RIGHT]:
            steering = 1.0

        # 与 PlayerTank.handle_input 相同的物理/碰撞流程
        old_x, old_y = self.x, self.y
        self.physics.update_car(dt, throttle, steering)
        self.x = self.physics.x
        self.y = self.physics.y
        self._resolve_collision(old_x, old_y, dt)
        self.angle = self.physics.facing_angle
        self.rect.center = (round(self.x), round(self.y))

    # 覆写渲染配色（其余绘制逻辑完全复用父类）
    def _render_body_colors(self):
        return COLOR_P2_TANK, COLOR_P2_OUTLINE
```

> 说明：父类 `render` 内部直接引用模块常量 `COLOR_PLAYER_TANK/COLOR_PLAYER_OUTLINE`（硬编码在 player_tank.py 渲染方法内），无法通过覆写颜色常量改变外观而不改冻结文件。为满足"可区分 P1/P2"，本任务在子类覆写 `render`，仅替换两处取色，其余复制父类渲染（见下方实现；因父类渲染不拆方法，需整体覆写）。

```python
# -*- coding: utf-8 -*-
"""
玩家 2 坦克（车控模式）—— PVP / PvPvE 的第二位玩家。

仅覆写键位映射：方向键(↑↓=前后油门, ←→=转向) + 空格键(开火由 main 层处理)。
其余（物理/碰撞/弹药/道具/护盾/尾焰）全部继承 PlayerTank。
因父类 render 内硬编码 P1 配色，本子类整体覆写 render 以提供 P2 配色（蓝）。
"""
import math
import pygame
from entities.player_tank import PlayerTank

# P2 车身主色（区别于 P1 的红色），渲染偏蓝便于区分
COLOR_P2_TANK = (60, 90, 210)
COLOR_P2_OUTLINE = (10, 10, 60)


class Player2Tank(PlayerTank):
    """P2 坦克：方向键控制，继承 P1 全部能力。"""

    def handle_input(self, keys, dt: float) -> None:
        """车控模式：方向键 ↑↓=油门，←→=转向（与 P1 的 WASD 对称）。"""
        throttle = 0.0
        if keys[pygame.K_UP]:
            throttle = 1.0
        elif keys[pygame.K_DOWN]:
            throttle = -1.0

        steering = 0.0
        if keys[pygame.K_LEFT]:
            steering = -1.0
        if keys[pygame.K_RIGHT]:
            steering = 1.0

        old_x, old_y = self.x, self.y
        self.physics.update_car(dt, throttle, steering)
        self.x = self.physics.x
        self.y = self.physics.y
        self._resolve_collision(old_x, old_y, dt)
        self.angle = self.physics.facing_angle
        self.rect.center = (round(self.x), round(self.y))

    def render(self, surface: pygame.Surface) -> None:
        """绘制坦克：与父类一致，但车身/描边使用 P2 配色。"""
        self._render_trail(surface)

        outline = max(2, self.rect.width // 10)
        barrel_length = self.rect.width * 0.65
        barrel_thickness = max(5, self.rect.width // 4)
        turret_radius = self.rect.width * 0.42

        canvas_size = int(self.rect.width + barrel_length * 2 + outline * 2)
        canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        ccx, ccy = canvas_size // 2, canvas_size // 2

        body_outer = pygame.Rect(0, 0, self.rect.width, self.rect.width)
        body_outer.center = (ccx, ccy)
        pygame.draw.rect(canvas, COLOR_P2_OUTLINE, body_outer)
        body_inner = body_outer.inflate(-outline * 2, -outline * 2)
        pygame.draw.rect(canvas, COLOR_P2_TANK, body_inner)

        barrel_rect = pygame.Rect(0, 0, barrel_thickness, int(barrel_length))
        barrel_rect.centerx = ccx
        barrel_rect.bottom = ccy
        pygame.draw.rect(canvas, COLOR_P2_OUTLINE, barrel_rect)
        pygame.draw.rect(canvas, COLOR_P2_TANK, barrel_rect.inflate(-outline, 0))

        pygame.draw.circle(canvas, COLOR_P2_OUTLINE, (ccx, ccy), int(turret_radius))
        pygame.draw.circle(canvas, COLOR_P2_TANK, (ccx, ccy), int(turret_radius - outline))

        rotated = pygame.transform.rotate(canvas, -math.degrees(self.angle))
        rotated_rect = rotated.get_rect(center=self.rect.center)
        surface.blit(rotated, rotated_rect)

        # 护盾光圈（与父类一致）
        if self.is_shielded:
            ring_radius = int(self.rect.width * 0.9)
            ring_rect = pygame.Rect(0, 0, ring_radius * 2, ring_radius * 2)
            ring_rect.center = self.rect.center
            pulse = 1.0
            shield_layer = pygame.Surface(ring_rect.size, pygame.SRCALPHA)
            ring_alpha = int(255 * pulse)
            pygame.draw.ellipse(shield_layer, (80, 160, 255, ring_alpha),
                                shield_layer.get_rect(),
                                max(2, self.rect.width // 12))
            surface.blit(shield_layer, ring_rect)
```

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `python _verify_multimode_t2.py`
Expected: `T2 OK`

- [ ] **Step 5: 提交**（若 git 已初始化）

```bash
git add entities/player2_tank.py _verify_multimode_t2.py
git commit -m "feat: 新增 P2 玩家坦克子类（方向键+空格，P2 配色）"
```

---

### Task 3: main.py 双玩家战斗框架（P1+P2 同场，共用地基）

> 本任务只把"双玩家能同场移动/开火/被子弹判定"落进 main.py，作为 PVP/PvPvE 共用地基；模式开关此时仍关闭，单人不受影响。

**Files:**
- Modify: `main.py`
- Test: `_verify_multimode_t3.py`

- [ ] **Step 1: 写失败验证脚本 `_verify_multimode_t3.py`**

```python
# -*- coding: utf-8 -*-
"""Task3 验证：双玩家战斗框架 —— owner 归因 + 敌方子弹双判。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
from core.game_state import GameState

game = M.Game()
# 进入 PVP 双玩家骨架：手动注入 player2
from entities.player2_tank import Player2Tank
game.player2_tank = Player2Tank(400, 400, game.game_map)

# 1) 开火归因：模拟 P1/P2 开火 -> owner 正确（每玩家独立冷却，P2 冷却不受 P1 影响）
game._try_fire_for(game.player_tank, "p1")
assert game.bullets and game.bullets[-1].owner == "p1"
game._try_fire_for(game.player2_tank, "p2")   # P2 无冷却，应直接开火
assert game.bullets[-1].owner == "p2"
assert game._get_cooldown("p1") > 0 and game._get_cooldown("p2") > 0

# 2) 敌方子弹双判：P2 位置放一颗敌弹 -> 应命中
from entities.bullet import Bullet
bx, by = game.player2_tank.rect.center
enemy_bullet = Bullet(bx, by, 0.0, 1.0, game.game_map, owner="enemy")
game.bullets.append(enemy_bullet)
hit = game._check_enemy_bullet_hit(enemy_bullet)
assert hit is game.player2_tank, "敌弹应命中 P2"
game.bullets.remove(enemy_bullet)

# 3) 霰弹 owner 赋值
game._fire_shotgun_for(game.player_tank, "p1")
pellets = [b for b in game.bullets if getattr(b, "owner", None) == "p1"]
assert pellets, "霰弹弹丸应带 p1 owner"

print("T3 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_multimode_t3.py`
Expected: `AttributeError: 'Game' object has no attribute '_try_fire_for'`

- [ ] **Step 3: 修改 `main.py` —— 拆分开火方法 + 双玩家结构**

在 `_new_combat()` 中（置于 `self.player_tank = None` 之后，随每次战斗/reset 正确复位）：

```python
# 双玩家框架（PVP/PvPvE 使用）：None 表示该玩家不在场；单人仅 player_tank
self.player2_tank = None
# 开火冷却改为按 owner 独立（双人同场各自独立 0.1s，互不影响）
# 替代原单一 self.fire_cooldown_remaining（持续到 Task 全落地后彻底移除）
self.fire_cooldowns = {}          # {owner: 剩余冷却秒}
```

替换 `_try_fire` 为按玩家分发，并新增 `_try_fire_for` / `_fire_shotgun_for` / `_get_cooldown`（每玩家独立冷却）：

```python
def _try_fire(self) -> None:
    """P1 开火入口（PLAYING 帧内由 J 键触发）。"""
    if self.player_tank is not None:
        self._try_fire_for(self.player_tank, "p1")

def _try_fire_p2(self) -> None:
    """P2 开火入口（PLAYING 帧内由空格键触发；P2 不在场则忽略）。"""
    if self.player2_tank is not None:
        self._try_fire_for(self.player2_tank, "p2")

def _get_cooldown(self, owner: str) -> float:
    """读取某玩家剩余开火冷却（不在场/未开过火视为 0）。"""
    return self.fire_cooldowns.get(owner, 0.0)

def _try_fire_for(self, tank, owner: str) -> None:
    """按 tank 与 owner 开火：普通弹 owner 传入；霰弹弹丸实例补 owner。"""
    if self._get_cooldown(owner) > 0:
        return
    muzzle_x, muzzle_y = tank.get_muzzle_position()
    dx0, dy0 = tank.get_direction_vector()

    # 霰弹模式（独立弹夹）：不依赖普通弹药/重装
    if ITEM_SYSTEM_ENABLED and tank.shotgun_active:
        self._fire_shotgun_for(tank, owner)
        return

    if not tank.can_fire():
        return
    bullet = Bullet(muzzle_x, muzzle_y, dx0, dy0, self.game_map, owner=owner)
    self.bullets.append(bullet)
    self.fire_cooldowns[owner] = BULLET_FIRE_COOLDOWN
    tank.consume_ammo()

def _fire_shotgun_for(self, tank, owner: str) -> None:
    """霰弹开火：生成 16 颗弹丸并对实例补 owner（ShotgunPellet 构造不支持 owner 参数）。"""
    import math as _m
    muzzle_x, muzzle_y = tank.get_muzzle_position()
    dx0, dy0 = tank.get_direction_vector()
    base_angle = _m.atan2(dx0, -dy0)   # 还原朝向：dx=sin a, dy=-cos a -> a=atan2(dx, -dy)
    for _ in range(SHOTGUN_PELLETS):
        spread = random.uniform(-SHOTGUN_SPREAD_RADIANS, SHOTGUN_SPREAD_RADIANS)
        angle = base_angle + spread
        dx = _m.sin(angle)
        dy = -_m.cos(angle)
        pellet = ShotgunPellet(muzzle_x, muzzle_y, dx, dy, self.game_map)
        pellet.owner = owner          # 覆盖默认 "player"，供友军伤害判定
        self.bullets.append(pellet)
    tank.consume_shotgun_ammo()
    self.fire_cooldowns[owner] = BULLET_FIRE_COOLDOWN
```

在 `update()` 中，把开火冷却的全局扣减（原 `self.fire_cooldown_remaining > 0` 段）替换为按在场玩家各自扣减：

```python
# 开火冷却：按在场玩家 owner 各自递减
for owner in ("p1", "p2"):
    if self.fire_cooldowns.get(owner, 0.0) > 0:
        self.fire_cooldowns[owner] = max(0.0, self.fire_cooldowns[owner] - dt)
```

在 `handle_events` 的 PLAYING 分支补充 P2 开火键：

```python
elif self.state == GameState.PLAYING:
    if key == pygame.K_j:
        self._try_fire()
    if key == pygame.K_SPACE:
        self._try_fire_p2()
```

在 `update()` 中，把玩家移动改为按在场玩家执行：

```python
# 玩家移动 & 弹药（P1 必在场；P2 视模式存在）
keys = pygame.key.get_pressed()
self.player_tank.handle_input(keys, dt)
self.player_tank.update_ammo(dt)
if self.player2_tank is not None:
    self.player2_tank.handle_input(keys, dt)
    self.player2_tank.update_ammo(dt)
```

替换敌方子弹 vs 玩家 碰撞段为双判（新增 `_check_enemy_bullet_hit`）：

```python
# 2) 敌方子弹 vs 玩家（P1 与 P2 分别判定）
for bullet in self.bullets:
    if not bullet.alive or bullet.owner != "enemy":
        continue
    hit = self._check_enemy_bullet_hit(bullet)
    if hit is not None:
        bullet.alive = False
        self._on_player_destroyed(hit)
        return
```

新增两个方法：

```python
def _check_enemy_bullet_hit(self, bullet):
    """敌弹命中判定：返回被命中的玩家（P1 或 P2），未命中返回 None。"""
    if bullet.rect.colliderect(self.player_tank.rect):
        return self.player_tank
    if (self.player2_tank is not None
            and bullet.rect.colliderect(self.player2_tank.rect)):
        return self.player2_tank
    return None

def _on_player_destroyed(self, tank) -> None:
    """玩家被摧毁统一出口（护盾判定在调用前完成）。

    Task3 阶段：仅落回原有 _game_over() 行为，局制分流在 Task4/5/6 引入。
    """
    # 护盾免疫判定：命中护盾则忽略（不消耗护盾时间）
    if ITEM_SYSTEM_ENABLED and tank.handle_enemy_hit():
        return
    self._game_over()
```

> 说明：现 [main.py L495-504](file:///c:/Users/32857/Desktop/tank_game/main.py#L495-L504) 的敌弹命中段整体替换为上两段。护盾判定移入 `_on_player_destroyed` 统一处理（含后续友军伤害共用）。

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `python _verify_multimode_t3.py`
Expected: `T3 OK`

- [ ] **Step 5: 手动回归单人**：`python main.py` 进入单人，确认移动/开火/被击中 GAME OVER 行为与原先一致。

- [ ] **Step 6: 提交**（若 git 已初始化）

```bash
git add main.py _verify_multimode_t3.py
git commit -m "feat: 双玩家战斗框架（owner 归因 + 敌方子弹双判）"
```

---

### Task 4: 单人局制改造（系列赛流程）

> 单人 / PvPvE 入口沿用"选关 → 选难度"；全模式任意关卡直接可选（无解锁限制）。N 局系列赛在选定单关内进行；每局清空该关波次=玩家胜，被摧毁=敌胜。

**Files:**
- Modify: `main.py`
- Test: `_verify_multimode_t4.py`

- [ ] **Step 1: 写失败验证脚本 `_verify_multimode_t4.py`**

```python
# -*- coding: utf-8 -*-
"""Task4 验证：单人局制 —— 清波胜 / 被摧毁负 / 系列结算 / 全关卡可选。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
game = M.Game()

# 单人进入局制
game.start_game(0, "简单")
assert game.round_manager is not None
assert game.round_manager.rounds_total == 5 and game.round_manager.win_needed == 3

# 模拟清空本局波次 -> 该局玩家胜 -> 进入第 2 局
game.wave_manager._finished = True
game._complete_round_win()
assert game.round_manager.current_round == 2
assert game.round_manager.side_a_wins == 1

# 进入局 2：被摧毁 -> 该局敌胜
game._start_round()
game._on_round_loss()
assert game.round_manager.side_b_wins == 1
assert game.round_manager.current_round == 3

# 玩家赢局 3、4 -> 共 3 胜到顶 -> 系列胜（全关卡开放，无解锁步骤）
game._start_round(); game._complete_round_win()   # 局 3 玩家胜
game._start_round(); game._complete_round_win()   # 局 4 玩家胜 -> side_a_wins==3==win_needed
assert game.round_manager.match_over and game.round_manager.a_win

print("T4 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_multimode_t4.py`
Expected: `AttributeError: 'Game' object has no attribute 'round_manager'`

- [ ] **Step 3: 修改 `main.py` —— 单人局制接入**

`_new_combat` 中新增局制管理器（单人默认生效；PVP/PvPvE 在各自 start 方法重建）：

```python
# 局制管理（系列赛）：单人默认在 _new_combat 建立，start_game 时按难度重建
self.round_manager = RoundManager("solo", self.selected_difficulty)
```

import 增加：

```python
from core.match_config import get_rounds, get_win_rounds, friendly_fire_enabled, ai_cap
from core.round_manager import RoundManager
```

`start_game` 中按难度重建局制并进入局 1（整段替换）：

```python
def start_game(self, stage_index: int = 0, difficulty: str = None) -> None:
    """从指定关进入 PLAYING（单人局制：N 局系列，清波胜/被摧毁负）。"""
    self.selected_stage = stage_index
    self.selected_difficulty = difficulty or self.selected_difficulty
    self.match_mode = None            # 单人非 PVP/PvPvE
    self.state = GameState.PLAYING
    self.game_over_flag = False
    self.level_manager.start_game_at(stage_index)
    self.score_manager.reset()
    self.round_manager = RoundManager("solo", self.selected_difficulty)
    self.player2_tank = None
    self.ai_tanks = []
    self._start_round()
    # 重置流程奖励追踪（当前波=1，未发胜利奖励）
    self._prev_wave = self.wave_manager.current_wave
    self._victory_scored = False
```

新增局制方法（`_start_round` 为最终版，含 P2 重定位与友方存活列表，PvPvE 直接复用）：

```python
def _start_round(self) -> None:
    """开始新一局：重载当前关战场（地图/波次/玩家复位）并复位局标记。"""
    self.round_manager.reset_for_round()
    # 友方存活列表（solo 仅 P1；PvPvE 含 P2）
    self._friendly_alive = [self.player_tank]
    if self.player2_tank is not None:
        self._friendly_alive.append(self.player2_tank)
    self._load_stage(self.level_manager.current_stage)
    # P2 重定位到合法出生点（避免与 P1 出生点重叠）
    if self.player2_tank is not None:
        sx, sy = self._pick_random_player_spawn()
        self._reset_player_for_stage(sx, sy)

def _complete_round_win(self) -> None:
    """本局玩家（side_a）胜：清空波次后由 update 调用。"""
    if self.round_manager.round_over:
        return
    self.round_manager.record_round(side_a_win=True)
    self._after_round_settled()

def _on_round_loss(self) -> None:
    """本局玩家（side_a）负：玩家被摧毁时由 _on_player_destroyed 调用。"""
    if self.round_manager.round_over:
        return
    self.round_manager.record_round(side_a_win=False)
    self._after_round_settled()

def _after_round_settled(self) -> None:
    """单局结算后：系列结束则进结算页；否则下一局。

    set_victory = side_a 系列胜（solo 玩家 / PVP P1 / PvPvE 友方）；
    set_game_over = side_b 系列胜。全模式关卡均直接可选（无解锁）；
    单人系列胜仅同步记录通关存档（ProgressManager，不驱动解锁）。
    """
    if self.round_manager.match_over:
        if self.round_manager.a_win:
            if self.match_mode is None:      # 仅单人记录通关存档（战绩用途）
                idx = self.level_manager.stage_number - 1
                self.progress.mark_stage_cleared(idx)
            self.set_victory()
        else:
            self.set_game_over()
        return
    # 系列未结束：短暂停留后进入下一局
    self.round_over_pause = ROUND_PAUSE_SECONDS
```

在 `_new_combat` 初始化 `self.round_over_pause = 0.0`，并定义常量 `ROUND_PAUSE_SECONDS = 1.2`（放 main.py 模块级）。

`update()` 中清波胜利路径改造（替换现 [main.py L538-553](file:///c:/Users/32857/Desktop/tank_game/main.py#L538-L553) 的 VICTORY/切关块）：

```python
if self.wave_manager.is_finished:
    # 局制：清空该关全部波次 = 本局玩家胜（不再直接切关/VICTORY）
    self._complete_round_win()
    return
```

敌弹命中处理改为经 `_handle_enemy_bullet_hit`（护盾判定前置，避免 T3 直调 `_on_player_destroyed` 导致护盾失效）：

```python
# 2) 敌方子弹 vs 玩家（护盾免疫前置；PVP 收集逻辑在 T5 扩展）
for bullet in self.bullets:
    if not bullet.alive or bullet.owner != "enemy":
        continue
    hit = self._check_enemy_bullet_hit(bullet)
    if hit is not None:
        bullet.alive = False
        self._handle_enemy_bullet_hit(hit)
        return

def _handle_enemy_bullet_hit(self, tank) -> None:
    """敌弹命中玩家后的统一入口（护盾判定前置）。

    solo/pvpe：护盾免疫则忽略，否则 _on_player_destroyed（PVP 分支在 T5 扩展）。
    """
    if ITEM_SYSTEM_ENABLED and tank.handle_enemy_hit():
        return                    # 护盾免疫（不消耗时间）
    self._on_player_destroyed(tank)
```

`_on_player_destroyed` 改为局制负（最终版，PvPvE 分支在 T6 生效，solo 时 match_mode=None 走兜底该局负；护盾判定已由 `_handle_enemy_bullet_hit` 前置完成）：

```python
def _on_player_destroyed(self, tank) -> None:
    """玩家被摧毁结算（护盾判定已在前置方法完成）。

    solo：直接该局负；pvpe：从友方存活列表移除，全灭则敌胜该局。
    （PVP 不经过本方法，走 _pvp_victims 收集 + _settle_pvp。）
    """
    if self.match_mode == "pvpe" and tank in self._friendly_alive:
        self._friendly_alive.remove(tank)
        if not self._friendly_alive:
            self._on_round_loss()     # 友方全灭 -> 敌胜该局
        return
    self._on_round_loss()             # solo 直接该局负
```

局间暂停推进（在 `update()` 顶部 PLAYING 分支加）：

```python
if self.round_over_pause > 0:
    self.round_over_pause -= dt
    if self.round_over_pause <= 0:
        self._start_round()
    return
```

> 说明：`_complete_round_win` 在 `wave_manager.is_finished` 分支调用，此时该局已清空，`_after_round_settled` 若非末局走 `_start_round` 重载战场。`ROUND_PAUSE_SECONDS` 用于让玩家看到"本局结束"反馈。
> 局制下 `VICTORY_SCORE_REWARD`（+20 最终胜利奖励）不再适用（每局清波只是"该局胜"，不是最终胜利），该分支已被 `_complete_round_win` 取代；`_victory_scored` 保留但不再触发加分，避免改动其余流程。

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `python _verify_multimode_t4.py`
Expected: `T4 OK`

- [ ] **Step 5: 手动回归**：`python main.py` 单人选简单关，完整打完一局（清波 → 结算进下一局），被击中 → 该局负，3 局决出系列胜（全模式任意关卡直接可选，无解锁）。

- [ ] **Step 6: 提交**（若 git 已初始化）

```bash
git add main.py _verify_multimode_t4.py
git commit -m "feat: 单人局制（N局先赢W，清波胜/被摧毁负，系列胜记录通关存档，全关卡可选）"
```

---

### Task 6: 双人对战 PVP（纯对抗 · 无 AI）※ 在 Task 5（PvPvE）之后执行

**Files:**
- Modify: `main.py`
- Modify: `ui/menu.py`（启用入口 + PVP 配置页，通过 main 的回调）
- Rename: `_verify_multimode_t5.py` → `_verify_multimode_t6.py`（执行会话既有 PVP 脚本；本 Task 编号为 6，避免与 Task 5 PvPvE 的 t5 脚本撞名）
- Test: `_verify_multimode_t6.py`

- [ ] **Step 1: 复用执行会话既有 PVP 验证脚本（重命名为 t6）**

> 既有 `_verify_multimode_t5.py` 已实现 PVP 纯1v1 断言（`start_pvp(rounds=N)` 局数选择 5/7/9/11/13 → ⌈N/2⌉、P2 恒在场、
> `_handle_player_bullet_hit_pvp` 互射收集与**当场 +1 分**、`_settle_pvp` 结算（互毁作废重开 / 独亡记胜局）、
> 护盾免疫、PVP 局间文案、60 帧无波次敌人断言）。先将其**重命名为 `_verify_multimode_t6.py`**，本任务实现须与此脚本**签名/行为兼容**（见 Step 3）。

- [ ] **Step 2: 运行确认失败**

Run: `venv_py310\Scripts\python.exe _verify_multimode_t6.py`
Expected: `AttributeError: 'Game' object has no attribute 'start_pvp'`

- [ ] **Step 3: 修改 `main.py` —— PVP 启动与玩家互打判定（与既有 t5 脚本对齐）**

新增方法（供菜单与验证脚本调用；**无 AI 参数**）：

```python
def start_pvp(self, rounds: int = 5, difficulty: str = "普通") -> None:
    """启动 PVP 系列赛：纯 P1 vs P2 对抗（对局数由菜单传入，如 5/7/9/11/13）。

    rounds 为对局数（5/7/9/11/13，由菜单按钮传入）。
    """
    self.match_mode = "pvp"
    self.selected_difficulty = difficulty
    self.player2_tank = Player2Tank(600, 600, self.game_map)  # P2 恒在场
    self.round_manager = RoundManager("pvp", difficulty, rounds=rounds)
    self.ai_tanks = []                       # PVP 无中立 AI
    self.state = GameState.PLAYING
    self.game_over_flag = False
    self._start_round()
    # 首局"开战版"信息提示（与单人 start_game 一致）
    self.round_over_pause = ROUND_INTRO_SECONDS
    self._pause_after = "intro"
    self._last_round_a_win = None
```

**PVP 必须跳过波次敌人生成与波次推进**（纯对抗，不应生成普通波次敌人）。在 `update()` 中加 `match_mode` 守卫：

```python
# 敌方生成：PVP 不生成波次敌人（纯对抗），其余模式照常
if self.match_mode != "pvp":
    self.spawn_manager.update(dt)
    spawn_pos = self.spawn_manager.try_spawn(
        len(self.enemy_tanks),
        self.player_tank.rect.center,
        [enemy.rect for enemy in self.enemy_tanks],
    )
    if spawn_pos is not None:
        self.enemy_tanks.append(
            EnemyTank(spawn_pos[0], spawn_pos[1], self.game_map)
        )
```

波次推进与流程奖励段（原 `self.wave_manager.update(...)` 及之后的 `_cur_wave`/`is_finished` 分支）整段包在 `if self.match_mode != "pvp":` 内，PVP 不执行（PVP 单局胜负由玩家互打判定）。

`update()` 中敌人更新保持现状即可：PVP 下 `enemy_tanks` 恒空、无 `ai_tanks`，遍历无副作用（PvPvE 的敌人 target=最近玩家在 Task 5 实现）。

**PVP 玩家子弹 vs 对方玩家判定（与既有 t5 脚本对齐）**：在"玩家子弹 vs 敌方"循环之后、敌弹循环之前插入一个专用循环；命中即收集到 `_pvp_destroyed` dict（{被摧毁者: 射手 owner}）并**当场给击杀方 +1 分**；护盾免疫剔除；帧末 `_settle_pvp()` 统一判胜负。实现如下：

```python
# 1c) 玩家子弹 vs 对方玩家（PVP 纯对抗）
def _handle_player_bullet_hit_pvp(self, owner: str, victim) -> None:
    """PVP 玩家子弹命中对方：护盾免疫剔除；记录到 _pvp_destroyed 并当场 +1 分。

    Args:
        owner:  射手 owner（"p1"/"p2"）
        victim: 被命中的对方玩家坦克
    """
    if ITEM_SYSTEM_ENABLED and victim.handle_enemy_hit():
        return                       # 护盾免疫（不消耗时间、不结算、不加分）
    self._pvp_destroyed[victim] = owner
    shooter = self.player_tank if owner == "p1" else self.player2_tank
    self.score_manager.add_score(1)  # 击败对方玩家 +1 分（spec 计分表）
```

```python
# 调用处：1c) 循环（放在"玩家子弹 vs 敌方"循环之后、敌弹循环之前）
if self.match_mode == "pvp":
    for bullet in self.bullets:
        if not bullet.alive or bullet.owner not in ("p1", "p2"):
            continue
        victim = (self.player_tank if bullet.owner == "p2"
                  else self.player2_tank)
        if victim is None:
            continue
        if bullet.rect.colliderect(victim.rect):
            bullet.alive = False
            self._handle_player_bullet_hit_pvp(bullet.owner, victim)
if self.match_mode == "pvp" and self._pvp_destroyed:
    self._settle_pvp()
    return        # 结算可能重载战场（同帧互毁重开），本帧不再继续下游碰撞
```

新增结算方法（互毁作废重开；独亡记被摧毁方负该局；加分已在命中时完成）：

```python
def _settle_pvp(self) -> None:
    """PVP 本帧结算：同帧互毁作废重开；独亡则被摧毁方负该局。"""
    if len(self._pvp_destroyed) >= 2:
        self._pvp_destroyed.clear()
        self._start_round()         # 同帧互毁：该局作废重开
        return
    victim = next(iter(self._pvp_destroyed))
    self._pvp_destroyed.clear()
    self.round_manager.record_round(side_a_win=(victim is self.player2_tank))
    self._after_round_settled()
```

> 说明：PVP 无敌人，故 `_handle_enemy_bullet_hit` 无需 PVP 分支（敌弹循环保持 T4 原样：solo 该局负 / pvpe 移除存活）。互毁判定：本帧 P1/P2 同时被对方子弹命中（dict size ≥ 2）→ 该局作废重开，直到某局仅一方被摧毁。
> ⚠️ 既有 `_verify_multimode_t5.py` 断言 `assert game.score_manager.current_score == before + 1` 在调用 `_handle_player_bullet_hit_pvp` **之后立即生效**——故加分须在命中方法内当场完成（而非 `_settle_pvp` 时）。

**新状态字段与渲染**：
- `_new_combat()` 初始化（与 `match_mode`/`ai_tanks` 同批）：

```python
self._pvp_destroyed = {}    # {被摧毁玩家: 射手 owner}（PVP 本帧结算缓冲）
```

- `update()` 顶部清空（与其他每帧状态同上）：

```python
self._pvp_destroyed = {}
```

- `_render_battle` 追加绘制 P2（`ai_tanks` 无需渲染，PVP 无 AI）：

```python
if self.player2_tank is not None:
    self.player2_tank.render(self.screen)
```

> 注：Player2Tank 须在 PlayerTank 之后渲染（P2 在 P1 之上，位置不同不重叠）。

- [ ] **Step 4: 修改 `main.py`/`ui/menu.py` —— 启用 PVP 入口（简化：无 AI 配置）**

在 `_mode_screen` 中启用双人对战，新增 `_pvp_setup_screen`（PVP 对局数选择 5/7/9/11/13，无难度/AI 配置）：

```python
def _mode_screen(self) -> MenuScreen:
    scr = MenuScreen("mode", "选择模式")
    scr.add(
        UiButton(column_button_rect(0, 4), "单人模式",
                 lambda: self.menu.push(self._level_screen())),
        UiButton(column_button_rect(1, 4), "双人对战",
                 lambda: self.menu.push(self._pvp_setup_screen())),
        UiButton(column_button_rect(2, 4), "PVPVE 作战",
                 lambda: self.menu.push(self._pvpe_level_screen())),  # 先选关，再选难度
        UiButton(column_button_rect(3, 4), "返回", lambda: self.menu.pop()),
    )
    return scr

def _pvp_setup_screen(self) -> MenuScreen:
    scr = MenuScreen("pvp_setup", "双人对战 · 选择对局数")
    n = len(PVP_ROUNDS_CHOICES)
    labels = {5: "三局两胜", 7: "四局三胜", 9: "五局四胜",
              11: "六局五胜", 13: "七局六胜"}
    for i, r in enumerate(PVP_ROUNDS_CHOICES):
        scr.add(UiButton(column_button_rect(i, n + 1),
                         f"打 {r} 局（{labels.get(r, '')}）",
                         lambda r=r: self.start_pvp(r)))
    scr.add(UiButton(column_button_rect(n, n + 1), "返回", lambda: self.menu.pop()))
    scr.on_draw = _draw_bottom_note("P1 vs P2 纯对抗 · 先赢 ⌈N/2⌉ · 击败对方 +1 分")
    return scr
```

- [ ] **Step 5: 运行验证脚本确认通过**

Run: `venv_py310\Scripts\python.exe _verify_multimode_t6.py`
Expected: `T6 OK`

- [ ] **Step 6: 手动验收**：`python main.py` → 双人对战 → 选局数 → 开始。确认：P1(WASD+J)/P2(方向键+空格) 可同时移动开火；P1 子弹可命中 P2（护盾免疫生效）击杀方 **+1 分**、被摧毁方负该局；按所选局数决出系列胜者回到菜单。

- [ ] **Step 7: 提交**（若 git 已初始化）

```bash
git add main.py ui/menu.py _verify_multimode_t6.py
git commit -m "feat: PVP 双人对战（纯对抗·无AI，玩家互打+1分，5 胜决系列）"
```

---

### Task 5: 双人 PvPvE 协作模式 ※ 优先执行（早于 Task 6 PVP）

**Files:**
- Modify: `main.py`
- Modify: `ui/menu.py`（启用 PvPvE 入口，经 main 的回调）
- Test: `_verify_multimode_t5.py`

- [ ] **Step 1: 写失败验证脚本 `_verify_multimode_t5.py`**

```python
# -*- coding: utf-8 -*-
"""Task5 验证：PvPvE 友军伤害 / 护盾免疫 / 阵营计分 / 敌人追最近玩家。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
game = M.Game()
game.start_pvpe("简单")        # stage_index 缺省 = 第 1 关
assert game.match_mode == "pvpe"
assert game.player2_tank is not None
assert game.round_manager.rounds_total == 5 and game.round_manager.win_needed == 3
assert game.ai_tanks == []
assert len(game._friendly_alive) == 2       # 友方 = P1 + P2

# 敌人 target = 最近玩家
from entities.enemy_tank import EnemyTank
probe = EnemyTank(300, 300, game.game_map)  # 直接构造探针敌人（不进 enemy_tanks）
probe.x, probe.y = 300, 300
game.player_tank.x, game.player_tank.y = 600, 300   # 距离 300
game.player2_tank.x, game.player2_tank.y = 400, 300 # 距离 100
assert game._ai_target(probe) == game.player2_tank.rect.center, "敌人应追最近玩家(P2)"

# 友军伤害：护盾免疫（不减少友方存活、不计分、不结算）
game.player2_tank.apply_shield()
before_alive = len(game._friendly_alive)
game._on_ally_hit(game.player2_tank, game.player_tank)
assert len(game._friendly_alive) == before_alive, "护盾应免疫友军伤害"

# 友军伤害：无护盾被队友击杀 -> 友方存活-1，本局未结束，不计分
game.player2_tank.shield_remaining = 0.0
game._on_ally_hit(game.player2_tank, game.player_tank)
assert len(game._friendly_alive) == 1, "P2 被队友击杀，友方剩 P1"
assert game.round_manager.side_b_wins == 0, "仅一名队友被击杀，本局未结束"
assert game.score_manager.current_score == 0, "击杀队友不计分"

# 友方剩余 P1 被敌方摧毁 -> 友方全灭 -> 敌胜该局
game._on_player_destroyed(game.player_tank)
assert game.round_manager.side_b_wins == 1
assert game.round_manager.current_round == 2

print("T5 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `venv_py310\Scripts\python.exe _verify_multimode_t5.py`
Expected: `AttributeError: 'Game' object has no attribute 'start_pvpe'`

- [ ] **Step 3: 修改 `main.py` —— PvPvE 启动与友军伤害**

新增方法：

```python
def start_pvpe(self, difficulty: str = None, stage_index: int = 0) -> None:
    """启动 PvPvE 系列赛：友方=P1+P2，敌方=该关波次 AI。"""
    self.match_mode = "pvpe"
    self.selected_difficulty = difficulty
    self.player2_tank = Player2Tank(600, 600, self.game_map)  # P2 恒在场
    self.round_manager = RoundManager("pvpe", difficulty)
    self.ai_tanks = []                       # PvPvE 敌方走波次生成
    self.state = GameState.PLAYING
    self.game_over_flag = False
    self._start_round()
    # 波次流程奖励追踪（每局清波仍累计 WAVE_SCORE_REWARD）
    self._prev_wave = self.wave_manager.current_wave
    self._victory_scored = False
```

**PvPvE 敌人 target = 最近玩家**（双玩家在场时敌人追距其更近者）：`update()` 敌方更新段把原本写死的 `self.player_tank.rect.center` 改为 `self._ai_target(enemy)`：

```python
# 敌方坦克更新（PvPvE 追最近玩家；solo 时 P2 不在场则等价于 P1）
for enemy in self.enemy_tanks:
    enemy.evaluate_threats(self.bullets)
    enemy.update(dt, self._ai_target(enemy),
                 player_reloading=(self.player_tank.reload_remaining > 0))
    if enemy.pending_bullet is not None:
        self.bullets.append(enemy.pending_bullet)
        enemy.pending_bullet = None
```

新增方法（供 update 与验证脚本使用）：

```python
def _ai_target(self, enemy):
    """敌方 AI 目标：双玩家在场取距敌人最近者，否则取 P1（solo 等价原行为）。"""
    candidates = [self.player_tank]
    if self.player2_tank is not None:
        candidates.append(self.player2_tank)
    return min(candidates,
               key=lambda t: ((t.x - enemy.x) ** 2 + (t.y - enemy.y) ** 2)).rect.center
```

友军伤害判定（子弹命中逻辑内新增）：

```python
def _check_player_bullet_hit(self, bullet):
    """玩家子弹命中判定：返回 (被命中玩家, 射手玩家)；未命中返回 None。

    友军伤害（PvPvE）：任一玩家子弹可命中另一玩家（含队友），护盾免疫。
    """
    shooter = self.player_tank if bullet.owner == "p1" else (
        self.player2_tank if bullet.owner == "p2" else None)
    if shooter is None:
        return None
    targets = [t for t in (self.player_tank, self.player2_tank)
               if t is not None and t is not shooter]
    for t in targets:
        if bullet.rect.colliderect(t.rect):
            return (t, shooter)
    return None
```

在玩家子弹 vs 敌方/中立 AI 循环之后、敌弹循环之前，新增玩家子弹 vs 玩家（友军伤害，**仅 PvPvE**）：

```python
# 1b) 玩家子弹 vs 玩家（友军伤害，仅 PvPvE；PVP/单人无友军伤害）
if self.match_mode == "pvpe":
    for bullet in self.bullets:
        if not bullet.alive or bullet.owner not in ("p1", "p2"):
            continue
        hit = self._check_player_bullet_hit(bullet)
        if hit is not None:
            victim, shooter = hit
            bullet.alive = False
            self._on_ally_hit(victim, shooter)
            break
```

新增：

```python
def _on_ally_hit(self, victim, shooter) -> None:
    """友军伤害结算：护盾免疫；击杀队友不计分；友方全灭 -> 敌胜该局。"""
    if victim.handle_enemy_hit():
        return                       # 护盾免疫（不消耗时间、不计分）
    # 击杀队友：不加分不扣分（spec 定稿），仅推进友方存活
    self._friendly_alive = [t for t in self._friendly_alive if t is not victim]
    if not self._friendly_alive:     # 友方全员被摧毁 -> 敌胜该局
        self._on_round_loss()
```

`_start_round`（含 `_friendly_alive` 与 P2 重定位）与 `_on_player_destroyed`（含 pvpe 分支）已在 T4 最终版实现，PvPvE 直接复用，**无需改动**。仅补充：`_on_ally_hit` 供友军子弹命中调用（T4 版 `_on_player_destroyed` 已含 pvpe 移除逻辑）。

`_on_player_destroyed`（T4 最终版，已含 pvpe 分支，此处仅确认）：
- solo：直接该局负
- pvpe：若 tank 在 `_friendly_alive` 中则移除，全灭则 `_on_round_loss()`

菜单启用 PvPvE（与单人流程对齐：先选关、再选难度）：

```python
def _pvpe_level_screen(self) -> MenuScreen:
    """PvPvE 关卡选择页：全模式任意关卡直接可选（无解锁限制）。"""
    stages = self.level_manager.stages
    scr = MenuScreen("pvpe_level", "PVPVE 作战 · 选择关卡")
    for i, st in enumerate(stages):
        name = st.get("meta", {}).get("name", f"关卡 {i + 1}")
        scr.add(UiButton(column_button_rect(i, len(stages) + 1),
                         f"第{i + 1}关 · {name}",
                         lambda i=i: self._pick_pvpe_level(i)))
    scr.add(UiButton(column_button_rect(len(stages), len(stages) + 1),
                     "返回", lambda: self.menu.pop()))
    scr.on_draw = _draw_bottom_note("任意关卡均可直接挑战")
    return scr

def _pick_pvpe_level(self, index: int) -> None:
    self.selected_stage = index
    self.menu.push(self._pvpe_setup_screen())

def _pvpe_setup_screen(self) -> MenuScreen:
    scr = MenuScreen("pvpe_setup", f"PVPVE 作战 · 第{self.selected_stage + 1}关 · 难度")
    n = len(DIFFICULTY_ORDER)
    for i, d in enumerate(DIFFICULTY_ORDER):
        scr.add(UiButton(column_button_rect(i, n + 1), d,
                         lambda d=d: self.start_pvpe(d, self.selected_stage)))
    scr.add(UiButton(column_button_rect(n, n + 1), "返回", lambda: self.menu.pop()))
    scr.on_draw = _draw_bottom_note("友方=P1+P2，友军伤害开启；清空波次友方胜")
    return scr
```

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `venv_py310\Scripts\python.exe _verify_multimode_t5.py`
Expected: `T5 OK`

- [ ] **Step 5: 手动验收**：`python main.py` → PvPvE → 选关 → 选难度。确认：P1/P2 同场清波且敌人追最近玩家；P1 子弹可伤害 P2（护盾免疫生效）；击杀队友不计分；友方全灭 → 敌胜该局；清空波次 → 友胜；系列按难度局数决出胜负。

- [ ] **Step 6: 提交**（若 git 已初始化）

```bash
git add main.py ui/menu.py _verify_multimode_t5.py
git commit -m "feat: PvPvE 双人协作（友军伤害+护盾免疫+阵营计分+敌人追最近玩家+局制）"
```

---

### Task 7: HUD 局间覆盖层 + 全量回归验收

**Files:**
- Modify: `main.py`
- Modify: `ui/hud.py`
- Test: `_verify_multimode_t7.py`

- [ ] **Step 1: 写验证脚本 `_verify_multimode_t7.py`**

```python
# -*- coding: utf-8 -*-
"""Task7 验证：HUD 局间信息 + 三模式回归冒烟。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
game = M.Game()

# 局间信息文本
game.match_mode = "pvp"
game.player2_tank = None
game.round_manager = M.RoundManager("pvp", "普通")
text = game._round_indicator_text()
assert "ROUND" in text and "/9" in text, text

# 单人冒烟：start_game 后能跑一帧 update
game = M.Game()
game.start_game(0, "简单")
game.update()
assert game.state.value in ("PLAYING", "GAME_OVER", "VICTORY")

# 全模式配置表一致
for m in ("solo", "pvp", "pvpe"):
    for d in ("简单", "普通", "中等", "困难"):
        n = M.get_rounds(m, d)
        w = M.get_win_rounds(m, d)
        assert w == (n + 1) // 2

print("T7 OK")
```

- [ ] **Step 2: 运行确认失败**

Run: `python _verify_multimode_t7.py`
Expected: `AttributeError: 'Game' object has no attribute '_round_indicator_text'`

- [ ] **Step 3: 修改 `main.py` + `ui/hud.py` —— 局间覆盖层**

`main.py` 新增局间信息文本与渲染（PLAYING 时叠加，不新增状态）：

```python
def _round_indicator_text(self) -> str:
    """局间 HUD 文本：ROUND x/N · A 胜局 · B 胜局（按模式取标签）。"""
    rm = self.round_manager
    if self.match_mode == "pvp":
        a, b = "P1", "P2"
    elif self.match_mode == "pvpe":
        a, b = "友方", "敌方"
    else:
        a, b = "玩家", "敌方"
    return (f"ROUND {rm.current_round}/{rm.rounds_total} · "
            f"{a} {rm.side_a_wins} · {b} {rm.side_b_wins}")
```

`ui/hud.py` 新增渲染方法（读 `game._round_indicator_text()`）：

```python
def render_round_indicator(self, surface, text: str) -> None:
    """局间角标：绘制在游戏区左上角（半透明底条）。"""
    import pygame
    from core.settings import COLOR_UI_AREA_TEXT
    font = pygame.font.SysFont("microsoftyahei", 18)
    surf = font.render(text, True, COLOR_UI_AREA_TEXT)
    pad_x, pad_y = 8, 4
    bg = pygame.Surface((surf.get_width() + pad_x * 2,
                         surf.get_height() + pad_y * 2), pygame.SRCALPHA)
    bg.fill((255, 255, 255, 150))
    bg.blit(surf, (pad_x, pad_y))
    surface.blit(bg, (8, 8))
```

在 `render()` 的 PLAYING 分支调用（`self.hud.render(self.screen, self)` 之后；单人局制同样显示，故判断用 `round_manager` 而非 `match_mode`）：

```python
if self.round_manager is not None:
    self.hud.render_round_indicator(
        self.screen, self._round_indicator_text())
```

- [ ] **Step 4: 运行验证脚本确认通过**

Run: `python _verify_multimode_t7.py`
Expected: `T7 OK`

- [ ] **Step 5: 全量手动验收（三模式 + 单人回归）**

```bash
python _verify_multimode_t1.py   # 期望 T1 OK
python _verify_multimode_t2.py   # 期望 T2 OK
python _verify_multimode_t3.py   # 期望 T3 OK
python _verify_multimode_t4.py   # 期望 T4 OK
python _verify_multimode_t5.py   # 期望 T5 OK
python _verify_multimode_t6.py   # 期望 T6 OK
python _verify_multimode_t7.py   # 期望 T7 OK
```

手动（`python main.py`）：
- 单人-简单：5 局先赢 3，清波胜/被摧毁负，任意关卡直接可选（无解锁限制）；局间左上角显示 ROUND。
- 双人对战：P1/P2 键位、选局数（5/7/9/11/13）、一局定负、先赢 ⌈N/2⌉ 决系列。
- PvPvE：友军伤害+护盾免疫、击杀队友不计分、友方全灭敌胜、清波友胜、按难度局数。
- `ITEM_SYSTEM_ENABLED=False` 时单人可正常游玩（回归）。

- [ ] **Step 6: 提交**（若 git 已初始化）

```bash
git add main.py ui/hud.py _verify_multimode_t7.py
git commit -m "feat: 局间 HUD 覆盖层 + 三模式回归验收"
```

---

### Task 8: 收尾文档（DEV-PSA）

**Files:**
- Create: `# Phase 9 多人模式（PVP/PvPvE）完成冻结 PSA.md`

- [ ] **Step 1: 编写 PSA 文档**（沿用项目既有 PSA 格式：范围 / 冻结内容 / 回归结果 / 已知限制 / 后续任务）

```markdown
# Phase 9 多人模式（PVP / PvPvE）完成冻结 PSA

范围：新增双人对战（PVP）、双人 PvPvE；统一"系列赛(N局先赢⌈N/2⌉)"对局模型；
单人升级为局制（清波胜/被摧毁负）。详见 docs/superpowers/specs/2026-08-23-multiplayer-modes-design.md。

冻结内容：
- core/match_config.py / core/round_manager.py（纯逻辑）
- entities/player2_tank.py（P2 键位子类）
- main.py 双玩家框架 + 局制流程 + 模式分流 + 友军伤害
- ui/hud.py 局间覆盖层

回归结果：_verify_multimode_t1~t7 全部通过；手动验收三模式 + 单人回归通过。

已知限制（后续独立任务）：
- "小/中/重"敌人类型未实现（enemy_tank 仅 small 单型）
- 敌方阵营内讧规则未实现（AI 不会互相开火）
- PVP 同帧互毁采用简化判定（作废重开该局）

后续：差异化敌人类型、敌我阵营扩军、手机端同屏双人。
```

- [ ] **Step 2: 提交**（若 git 已初始化）

```bash
git add "# Phase 9 多人模式（PVP/PvPvE）完成冻结 PSA.md"
git commit -m "docs: Phase 9 多人模式冻结 PSA"
```

---

## 自审记录（Self-Review）

**第一轮（初稿后）：**
- **Spec 覆盖**：对局模型（T1）、P2 键位（T2）、双玩家地基（T3）、单人局制（T4）、PVP+中立 AI 追最近玩家（T5）、PvPvE 友军伤害+护盾免疫+阵营计分（T6）、HUD+回归（T7）、PSA（T8）。无遗漏。
- **Placeholder 扫描**：全部步骤含完整代码/命令/期望输出，无 TBD。
- **类型一致性**：`RoundManager` 字段与 `record_round/reset_for_round`、`_start_round/_complete_round_win/_on_round_loss/_after_round_settled`、`match_mode`（None/'pvp'/'pvpe'）、owner（"p1"/"p2"/"enemy"）全程一致。

**第二轮（执行前复核，已修正）：**
- **霰弹 muzzle 混乱**：`_fire_shotgun_for` 原先用海象运算符重复取 muzzle，已改为先取一次并删冗余 `_dir_parts`。
- **T4 验证脚本对局复位缺失**：连续结算间未 `_start_round`，`round_over` 未复位会误 return；已改为每局结算后 `_start_round()`。
- **护盾回归缺陷**：T4 替换 `_on_player_destroyed` 后护盾检查丢失（敌弹循环直调）；已把 `_handle_enemy_bullet_hit`（护盾前置）引入提前到 T4，T5 仅扩展 PVP 分支。
- **PVP 同帧互毁判定顺序缺陷**：原 `_pvp_double_kill` 先记账后判重开会残留胜局；改为 `_pvp_destroyed` 集合 + `_settle_pvp` 统一结算。
- **PVP 误生成波次敌人**：`update()` 生成段/波次段加 `if self.match_mode != "pvp"` 守卫。
- **T6 验证脚本口径错误**：友军击杀队友非全灭不应结算敌胜；已改为"存活-1、本局继续、不计分"，护盾免疫单独验证。
- **`_after_round_settled` 记录范围**：`mark_stage_cleared` 仅为单人通关存档（战绩记录，不驱动解锁），PVP/PvPvE 不记录。
- **T7 局间指示显示条件**：单人局制同样显示，判断用 `round_manager` 而非 `match_mode`。
- **`start_pvpe` 缺波次追踪复位**：补 `_prev_wave`/`_victory_scored`。
- **VICTORY 奖励处置**：局制下 +20 最终奖励分支由 `_complete_round_win` 取代，说明已注明。

**关键对接点复核：** `ShotgunPellet` 构造后实例赋 `owner`（T3）；`EnemyTank` 有 `.x/.y/.physics.max_speed` 实例属性与 `update(dt, player_pos, player_reloading)`（T5）；`WaveManager.is_finished` 作为局胜边界（T4）；PvPvE 的 `try_spawn` 安全距离保持以 P1 为基准（敌人远离任一玩家均可，无需改动冻结逻辑）。

**第三轮（与 spec 交叉 + 代码级核验，已修正）：**
- **E1【重大，已修】** PVP 玩家子弹无法击杀中立 AI：现有"玩家子弹 vs 敌方"碰撞只遍历 `enemy_tanks`（PVP 为空），AI 在 `ai_tanks`。T5 已把该碰撞改为合并判定，`ai_tanks` 命中也可击杀 +1。
- **E2【重大，已修】** PVP AI 难度用 `fire_cooldown` 覆盖无效（`EnemyTank.update` 开火后重置回模块常量）；改为覆盖 `physics.max_speed`（实例持久）。
- **E3【已修】** T1 验证脚本断言 `current_round==9` 错误，5 连胜系列提前结束 `current_round==5`。
- **E4【已修】** T3 验证脚本同帧两次开火曾可能被全局冷却拦截；已改为**每玩家独立冷却**（`fire_cooldowns` dict，P1/P2 各自 0.1s 互不影响），验证脚本不再需要重置冷却。
- **E6【用户决策，已纳入 Task 3】** 开火冷却由全局 `fire_cooldown_remaining` 改为按 owner 独立字典 `self.fire_cooldowns`，双人同场各自独立，符合"每玩家单独数据"。
- **E5【已修】** T6 友军伤害循环未门控，会污染 PVP/单人；已加 `if self.match_mode == "pvpe"` 守卫。

**第四轮（2026-08-24 用户范围修订，已重排）：**
- **PVP 移除"可选中立 AI"**：`start_pvp` 无 `ai_count/ai_difficulty` 参数、删 `PVP_AI_DIFFICULTY`、删 `ai_tanks` 生成与"玩家子弹击杀中立 AI"判定；对应旧修正 E1/E2 随修订**作废**（PVP 无 AI，`_ai_target` 转由 PvPvE 使用）。
- **顺序调整：Task 5 = PvPvE（优先），Task 6 = PVP（后做）**：两章标题/验证脚本（t5/t6）已对调；plan 头部"范围修订"已记录。
- **填补原 plan 缺口**：PVP 纯对抗必须有"玩家子弹 vs 对方玩家"判定（原 PVP 依赖中立 AI 子弹结算，砍 AI 后不可缺）——已新增无参 `_settle_pvp()` + `_pvp_victims/_pvp_shooters` 收集（验证脚本先 append 再调用），含护盾免疫、击杀方 +1 分、同帧互毁作废重开、结算后 return。
- **PvPvE 敌人追最近玩家**：`_ai_target` 划归 PvPvE（update 敌人段 target 改最近玩家，solo 等价 P1）。
- **`AI_CAP["pvp"]` 2→0** 已同步 core/match_config.py。

**第五轮（2026-08-24 复核修正，与执行会话实现对齐）：**
- **修正"死代码"误判**：`get_win_rounds_from_n`/`PVP_ROUNDS_CHOICES` 并非无用——`RoundManager(rounds=)` 已依赖、执行会话既有 `_verify_multimode_t5.py`（PVP）也在用。**保留为通用能力**；PVP 菜单暴露选局数（见头部"PVP 局数口径"）。
- **PVP 实现改为 dict 方案（与既有 t5 脚本兼容）**：`_pvp_destroyed`（dict: 被摧毁者→射手 owner）+ `_handle_player_bullet_hit_pvp(owner, victim)`（命中当场 +1 分、护盾免疫剔除）+ `_settle_pvp()` 无参（互毁重开/独亡记胜局）；废弃此前的 list 方案（`_pvp_victims/_pvp_shooters`）。
- **脚本文件名对齐**：既有 `_verify_multimode_t5.py`（PVP）在 Task 6 开工时**重命名为 `_verify_multimode_t6.py`**，避免与 Task 5（PvPvE）的 t5 脚本撞名。
- **F1/F2/F3 与笔误**：`_settle_pvp(victim=)` 签名不匹配已修；`_make_pvpe_probe_enemy` 探针已删（脚本直接构造 EnemyTank）；PVP settle 后 `return`；`bullet_owner` 未定义笔误已删。