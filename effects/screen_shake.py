# -*- coding: utf-8 -*-
"""屏幕震动控制器（表现层，纯数学，无渲染依赖）。

设计：trauma 模型。
  - add_trauma(amount)：爆炸生成时调用，累加震动强度（上限 1.0）。
  - update(dt)：trauma 随时间线性衰减至 0。
  - offset()：返回当前帧应施加到"游戏区整体贴图"上的 (dx, dy) 位移。
    位移幅度 = trauma^2 * 最大位移（小震频繁、大震稀有，手感更自然），
    方向由多个不同频率的正弦叠加得到平滑抖动（避免每帧纯随机的刺眼闪烁）。

接线方式（由 main.py 负责，本模块不碰主循环）：
  1) Game.__init__:        self.shake = CameraShake()
  2) 爆炸生成时:           self.shake.add_trauma(Explosion.TRAUMA)   # 玩家被毁可乘 1.8
  3) update 每帧:          self.shake.update(dt)
  4) render 末尾:          先把"游戏世界"（地图/坦克/子弹/特效）画到一张临时画布
     world_surface，再以 self.shake.offset() 为左上角偏移，把 world_surface 贴回
     self.screen；游戏区抖、底部 UI 区不抖（UI 直接画到 self.screen）。
"""

import math


class CameraShake:
    """屏幕震动：trauma 累加、随时间衰减，offset() 给出本帧位移。"""

    def __init__(self, max_offset: float = 10.0, decay: float = 1.8):
        self._trauma = 0.0          # 当前震动强度 0~1
        self._max = float(max_offset)   # trauma=1 时的最大位移（px）
        self._decay = float(decay)      # 每秒衰减量
        self._t = 0.0                  # 累计时间（用于平滑抖动相位）

    def add_trauma(self, amount: float) -> None:
        """累加震动强度（与现有值相加后钳制到 1.0）。"""
        self._trauma = min(1.0, self._trauma + float(amount))

    def update(self, dt: float) -> None:
        """每帧衰减 trauma；dt<=0 时跳过。"""
        if dt > 0:
            self._trauma = max(0.0, self._trauma - self._decay * dt)
            self._t += dt

    def offset(self):
        """当前帧位移 (dx, dy)；无震动时返回 (0, 0)。"""
        if self._trauma <= 0.0:
            return (0, 0)
        mag = self._trauma * self._trauma * self._max
        # 多频正弦叠加 -> 平滑且不规则的抖动，比每帧纯随机自然
        ox = mag * (0.5 * math.sin(self._t * 53.0) + 0.5 * math.sin(self._t * 91.0))
        oy = mag * (0.5 * math.cos(self._t * 47.0) + 0.5 * math.cos(self._t * 83.0))
        return (int(ox), int(oy))
