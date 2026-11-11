# -*- coding: utf-8 -*-
"""
瓦片类型定义
地图用二维数组表示，数组中的每个元素是下面枚举中的一个整数值。
当前阶段只区分"空地 / 砖墙 / 钢墙"，均不可破坏（后续如需可破坏砖墙，
可以在这里扩展新的类型而不影响现有结构）。
"""
from enum import IntEnum

class TileType(IntEnum):
    EMPTY = 0   # 空地，可通行
    BRICK = 1   # 砖墙，不可破坏（本阶段）
    STEEL = 2   # 钢墙，不可破坏