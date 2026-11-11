# -*- coding: utf-8 -*-
"""
Phase 5.4.2 - Item Spawn Manager（道具刷新管理器）
负责"何时 / 何地 / 同时存在几个"道具的决策，将道具生成逻辑从主循环中独立出来。

设计边界（对齐 enemy_spawn_manager 的结构思想，但不修改它）：
  - 只负责道具生成计时、数量上限、合法刷新点选择、生命周期清理。
  - 不实例化具体效果；拾取时仅转发到 Item.apply(player) -> player.apply_item_effect()。

本阶段明确不做（Phase 5.4 边界）：
  - 不做掉落算法 / 概率权重（类型为等概率随机选择）。
  - 不支持多个道具同时存在（active_items <= 1）。
  - 不接 main.py（接线在后续子阶段）。
  - 不实现具体道具效果。
"""
import random

import pygame

from core.collision import rect_hits_obstacle
from core.settings import GRID_SIZE, TILE_SIZE
from core import spawn_rules
from entities.item import ITEM_SIZE, Item, ItemType
from maps.tile import TileType


# ------------------------------------------------------------------
# 道具刷新参数（沿用 "局部常量 + 注释说明"，后续可整体迁移到 core.settings）
# ------------------------------------------------------------------
ITEM_SPAWN_INTERVAL = 5.0    # 刷新检测间隔（秒）
ITEM_MAX_ACTIVE = 1          # 场上同时存在的道具数量上限
PLAYER_SPAWN_TILE = (3, 3)   # 玩家出生点格子 (row, col)，不可在此生成道具


class ItemSpawnManager:
    """控制道具刷新节奏、数量上限、合法刷新点与生命周期清理。

    流程：
      spawn(计时达标且未达上限)
        -> 选合法刷新点（空地 / 不越界 / 不撞障碍 / 不重叠玩家与敌人 / 避开出生点）
        -> 生成 Item 加入 self.items
      update(dt)
        -> 推进每个 Item 生命周期，清理过期 item
        -> 若未达上限，累加刷新计时，达标时尝试生成
      try_pickup(player)
        -> 检测玩家矩形与 Item 相交，收集并移除（效果转发到 item.apply）
    """

    def __init__(self, game_map,
                 spawn_interval: float = ITEM_SPAWN_INTERVAL,
                 max_active: int = ITEM_MAX_ACTIVE,
                 item_size: int = ITEM_SIZE,
                 player_spawn_tile=PLAYER_SPAWN_TILE):
        self.game_map = game_map
        self.spawn_interval = spawn_interval
        self.max_active = max_active
        self.item_size = item_size
        self.player_spawn_tile = tuple(player_spawn_tile)

        # 运行时状态
        self.time_elapsed = 0.0
        self.items: list = []

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def update(self, dt: float, player_rect=None, enemy_rects=None) -> None:
        """推进道具生命周期，并按间隔尝试刷新。

        Args:
            dt:          帧时长（秒）。
            player_rect: 玩家矩形（用于刷新点避让）。None 表示未提供（跳过重叠检测）。
            enemy_rects: 敌人矩形列表（用于刷新点避让）。None 表示未提供。
        """
        # 1) 生命周期推进 + 清理过期 item
        for it in self.items[:]:
            it.update(dt)
        self.items = [it for it in self.items if it.alive]

        # 2) 刷新调度：未达上限才累加计时
        if len(self.items) >= self.max_active:
            self.time_elapsed = 0.0
            return
        self.time_elapsed += dt
        if self.time_elapsed < self.spawn_interval:
            return

        # 3) 达到刷新间隔：尝试生成一个
        self.time_elapsed = 0.0
        item = self._spawn_one(player_rect, enemy_rects or [])
        if item is not None:
            self.items.append(item)

    def try_pickup(self, player) -> list:
        """检测玩家与 Item 的碰撞拾取。

        对相交且存活的 Item：调用 item.apply(player)（转发到玩家效果接口），
        并标记移除。返回本次实际拾取的类型列表。
        """
        collected = []
        kept = []
        for it in self.items:
            if it.alive and it.rect.colliderect(player.rect):
                it.apply(player)      # 只做接口转发，不实现具体效果
                collected.append(it.item_type)
                continue
            kept.append(it)
        self.items = kept
        return collected

    def reset(self) -> None:
        """重置刷新状态（重新开局 / 重玩）。"""
        self.time_elapsed = 0.0
        self.items = []

    # ------------------------------------------------------------------
    # 内部：刷新点
    # ------------------------------------------------------------------
    def _choose_type(self):
        """等概率随机选择一种道具类型（阶段内四种；不做权重）。"""
        return random.choice([ItemType.SHOTGUN, ItemType.SHIELD,
                              ItemType.SPEED, ItemType.LASER])

    def _spawn_one(self, player_rect, enemy_rects):
        """尝试刷新一个道具：找到合法中心点后创建 Item；失败返回 None。"""
        pos = self._find_spawn_position(player_rect, enemy_rects)
        if pos is None:
            return None
        cx, cy = pos
        item = Item(cx, cy, self._choose_type())
        self._bind_density(item)
        return item

    def _bind_density(self, item):
        """保留钩子：后续如需调节道具密度分布可在此处理。（当前为空实现。）"""
        return item

    def _find_spawn_position(self, player_rect, enemy_rects):
        """随机找一个合法刷新点（50 次尝试，失败返回 None）。

        约束：
          - 空地 TileType.EMPTY
          - 不越界
          - 不碰撞障碍物
          - 不与玩家矩形重叠
          - 不与敌人矩形重叠
          - 不位于玩家出生点 player_spawn_tile
        """
        sr, sc = self.player_spawn_tile
        for _ in range(50):
            col = random.randint(0, GRID_SIZE - 1)
            row = random.randint(0, GRID_SIZE - 1)
            # 跳过玩家出生点
            if (row, col) == (sr, sc):
                continue
            # 空地
            if self.game_map.get_tile(row, col) != TileType.EMPTY:
                continue
            # Phase 8.3：LJR Protected Zone 生成限制（统一经 spawn_rules）
            if spawn_rules.is_spawn_blocked(row, col):
                continue
            cx = col * TILE_SIZE + TILE_SIZE / 2
            cy = row * TILE_SIZE + TILE_SIZE / 2
            test_rect = pygame.Rect(0, 0, self.item_size, self.item_size)
            test_rect.center = (cx, cy)
            # 不碰撞障碍物
            if rect_hits_obstacle(test_rect, self.game_map):
                continue
            # 不与玩家重叠
            if player_rect is not None and test_rect.colliderect(player_rect):
                continue
            # 不与敌人重叠
            if any(test_rect.colliderect(er) for er in enemy_rects):
                continue
            return (cx, cy)
        return None