# -*- coding: utf-8 -*-
"""
玩家 2 坦克（车控模式）—— PVP / PvPvE 的第二位玩家。

仅覆写键位映射：方向键(↑↓=前后油门, ←→=转向) + 空格键(开火由 main 层处理)。
其余（物理/碰撞/弹药/道具/护盾/尾焰）全部继承 PlayerTank。
因父类 render 内硬编码 P1 配色，本子类整体覆写 render 以提供 P2 配色（蓝）。
"""
import math
import pygame
from entities.player_tank import PlayerTank

# P2 车身主色（区别于 P1 的红色），渲染偏蓝便于区分
COLOR_P2_TANK = (60, 90, 210)
COLOR_P2_OUTLINE = (10, 10, 60)


class Player2Tank(PlayerTank):
    """P2 坦克：方向键控制，继承 P1 全部能力。"""

    def handle_input(self, keys, dt: float, others=None) -> None:
        """车控模式：方向键 ↑↓=油门，←→=转向（与 P1 的 WASD 对称）。
        others: 同 PlayerTank，传入其它坦克用于互撞检测。"""
        throttle = 0.0
        if keys[pygame.K_UP]:
            throttle = 1.0
        elif keys[pygame.K_DOWN]:
            throttle = -1.0

        steering = 0.0
        if keys[pygame.K_LEFT]:
            steering = -1.0
        if keys[pygame.K_RIGHT]:
            steering = 1.0

        old_x, old_y = self.x, self.y
        self.physics.update_car(dt, throttle, steering)
        self.x = self.physics.x
        self.y = self.physics.y
        self._resolve_collision(old_x, old_y, dt, others)
        self.angle = self.physics.facing_angle
        self.rect.center = (round(self.x), round(self.y))

    def render(self, surface: pygame.Surface) -> None:
        """绘制坦克：与父类一致，但车身/描边使用 P2 配色。"""
        self._render_trail(surface)

        outline = max(2, self.rect.width // 10)
        barrel_length = self.rect.width * 0.65
        barrel_thickness = max(5, self.rect.width // 4)
        turret_radius = self.rect.width * 0.42

        canvas_size = int(self.rect.width + barrel_length * 2 + outline * 2)
        canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        ccx, ccy = canvas_size // 2, canvas_size // 2

        body_outer = pygame.Rect(0, 0, self.rect.width, self.rect.width)
        body_outer.center = (ccx, ccy)
        pygame.draw.rect(canvas, COLOR_P2_OUTLINE, body_outer)
        body_inner = body_outer.inflate(-outline * 2, -outline * 2)
        pygame.draw.rect(canvas, COLOR_P2_TANK, body_inner)

        barrel_rect = pygame.Rect(0, 0, barrel_thickness, int(barrel_length))
        barrel_rect.centerx = ccx
        barrel_rect.bottom = ccy
        pygame.draw.rect(canvas, COLOR_P2_OUTLINE, barrel_rect)
        pygame.draw.rect(canvas, COLOR_P2_TANK, barrel_rect.inflate(-outline, 0))

        pygame.draw.circle(canvas, COLOR_P2_OUTLINE, (ccx, ccy), int(turret_radius))
        pygame.draw.circle(canvas, COLOR_P2_TANK, (ccx, ccy), int(turret_radius - outline))

        rotated = pygame.transform.rotate(canvas, -math.degrees(self.angle))
        rotated_rect = rotated.get_rect(center=self.rect.center)
        surface.blit(rotated, rotated_rect)

        # 护盾光圈（与父类一致）
        if self.is_shielded:
            ring_radius = int(self.rect.width * 0.9)
            ring_rect = pygame.Rect(0, 0, ring_radius * 2, ring_radius * 2)
            ring_rect.center = self.rect.center
            pulse = 1.0
            shield_layer = pygame.Surface(ring_rect.size, pygame.SRCALPHA)
            ring_alpha = int(255 * pulse)
            pygame.draw.ellipse(shield_layer, (80, 160, 255, ring_alpha),
                                shield_layer.get_rect(),
                                max(2, self.rect.width // 12))
            surface.blit(shield_layer, ring_rect)
