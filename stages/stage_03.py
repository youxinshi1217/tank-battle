# -*- coding: utf-8 -*-
"""
Stage 配置 - Stage 3「军事攻坚 · 多枢纽区」
只保存引用（Map Data + Visual/Decoration + 玩家出生点 + 元信息）。
"""
from maps.map_03 import build_map_data, build_visual_data, build_decorations

STAGE_CONFIG = {
    "map_data": build_map_data,
    "visual_fn": build_visual_data,
    "deco_fn": build_decorations,
    "player_spawn": (2, 2),
    "bg": "关卡背景_3.png",   # 本关专属背景图（缺失时回退纯色底）
    "meta": {
        "id": "map_03",
        "name": "军事攻坚",
        "description": "多枢纽要塞：中央指挥广场（营墙围环+纪念碑）四方门户，四角高地/装甲/军火/防空阵地，远距对射+掩体节点",
    },
}