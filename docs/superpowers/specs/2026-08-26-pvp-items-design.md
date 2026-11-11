# T7 设计：PVP 启用道具 + 道具系统全局调优

日期：2026-08-26
范围：在既有多人模式（PVP / PvPvE）之上，为 **PVP 纯 1v1 启用道具刷新与竞争拾取**，并对**道具系统做全局调优**（刷新更快、数量更多、在场更久），调优应用于全模式（单人 / PVP / PvPvE）。

## 背景与动机

用户游玩双人对战（PVP）时发现地图不刷新道具。经代码核查，PVP 无道具是**有意设计**：`main.py` 的道具系统块带 `match_mode != "pvp"` 守卫，Phase 5.4 设计时 PVP 定义为"纯 1v1 竞技、无道具无波次"。现需求变更为 PVP 也应有道具（双方竞争拾取），同时用户反馈道具系统整体"生成慢、数量少、在场短"，要求全局调优并应用到所有模式。

## 关键现状（已核实）

- `main.py` 道具块（update）：`if ITEM_SYSTEM_ENABLED and self.match_mode != "pvp":`，只对 P1 调用 `try_pickup` 与 `update_effects`。
- 道具机制底层**已支持双人**：`_try_fire_for(player2_tank, "p2")` 支持 P2 霰弹；`handle_enemy_hit` 对 P2 护盾免疫已生效（PVP 子弹互射 / 敌弹命中均校验）。
- 道具渲染（`_render_battle`）无模式限制，PVP 可直接显示。
- 每局 `_start_round → _load_stage` 会 `item_spawn_manager.reset()`，换局/互毁重开自动清场。
- **冻结约束**：`entities/item.py`、`core/item_spawn_manager.py` 为 Phase 7.1 冻结清单，禁止修改。二者构造函数已预留参数口：`ItemSpawnManager(game_map, spawn_interval=..., max_active=..., ...)`、`Item(x, y, item_type, lifetime=...)`。

## 硬约束（不可破坏）

- **不改冻结文件**：`entities/item.py`、`core/item_spawn_manager.py` 及其余冻结清单零改动。调优与多玩家避让通过**构造参数 + 子类扩展**在 main.py 层实现。
- **不改核心玩法**：PVP 仍无敌人/无波次（spawn/wave 守卫保持）；互毁作废、护盾豁免、AI 追最近玩家等逻辑不动。
- 参数集中化：调优值写入 `core/settings.py`（非冻结，已有道具系统区），作为唯一事实来源。
- PVP 道具竞争拾取、P1 先判规则不引入新 GameState。

## 需求定稿（已与用户确认）

| 项 | 现值 | 目标值 | 说明 |
|---|---|---|---|
| 刷新间隔 `ITEM_SPAWN_INTERVAL` | 5.0s | **3.0s** | 生成更快 |
| 同场上限 `ITEM_MAX_ACTIVE` | 1 | **2** | 数量更多 |
| 在场时长 `ITEM_LIFETIME` | 15.0s | **20.0s** | 多待 5 秒 |

**PVP 拾取规则**：P1、P2 竞争拾取——谁碰到谁捡，效果对双方完全一致（护盾/加速/霰弹）。同帧两人命中同一道具的概率极低，若出现按**先判定 P1 先得**（用户认可的推荐答案）。

## 设计

### 1. `core/settings.py` — 道具调优参数（唯一事实来源）

在既有"道具系统"区新增：

```python
ITEM_SPAWN_INTERVAL = 3.0   # 道具刷新间隔（秒），原 5.0 → 3.0（更快）
ITEM_MAX_ACTIVE   = 2       # 同场上限，原 1 → 2（更多）
ITEM_LIFETIME     = 20.0    # 道具在场时长（秒），原 15 → 20（+5s）
```

### 2. `main.py` — 增强版 ItemSpawnManagerEx（子类，不改冻结文件）

定义模块级子类，**只覆盖 `_spawn_one`**（因 `ItemSpawnManager` 未暴露 item 构造 lifetime 参数）：

```python
class ItemSpawnManagerEx(ItemSpawnManager):
    """道具刷新增强：以 settings 的 ITEM_LIFETIME 创建道具（覆盖冻结文件默认 15s）。
    不改冻结文件 item_spawn_manager.py；刷新间隔/数量经构造参数传入。"""

    def _spawn_one(self, player_rect, enemy_rects):
        pos = self._find_spawn_position(player_rect, enemy_rects)
        if pos is None:
            return None
        cx, cy = pos
        item = Item(cx, cy, self._choose_type(), lifetime=ITEM_LIFETIME)
        self._bind_density(item)
        return item
```

