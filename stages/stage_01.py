# -*- coding: utf-8 -*-
"""
Stage 配置 - Stage 1
只保存引用（Map Data + Visual + 玩家出生点），不保存大量数据。

导出声明：
  STAGE_CONFIG - 当前 Stage 的配置字典，供 main.py 的 STAGES 列表引用
                （PVP 双人模式选图用）。

字段：
  map_data      : map_XX.build_map_data 函数引用（调用返回 (grid, is_decorative)）
  visual_fn     : map_XX.build_visual_data 函数引用（返回区域配色，可选）
  player_spawn  : 玩家出生点格子 (row, col)
  meta          : 地图元信息（id/name/description，展示用）
"""
from maps.map_01 import build_map_data, build_visual_data

STAGE_CONFIG = {
    "map_data": build_map_data,
    "visual_fn": build_visual_data,
    "player_spawn": (3, 3),   # (row, col)
    "bg": "关卡背景_1.png",   # 本关专属背景图（位于项目根目录；缺失时回退纯色底）
    "meta": {
        "id": "map_01",
        "name": "钢铁废墟",
        "description": "围绕中央控制核心展开的攻防战场：中路核心争夺，左右工业/军事包抄",
    },
}