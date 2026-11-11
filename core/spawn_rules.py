# -*- coding: utf-8 -*-
"""
Phase 8.3 - 统一 Spawn 限制规则

职责：
  道具（与 PVP 双玩家出生逻辑）的生成限制统一通过本层判定，不各自实现。

结构：
  ItemSpawnManager ─┴─> spawn_rules ──> maps.ljr_zone

提供：
  is_spawn_blocked(r, c) -> bool
    当前仅判定 LJR Protected Zone；未来如需扩展其它限制，在此集中维护。
"""
from maps import ljr_zone


def is_spawn_blocked(r, c, origin=None):
    """判定 (row, col) 是否禁止任何实体生成。

    现状：LJR Protected Zone 为唯一生成限制区（禁 spawn / item / player）。
    origin 缺省使用 Stage 1 的 LJR 原点。
    """
    if origin is None:
        origin = ljr_zone.DEFAULT_ORIGIN
    return ljr_zone.is_ljr_protected(r, c, origin)