> **多玩家避让不覆盖 `_find_spawn_position`**：父类把"避让对象列表"作为 `enemy_rects` 参数使用，PVP 中把 P2 的 rect 并入该列表即可同时避开 P1+P2，无需复制方法体。

### 3. `main.py` `_load_stage` — 用增强类构造

```python
self.item_spawn_manager = ItemSpawnManagerEx(
    self.game_map,
    spawn_interval=ITEM_SPAWN_INTERVAL,
    max_active=ITEM_MAX_ACTIVE,
)
```

### 4. `main.py` `update()` — 全模式启用 + 双人接线

去掉 `match_mode != "pvp"` 守卫，改为全模式统一：

```python
if ITEM_SYSTEM_ENABLED:
    enemy_rects = [enemy.rect for enemy in self.enemy_tanks]
    if self.player2_tank is not None:
        enemy_rects = enemy_rects + [self.player2_tank.rect]  # PVP/PvPvE 避让 P2
    self.item_spawn_manager.update(dt, self.player_tank.rect, enemy_rects)
    collected = self.item_spawn_manager.try_pickup(self.player_tank)
    if collected:
        self.audio.play(SFX_ITEM_PICKUP, volume_scale=SFX_ITEM_PICKUP_VOLUME)
    if self.player2_tank is not None:
        collected2 = self.item_spawn_manager.try_pickup(self.player2_tank)
        if collected2:
            self.audio.play(SFX_ITEM_PICKUP, volume_scale=SFX_ITEM_PICKUP_VOLUME)
    self.player_tank.update_effects(dt)
    if self.player2_tank is not None:
        self.player2_tank.update_effects(dt)
```

- P1 先 try_pickup 后 P2 → 同帧竞争时 P1 先得（用户认可）。
- P2 效果计时生效：护盾/加速/霰弹剩余时间随 `update_effects(dt)` 递减。

## 数据流

```
update()
  └ ITEM_SYSTEM_ENABLED → ItemSpawnManagerEx.update(dt, P1.rect, enemy_rects=[敌人…, P2.rect])
       └ 计时达标且未达上限 → _spawn_one → _find_spawn_position(避让 P1+enemy_rects(含 P2))
       └ Item(lifetime=ITEM_LIFETIME=20) → items[]
  └ try_pickup(P1) / try_pickup(P2)   → item.apply(player) → player.apply_item_effect()
  └ P1.update_effects(dt) / P2.update_effects(dt) → 效果计时递减
```

## 错误处理与边界

- **换局/互毁重开**：`_start_round → _load_stage → reset()` 清空道具，不跨局残留。
- **P2 缺席（solo）**：`player2_tank is None` 分支跳过拾取与计时，行为与现状一致。
- **刷新点不足（50 次尝试失败）**：返回 None，本帧不生成（沿用冻结逻辑，无异常）。
- **同一道具同帧双碰**：P1 先判先得（低概率，推荐答案）。

## 测试与验证

> 运行环境：本项目为多解释器环境，`python` 指向 3.10（无 pygame）。**所有命令统一用 `py -3.14`**（pygame-ce 2.5.8）。项目非 git 仓库，冻结核对采用文件清单方式。

- `py -3.14 -m py_compile main.py` 通过。
- 回归既有验证脚本 `_verify_multimode_t5.py` / `_verify_multimode_t6.py` / `_verify_multimode_t45.py`：PVP 无敌人/无波次断言不受影响。
- 新增验证脚本 `_verify_multimode_t7.py` 覆盖：
  1. settings 新参数生效（间隔 3 / 上限 2 / 寿命 20）。
  2. PVP 中 `update()` 运行后道具列表非空（已启用）。
  3. P1 拾取生效、P2 拾取生效（分别 `try_pickup`）。
  4. P2 护盾/加速计时递减（`update_effects`）。
  5. PVP 仍无 enemy_tanks / 无波次推进。
  6. solo 道具参数与刷新行为一致。

## 范围外（YAGNI）

- 不做道具权重/掉落率（保持等概率三类型）。
- 不改变道具类型、图标、渲染。
- 不迁移冻结文件内的旧常量（无法修改，保留为未使用默认值）。
- PvPvE 模式本身仍保持菜单禁用状态（另有任务）。
