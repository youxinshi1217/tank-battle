# -*- coding: utf-8 -*-
"""
方向定义
坦克的移动方向 / 朝向共用同一套枚举。每个方向附带一个 (dx, dy) 单位向量，
方便移动计算时直接使用。
"""
from enum import Enum

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]