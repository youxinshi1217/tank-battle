# -*- coding: utf-8 -*-
"""
霰弹弹丸（Phase 5.4）
带独立弹夹的一次性散射弹丸：16 颗随机散射、小颗粒、初速略快、每颗独立反弹。
复用 Bullet 的移动/反弹逻辑，不改动冻结的 bullet.py；仅覆写尺寸与速度。
"""
import pygame

from core.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BULLET_MAX_BOUNCES,
    SHOTGUN_PELLET_SIZE,
    SHOTGUN_SPEED,
    COLOR_BULLET,
)
from core.collision import rect_hits_obstacle
from maps.game_map import GameMap
from entities.bullet import Bullet


class ShotgunPellet(Bullet):
    """霰弹弹丸：速度更快、体积更小，仍按全局 BULLET_MAX_BOUNCES(=2) 独立反弹。"""

    def __init__(self, x: float, y: float, dx: float, dy: float,
                 game_map: GameMap):
        self.game_map = game_map
        self.dx = dx
        self.dy = dy
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(0, 0, SHOTGUN_PELLET_SIZE, SHOTGUN_PELLET_SIZE)
        self.rect.center = (round(self.x), round(self.y))
        self.bounce_count = 0
        self.alive = True
        self.owner = "player"

    def update(self, dt: float) -> None:
        """速度固定为 SHOTGUN_SPEED（略快），反弹逻辑与 Bullet 相同、每颗独立计数。"""
        if not self.alive:
            return
        speed = SHOTGUN_SPEED
        distance = speed * dt
        half = SHOTGUN_PELLET_SIZE / 2

        # X 轴
        new_x = self.x + self.dx * distance
        hit_x_boundary = new_x - half < 0 or new_x + half > SCREEN_WIDTH
        if self.dx != 0:
            test_rect = self.rect.copy()
            clamped_x = min(max(new_x, half), SCREEN_WIDTH - half)
            test_rect.center = (round(clamped_x), round(self.y))
            hit_x_wall = rect_hits_obstacle(test_rect, self.game_map)
            if hit_x_boundary or hit_x_wall:
                self.dx = -self.dx
                self._register_bounce()
            else:
                self.x = new_x

        # Y 轴
        new_y = self.y + self.dy * distance
        hit_y_boundary = new_y - half < 0 or new_y + half > SCREEN_HEIGHT
        if self.dy != 0:
            test_rect = self.rect.copy()
            clamped_y = min(max(new_y, half), SCREEN_HEIGHT - half)
            test_rect.center = (round(self.x), round(clamped_y))
            hit_y_wall = rect_hits_obstacle(test_rect, self.game_map)
            if hit_y_boundary or hit_y_wall:
                self.dy = -self.dy
                self._register_bounce()
            else:
                self.y = new_y

        self.rect.center = (round(self.x), round(self.y))

    def render(self, surface) -> None:
        pygame.draw.rect(surface, COLOR_BULLET, self.rect)