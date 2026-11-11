# -*- coding: utf-8 -*-
"""
子弹（PVP 双人模式：玩家子弹，支持反弹）
"""
import pygame
from core.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BULLET_SIZE,
    BULLET_SPEED,
    BULLET_MAX_BOUNCES,
    COLOR_BULLET,
)
from core.collision import rect_hits_obstacle
from maps.game_map import GameMap

class Bullet:
    def __init__(self, x: float, y: float, dx: float, dy: float,
                 game_map: GameMap, owner: str = "player"):
        """
        owner: "player"/"p1"/"p2" 区分发射者（PVP 归属判定用）
        """
        self.game_map = game_map
        self.dx = dx
        self.dy = dy
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(0, 0, BULLET_SIZE, BULLET_SIZE)
        self.rect.center = (round(self.x), round(self.y))
        self.bounce_count = 0
        self.alive = True
        self.owner = owner  # "player" / "p1" / "p2"
        self.emitter = None  # 子弹归属实体（保留字段）

    # ------------------------------------------------------------------
    # 更新逻辑
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if not self.alive:
            return
        # 统一子弹速度（PVP 无双速敌我）
        speed = BULLET_SPEED
        distance = speed * dt
        half = BULLET_SIZE / 2

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

    def _register_bounce(self) -> None:
        self.bounce_count += 1
        if self.bounce_count > BULLET_MAX_BOUNCES:
            self.alive = False

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        color = COLOR_BULLET
        pygame.draw.rect(surface, color, self.rect)