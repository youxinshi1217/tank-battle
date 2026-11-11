# -*- coding: utf-8 -*-
"""
Stage 配置 - Stage 2「工业迷宫」
只保存引用（Map Data + Visual/Decoration + 玩家出生点 + 元信息）。
"""
from maps.map_02 import build_map_data, build_visual_data, build_decorations

STAGE_CONFIG = {
    "map_data": build_map_data,
    "visual_fn": build_visual_data,
    "deco_fn": build_decorations,
    "player_spawn": (2, 2),
    "bg": "关卡背景_2.png",   # 本关专属背景图（缺失时回退纯色底）
    "meta": {
        "id": "map_02",
        "name": "工业迷宫",
        "description": "单向深入废土工厂：入口厂区→仓库迷宫→机械核心→废墟出口，越走越深的攻防",
    },
}