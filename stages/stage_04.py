# -*- coding: utf-8 -*-
"""
Stage 配置 - Stage 4「决战要塞」
只保存引用（Map Data + Visual/Decoration + 玩家出生点 + 元信息）。
"""
from maps.map_04 import build_map_data, build_visual_data, build_decorations

STAGE_CONFIG = {
    "map_data": build_map_data,
    "visual_fn": build_visual_data,
    "deco_fn": build_decorations,
    "player_spawn": (2, 2),
    "bg": "关卡背景_4.png",   # 本关专属背景图（缺失时回退纯色底）
    "meta": {
        "id": "map_04",
        "name": "决战要塞",
        "description": "高密度+STEEL核心的最终决战：四向正面大道直插钢铁要塞，LJR 指挥核心被冷钢壳合围",
    },
}
