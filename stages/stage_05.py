# -*- coding: utf-8 -*-
"""
Stage 配置 - Stage 5「戈壁环岛」
只保存引用（Map Data + Visual/Decoration + 形状层 + 玩家出生点 + 元信息）。

背景 bg 留空字符串：本关背景由地图自身形状层与底色承担（沙洲/钢球/LJR水印
都是绘制在战场底色上的），复用通用底色即可，避免图片缺失带来的额外风险。
若后续要专属沙漠黄昏背景图，把文件名填进来即可（见 main._load_level_bg_for_stage）。
"""
from maps.map_05 import (
    build_map_data,
    build_visual_data,
    build_decorations,
    build_shapes,
    build_geometry,
)

STAGE_CONFIG = {
    "map_data": build_map_data,
    "visual_fn": build_visual_data,
    "deco_fn": build_decorations,
    "shape_fn": build_shapes,
    "geometry_fn": build_geometry,
    "player_spawn": (2, 2),
    "bg": "",                # 本关无专属背景图，用通用底色
    "meta": {
        "id": "map_05",
        "name": "戈壁环岛",
        "description": "完整环形沙洲 + 8 条完全等宽缺口通道（净宽 96px，"
                       "可并排 3.8 辆坦克）+ 缺口正前方钢球（球与沙洲缝隙 "
                       "46px / 56px，均超 1.5 辆坦克）；连续几何碰撞，"
                       "圆即圆、不放大；中央湖心广场直径 403px，"
                       "专为追踪导弹躲避而设计",
    },
}
