# -*- coding: utf-8 -*-
"""
玩家 3 坦克（鼠标模式）—— 三人混战（pvp3）的第三位玩家。

操作口径（用户需求）：
  - 坦克中心每帧向鼠标位置移动（有停止半径，到达后停住不抖动）；
  - 炮管朝向鼠标（车体朝向即炮管朝向，与 P1/P2 语义一致）；
  - 鼠标左键点击一次发射一枚子弹（开火入口在 main 层 handle_events 处理）。

其余（物理/碰撞/弹药/道具/护盾/尾焰）全部继承 PlayerTank。
因父类 render 内硬编码 P1 配色，本子类整体覆写 render 以提供 P3 配色（绿）。
"""
import math
import pygame
from core.collision import rect_hits_obstacle
from core.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TANK_SIZE,
)
from entities.player_tank import PlayerTank

# P3 车身主色（区别于 P1 红 / P2 蓝），渲染偏绿便于区分
COLOR_P3_TANK = (46, 190, 92)
COLOR_P3_OUTLINE = (8, 46, 22)

# 鼠标跟车停止半径（倍率 * TANK_SIZE）：进入该半径后停住，防在鼠标点上抖动
MOUSE_STOP_RADIUS = 0.9

# 直线被墙挡时的绕行候选角（弧度，正负对称；夹角由小到大试，先贴墙滑行；
# 末尾补纯垂直方向，保证一格宽断头走廊里也能沿墙脱困不冻住）
MOUSE_AVOID_ANGLES = (
    0.3, -0.3, 0.6, -0.6, 0.9, -0.9,
    1.2, -1.2, 1.5, -1.5,
    math.pi / 2, -math.pi / 2,
)


class Player3Tank(PlayerTank):
    """P3 坦克：鼠标控制（跟随移动 + 朝向鼠标），继承 P1 全部能力。"""

    def _step_free(self, nx: float, ny: float, speed: float, dt: float) -> bool:
        """预演：沿 (nx,ny) 走一步后是否不撞墙（用于绕行方向选择）。"""
        test = self.rect.copy()
        test.center = (round(self.x + nx * speed * dt),
                       round(self.y + ny * speed * dt))
        return not rect_hits_obstacle(test, self.game_map)

    def handle_mouse_input(self, mouse_pos, dt: float, others=None) -> None:
        """鼠标控制：中心每帧移向鼠标；炮管（车体）朝向鼠标。

        mouse_pos: 鼠标在窗口内的像素坐标 (mx, my)。
           鼠标可能停在下方 UI 状态区，这里把 y 钳制回游戏区下边界，
           保证目标点始终落在战斗空间内。
        others: 同 PlayerTank，传入其它坦克用于互撞检测。
        """
        mx, my = mouse_pos
        # 鼠标可能停在窗口边缘/下方 UI 状态区，把目标点钳制回战斗空间
        mx = min(max(mx, 0.0), SCREEN_WIDTH - 1.0)
        my = min(max(my, 0.0), SCREEN_HEIGHT - 1.0)

        dx = mx - self.x
        dy = my - self.y
        dist = math.hypot(dx, dy)

        # 炮管朝向鼠标（车体角度即炮管角度：dx=sin a, dy=-cos a -> a=atan2(dx, -dy)）
        if dist > 1.0:
            self.angle = math.atan2(dx, -dy)
            self.physics.facing_angle = self.angle

        # 保存旧位置用于碰撞回退
        old_x, old_y = self.x, self.y

        stop_radius = TANK_SIZE * MOUSE_STOP_RADIUS
        if dist > stop_radius and dt > 0:
            # 本帧可移动距离：不超速；快到时按剩余距离走，避免过冲抖动
            speed = min(self.physics.max_speed, dist / dt)
            ux, uy = dx / dist, dy / dist
            # 直线被墙挡时按夹角由小到大试绕行方向（沿墙滑动，不会卡死）
            step_dir = None
            if self._step_free(ux, uy, speed, dt):
                step_dir = (ux, uy)
            else:
                for ang in MOUSE_AVOID_ANGLES:
                    ca, sa = math.cos(ang), math.sin(ang)
                    rx = ux * ca - uy * sa
                    ry = ux * sa + uy * ca
                    if self._step_free(rx, ry, speed, dt):
                        step_dir = (rx, ry)
                        break
            if step_dir is not None:
                nx, ny = step_dir
                self.x += nx * speed * dt
                self.y += ny * speed * dt
                self.physics.vx = nx * speed
                self.physics.vy = ny * speed
                self.physics.current_speed = speed
            else:
                # 四面都挡：原地停住（等鼠标换方向）
                self.physics.vx = 0.0
                self.physics.vy = 0.0
                self.physics.current_speed = 0.0
        else:
            self.physics.vx = 0.0
            self.physics.vy = 0.0
            self.physics.current_speed = 0.0

        # 碰撞检测 + 修正（others=其它坦克，用于坦克互撞）
        self._resolve_collision(old_x, old_y, dt, others)
        self.rect.center = (round(self.x), round(self.y))

    def render(self, surface: pygame.Surface) -> None:
        """绘制坦克：与父类一致，但车身/描边使用 P3 配色（绿）。"""
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
        pygame.draw.rect(canvas, COLOR_P3_OUTLINE, body_outer)
        body_inner = body_outer.inflate(-outline * 2, -outline * 2)
        pygame.draw.rect(canvas, COLOR_P3_TANK, body_inner)

        barrel_rect = pygame.Rect(0, 0, barrel_thickness, int(barrel_length))
        barrel_rect.centerx = ccx
        barrel_rect.bottom = ccy
        pygame.draw.rect(canvas, COLOR_P3_OUTLINE, barrel_rect)
        pygame.draw.rect(canvas, COLOR_P3_TANK, barrel_rect.inflate(-outline, 0))

        pygame.draw.circle(canvas, COLOR_P3_OUTLINE, (ccx, ccy), int(turret_radius))
        pygame.draw.circle(canvas, COLOR_P3_TANK, (ccx, ccy), int(turret_radius - outline))

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
