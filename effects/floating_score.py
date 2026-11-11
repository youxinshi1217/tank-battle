# -*- coding: utf-8 -*-
"""
Phase 7.1 - Floating Score（世界空间分数飘字反馈）

定位：世界空间表现层（不属于 HUD / 不属于玩家面板）。
职责：敌人被击毁时，在其死亡位置弹出 +1/+2/+3 分数飘字；
      向上移动、透明度降低、生命周期结束删除。纯显示，不含任何玩法逻辑。

数据来源（创建时传入，不读取游戏状态）：
  - value    击杀分值（+1 / +2 / +3）
  - position 出生位置（敌人被击毁时的 rect.center）

第一版规则（刻意保持简单，禁止扩展）：
  - 仅"上浮 + 淡出 + 生命周期结束删除"
  - 不加入：缩放动画 / 颜色变化 / 粒子效果 / 音效 / Combo / 连杀
"""

import pygame

from core.game_fonts import game_font


class FloatingScore:
    """世界空间分数飘字：在出生位置显示 +value，上浮并淡出后自动移除。"""

    RISE_SPEED = 40       # 上浮速度（px/s）
    LIFETIME = 1.0        # 存活时长（秒）
    COLOR = (255, 255, 0)  # 亮黄色，地图上醒目

    def __init__(self, value: int, position, font_size: int = 24):
        self.value = int(value)
        self._x, self._y = float(position[0]), float(position[1])
        self._age = 0.0
        self.alive = True
        # 字体资源（仅数字/符号，consolas 足够）；创建即生成静态文字表面
        self._font = game_font(font_size)
        self._text = self._font.render(f"+{self.value}", True, self.COLOR)

    @property
    def position(self):
        """当前坐标（用于验证）。"""
        return int(self._x), int(self._y)

    def update(self, dt: float) -> None:
        """帧推进：上浮 + 累计寿命，达到 LIFETIME 后标记移除。"""
        if not self.alive:
            return
        self._age += dt
        self._y -= self.RISE_SPEED * dt
        if self._age >= self.LIFETIME:
            self.alive = False

    def render(self, surface: "pygame.Surface") -> None:
        """绘制飘字：按剩余寿命线性淡出。已移除则跳过。"""
        if not self.alive:
            return
        ratio = max(0.0, 1.0 - self._age / self.LIFETIME)
        surf = self._text.copy()
        surf.set_alpha(int(255 * ratio))
        rect = surf.get_rect(center=(int(self._x), int(self._y)))
        surface.blit(surf, rect)
