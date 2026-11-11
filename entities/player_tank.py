# -*- coding: utf-8 -*-
"""
玩家坦克（车控模式：W/S=前后，A/D=转向）
使用 TankPhysics.update_car() 实现 throttle + steering 物理。
"""
import math
import random

import pygame
from core.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TANK_SIZE,
    TANK_SPEED,
    COLOR_PLAYER_TANK,
    COLOR_PLAYER_OUTLINE,
    COLOR_SHIELD_RING,
    MAGAZINE_CAPACITY,
    RELOAD_DURATION,
    COLOR_AMMO_FULL,
    COLOR_AMMO_EMPTY,
    COLOR_AMMO_RELOADING,
    PHYSICS_ACCEL,
    PHYSICS_FRICTION,
    PHYSICS_TURN_SPEED,
    BRAKE_DECELERATION,
    REVERSE_SPEED_LIMIT,
    SHOTGUN_MAGAZINE,
    REVERSE_ACCEL_FACTOR,
    MISSILE_MAGAZINE,
)
from core.collision import rect_hits_obstacle
from core.tank_physics import TankPhysics
from maps.game_map import GameMap
from entities.item import ItemType


# ------------------------------------------------------------------
# 道具效果默认参数 (Phase 5.4.1)
# 本阶段仅作接口/状态记账，不实现具体效果。
# ------------------------------------------------------------------
SHIELD_DURATION = 10.0        # 护盾持续（秒）
SPEED_DURATION = 15.0         # 加速持续（秒）
SPEED_MULTIPLIER = 1.333      # 加速倍率（原 2.0；比现在慢 1.5 倍 = 2.0/1.5≈1.333，加速后最高速约基础×1.333）

# ------------------------------------------------------------------
# Phase 6.6 护盾警告反馈：剩余 <= SHIELD_WARN_SECONDS 进入"呼吸灯"透明警告
#  - 纯表现层，不改护盾持续时间 / 免伤逻辑 / 拾取逻辑
#  - 呼吸周期固定（不越来越快），透明度在 [PULSE_MIN, 1.0] 间正弦平滑循环
# ------------------------------------------------------------------
SHIELD_WARN_SECONDS = 5.0      # 剩余时间 <=5s 进入警告状态
SHIELD_BREATHE_PERIOD = 800.0  # 一个呼吸循环时长（毫秒）
SHIELD_PULSE_MIN = 0.65        # 呼吸最低透明度系数（不低于此值，避免突然消失）

# 加速尾焰粒子参数（Phase 5.4 视觉特效，纯渲染，不改物理/碰撞）
TRAIL_MAX_PARTICLES = 110      # 粒子数量上限（防止无界增长）
TRAIL_PARTICLES_PER_FRAME = 2   # 每束每帧向尾部喷射的粒子数
TRAIL_SPAWN_BACK = 0.55        # 发射点距车体中心的距离（倍率 * TANK_SIZE）
TRAIL_EJECT_SPEED = 260        # 粒子向后喷射的初速（像素/秒，远快于车速，营造"跑得飞快"）
TRAIL_LIFE = 0.45              # 每颗粒子存活时长（秒）
TRAIL_LANE_OFFSETS = (-0.80, 0.0, 0.80)  # 三束气流：左/中/右（倍率 * TANK_SIZE/2 的侧向偏移）
TRAIL_LANE_JITTER = 1.6        # 每束内部的随机左右抖动幅度（像素）


class PlayerTank:
    def __init__(self, x: float, y: float, game_map: GameMap):
        """x, y 为坦克中心点的初始像素坐标。"""
        self.game_map = game_map
        # 物理系统（车控模式）
        self.physics = TankPhysics(
            x=float(x),
            y=float(y),
            max_speed=TANK_SPEED,
            accel=PHYSICS_ACCEL,
            turn_speed=PHYSICS_TURN_SPEED,
            friction=PHYSICS_FRICTION,
            brake_decel=BRAKE_DECELERATION,
        )
        # 渲染用角度（同步自 physics.facing_angle）
        self.angle = 0.0
        # 用浮点数存坐标
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        self.rect.center = (round(self.x), round(self.y))
        # 弹药（弹匣）状态：出生时满弹
        self.ammo = MAGAZINE_CAPACITY
        self.reload_remaining = 0.0

        # ---- 道具效果状态 (Phase 5.4.1)：仅记账，不生效 ----
        self.shield_remaining = 0.0        # 护盾剩余秒数（0=无）
        self.speed_remaining = 0.0         # 加速剩余秒数（0=无）
        self.speed_multiplier = 1.0        # 速度倍率（本阶段仅记录）
        self.shotgun_ammo = 0                # 霰弹独立弹夹剩余次数（0=无霰弹模式）
        self.laser_charged = False           # 激光充能（拾取后一次性持有，直到发射）
        self.missile_ammo = 0                 # 追踪导弹剩余发数（拾取 +MISSILE_MAGAZINE，可累计）
        self._base_max_speed = TANK_SPEED  # 基础最大速度（加速结束时恢复）

        # 加速尾焰粒子缓存（dict: x, y, vx, vy, life, ttl, size, color）
        self.trail_particles = []

    # ------------------------------------------------------------------
    # 弹药 / 开火
    # ------------------------------------------------------------------
    def update_ammo(self, dt: float) -> None:
        """更新重装倒计时。每帧调用一次，重装完成后弹药恢复满弹匣。"""
        if self.reload_remaining > 0:
            self.reload_remaining -= dt
            if self.reload_remaining <= 0:
                self.reload_remaining = 0.0
                self.ammo = MAGAZINE_CAPACITY

    def can_fire(self) -> bool:
        return self.ammo > 0 and self.reload_remaining <= 0

    def consume_ammo(self) -> None:
        """发射一发后调用：扣除1发弹药；若弹药归零则立即开始重装。"""
        self.ammo -= 1
        if self.ammo <= 0:
            self.ammo = 0
            self.reload_remaining = RELOAD_DURATION

    @property
    def is_reloading(self) -> bool:
        return self.reload_remaining > 0

    # ------------------------------------------------------------------
    # 道具效果接口 (Phase 5.4.1)
    # 分发 + 状态记账。具体效果逐项落地：
    #   SHIELD  → 已实现（Phase 5.4.4，见下方）
    #   SPEED   → 已实现（移速倍率 + 尾焰）
    #   SHOTGUN → 已实现（独立弹夹散射）
    #   LASER   → 一次性充能（虚线预览弹道 + 快速射线，发射后失效）
    #   MISSILE → 追踪导弹（拾取 +MISSILE_MAGAZINE 发，可累计，发射后追踪最近坦克）
    # ------------------------------------------------------------------
    def apply_item_effect(self, item_type) -> None:
        """道具拾取效果分发接口：只负责按类型分发，不实现具体效果。"""
        if item_type == ItemType.SHIELD:
            self.apply_shield()
        elif item_type == ItemType.SPEED:
            self.apply_speed()
        elif item_type == ItemType.SHOTGUN:
            self.queue_shotgun()
        elif item_type == ItemType.LASER:
            self.charge_laser()
        elif item_type == ItemType.MISSILE:
            self.charge_missile()

    def charge_laser(self) -> None:
        """拾取激光道具：获得一次性充能，永久持有直到发射（不占弹匣、不受时间限制）。"""
        self.laser_charged = True

    def charge_missile(self) -> None:
        """拾取追踪导弹道具：获得 MISSILE_MAGAZINE 发追踪弹（可累计叠加、不封顶）。"""
        self.missile_ammo += MISSILE_MAGAZINE

    def apply_shield(self) -> None:
        """记录护盾状态。（免伤逻辑本阶段不实现。）"""
        self.shield_remaining = SHIELD_DURATION

    def apply_speed(self) -> None:
        """记录加速状态。（移速修改本阶段不实现，倍率仅记录。）"""
        self.speed_remaining = SPEED_DURATION
        self.speed_multiplier = SPEED_MULTIPLIER

    def queue_shotgun(self) -> None:
        """拾取霰弹道具：霰弹独立弹夹次数叠加（再捡一个 +SHOTGUN_MAGAZINE 次，
        可累计、不封顶）。"""
        self.shotgun_ammo += SHOTGUN_MAGAZINE

    @property
    def shotgun_active(self) -> bool:
        """霰弹模式是否生效中（独立弹夹还有剩余次数）。"""
        return self.shotgun_ammo > 0

    def consume_shotgun_ammo(self) -> None:
        """霰弹开火后扣除 1 次；归零即失效（不再散射，回普通开火）。"""
        if self.shotgun_ammo > 0:
            self.shotgun_ammo -= 1

    @property
    def missile_active(self) -> bool:
        """是否持有追踪弹（剩余发数 > 0）。"""
        return self.missile_ammo > 0

    def consume_missile_ammo(self) -> None:
        """发射追踪弹后扣除 1 发；归零即失效（回普通开火）。"""
        if self.missile_ammo > 0:
            self.missile_ammo -= 1

    def update_effects(self, dt: float) -> None:
        """推进道具计时：护盾 / 加速剩余时间各减去 dt，直至归零。
        同时按 speed_remaining 实时施加/恢复 physics.max_speed（实例级，不改 physics 文件/常量）。"""
        if self.shield_remaining > 0:
            self.shield_remaining = max(0.0, self.shield_remaining - dt)
        if self.speed_remaining > 0:
            self.speed_remaining = max(0.0, self.speed_remaining - dt)
        # 加速生效：当前限速 = 基础速 × 倍率；结束即恢复基础速
        if self.speed_remaining > 0:
            self.physics.max_speed = self._base_max_speed * self.speed_multiplier
        else:
            self.physics.max_speed = self._base_max_speed

        # 加速尾焰粒子：推进 + 按条件向尾部喷射（纯视觉，每帧随主循环调用）
        self._update_trail(dt)

    # ------------------------------------------------------------------
    # 加速尾焰粒子（纯视觉特效）
    # 发射条件：加速生效中 且 坦克确实在向前移动（用速度在朝向上的投影判断，
    # 避免原地转向/倒车也乱喷）。粒子从尾部向后方高速喷射、扩散并淡出。
    # ------------------------------------------------------------------
    def _is_moving_forward(self) -> bool:
        dx = math.sin(self.angle)
        dy = -math.cos(self.angle)
        forward_speed = self.physics.vx * dx + self.physics.vy * dy
        return forward_speed > 12.0

    def _update_trail(self, dt: float) -> None:
        # 1) 发新粒子：每条气流束（左/中/右）各自持续喷出一簇粒子
        if self.speed_remaining > 0 and self._is_moving_forward():
            for lane in TRAIL_LANE_OFFSETS:
                for _ in range(TRAIL_PARTICLES_PER_FRAME):
                    self._emit_trail_particle(lane)

        # 2) 推进已有粒子：向后飞 + 侧向扩散 + 轻微衰减 + 淡出
        remaining = []
        for p in self.trail_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.96   # 缓慢减速，形成拖尾感
            p["vy"] *= 0.96
            p["vy"] += 40 * dt  # 轻微下沉，更有"喷出后飘散"的感觉
            p["life"] -= dt
            if p["life"] > 0:
                remaining.append(p)
        # 3) 数量上限保护（From 最旧的丢弃）
        if len(remaining) > TRAIL_MAX_PARTICLES:
            del remaining[: len(remaining) - TRAIL_MAX_PARTICLES]
        self.trail_particles = remaining

    def _emit_trail_particle(self, lane: float) -> None:
        dx = math.sin(self.angle)
        dy = -math.cos(self.angle)
        # 侧向单位向量：(-dy, dx)
        side_x, side_y = -dy, dx
        # 束内抖动：在该束基准左右偏移上加入随机抖动
        jitter = random.uniform(-TRAIL_LANE_JITTER, TRAIL_LANE_JITTER)
        lateral = lane * (TANK_SIZE / 2) + jitter

        # 发射点：车体中心向正后方偏出（尾部），并沿侧向拉开到对应气流束
        back = TANK_SIZE * TRAIL_SPAWN_BACK
        px = self.x - dx * back + side_x * lateral
        py = self.y - dy * back + side_y * lateral

        # 初速：主要沿 -facing 向后喷出，附带随机侧向扩散
        spd = random.uniform(0.7, 1.35) * TRAIL_EJECT_SPEED
        vx = -dx * spd + side_x * random.uniform(-90, 90)
        vy = -dy * spd + side_y * random.uniform(-90, 90)

        # 青蓝粒子：随机轻微明暗差异
        bright = random.randint(-30, 20)
        color = (
            min(170, 30 + bright),
            min(255, 180 + bright),
            min(255, 255),
        )
        self.trail_particles.append({
            "x": px, "y": py,
            "vx": vx, "vy": vy,
            "life": TRAIL_LIFE, "ttl": TRAIL_LIFE,
            "size": random.randint(2, 5),
            "color": color,
        })

    # ------------------------------------------------------------------
    # 道具效果：SHIELD（Phase 5.4.4 首个真实道具）
    # 语义：拾取后 10 秒内完全免疫敌方伤害，10 秒后自动失效。
    #   - 免伤期间不消耗护盾时间（非一次性格挡）
    #   - 无护盾次数 / 无 HP 系统 / 不新增伤害系统
    # 死亡流程仍归 main 层：本方法只返回伤害判定结果，不触发 GAME OVER。
    # ------------------------------------------------------------------
    @property
    def is_shielded(self) -> bool:
        """护盾是否生效中：剩余有效时间 > 0。"""
        return self.shield_remaining > 0

    def handle_enemy_hit(self) -> bool:
        """玩家受到敌方子弹命中的伤害判定接口。

        Returns:
            True  : 本次命中被护盾完全免疫 → 玩家存活，护盾时间不消耗。
            False : 无护盾 → 命中生效，交由调用方执行原死亡逻辑。

        注意：本方法不触发 GAME OVER（死亡判定由 main 层控制）。
        """
        return self.is_shielded

    # ------------------------------------------------------------------
    # 更新逻辑（车控模式）
    # ------------------------------------------------------------------
    def handle_input(self, keys, dt: float, others=None) -> None:
        """车控模式：W/S=前后油门，A/D=转向，调用 physics.update_car()。
        others: 其它"实体坦克"对象列表（P2 / 敌方），用于坦克互撞检测。"""
        # ---- 输入合成 ----
        throttle = 0.0
        if keys[pygame.K_w]:
            throttle = 1.0
        elif keys[pygame.K_s]:
            throttle = -1.0

        steering = 0.0
        if keys[pygame.K_a]:
            steering = -1.0
        if keys[pygame.K_d]:
            steering = 1.0

        # 保存旧位置用于碰撞回退
        old_x, old_y = self.x, self.y

        # 物理更新（车控模式）
        self.physics.update_car(dt, throttle, steering)

        # 同步坐标
        self.x = self.physics.x
        self.y = self.physics.y

        # 碰撞检测 + 修正（others=其它坦克，用于坦克互撞）
        self._resolve_collision(old_x, old_y, dt, others)

        # 同步渲染角度
        self.angle = self.physics.facing_angle
        self.rect.center = (round(self.x), round(self.y))

    def _resolve_collision(self, old_x: float, old_y: float, dt: float, others=None) -> None:
        """碰撞处理：回退到旧位置 + 清零轴向速度。
        others: 其它实体坦克列表，用于"坦克互撞"——把对方当成一堵会动的墙。
        """
        half = TANK_SIZE / 2

        # X 轴检测
        test_rect = self.rect.copy()
        test_rect.centerx = round(self.x)
        if rect_hits_obstacle(test_rect, self.game_map):
            self.x = old_x
            self.physics.vx = 0.0

        # Y 轴检测
        test_rect = self.rect.copy()
        test_rect.centery = round(self.y)
        if rect_hits_obstacle(test_rect, self.game_map):
            self.y = old_y
            self.physics.vy = 0.0

        # 屏幕边界约束
        self.x = min(max(self.x, half), SCREEN_WIDTH - half)
        self.y = min(max(self.y, half), SCREEN_HEIGHT - half)

        # 先把候选位置同步到 rect，才能正确做"坦克 vs 坦克"的矩形重叠判定。
        # （进入本函数时 self.rect 仍是上一帧末的位置，必须先更新到本次候选位置。）
        self.rect.center = (round(self.x), round(self.y))

        # 坦克互撞：把其它坦克当成一堵会动的墙。
        # 用现有 self.rect（= 坦克尺寸正方形）作为碰撞体积，与对方矩形重叠即退回原位。
        if others:
            for other in others:
                if other is self:
                    continue
                if self.rect.colliderect(other.rect):
                    self.x = old_x
                    self.y = old_y
                    self.physics.vx = 0.0
                    self.physics.vy = 0.0
                    self.rect.center = (round(self.x), round(self.y))
                    break

        # 同步回 physics
        self.physics.x = self.x
        self.physics.y = self.y
        self.rect.center = (round(self.x), round(self.y))

    def get_muzzle_position(self):
        """返回当前朝向下炮管末端的像素坐标。"""
        cx, cy = self.rect.center
        barrel_length = TANK_SIZE * 0.65
        dx = math.sin(self.angle)
        dy = -math.cos(self.angle)
        muzzle_x = cx + dx * barrel_length
        muzzle_y = cy + dy * barrel_length
        return muzzle_x, muzzle_y

    def get_direction_vector(self):
        """返回当前朝向对应的单位向量 (dx, dy)。"""
        return math.sin(self.angle), -math.cos(self.angle)

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        """绘制坦克：车身+炮塔+炮管。"""
        # 加速尾焰粒子先画（在车身下方，气流从车尾喷出）
        self._render_trail(surface)

        outline = max(2, TANK_SIZE // 10)
        barrel_length = TANK_SIZE * 0.65
        barrel_thickness = max(5, TANK_SIZE // 4)
        turret_radius = TANK_SIZE * 0.42

        canvas_size = int(TANK_SIZE + barrel_length * 2 + outline * 2)
        canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        ccx, ccy = canvas_size // 2, canvas_size // 2

        # 1) 车身
        body_outer = pygame.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        body_outer.center = (ccx, ccy)
        pygame.draw.rect(canvas, COLOR_PLAYER_OUTLINE, body_outer)
        body_inner = body_outer.inflate(-outline * 2, -outline * 2)
        pygame.draw.rect(canvas, COLOR_PLAYER_TANK, body_inner)

        # 2) 炮管（朝上）
        barrel_rect = pygame.Rect(0, 0, barrel_thickness, int(barrel_length))
        barrel_rect.centerx = ccx
        barrel_rect.bottom = ccy
        pygame.draw.rect(canvas, COLOR_PLAYER_OUTLINE, barrel_rect)
        pygame.draw.rect(canvas, COLOR_PLAYER_TANK, barrel_rect.inflate(-outline, 0))

        # 3) 圆形炮塔
        pygame.draw.circle(canvas, COLOR_PLAYER_OUTLINE, (ccx, ccy), int(turret_radius))
        pygame.draw.circle(canvas, COLOR_PLAYER_TANK, (ccx, ccy), int(turret_radius - outline))

        rotated = pygame.transform.rotate(canvas, -math.degrees(self.angle))
        rotated_rect = rotated.get_rect(center=self.rect.center)
        surface.blit(rotated, rotated_rect)

        # 护盾效果：蓝色光圈跟随玩家（仅在护盾生效期间绘制）
        # 剩余 > SHIELD_WARN_SECONDS：维持原不透明效果；
        # 剩余 <= SHIELD_WARN_SECONDS：进入呼吸灯警告，光圈与光晕透明度同步平滑变化。
        if self.is_shielded:
            ring_radius = int(self.rect.width * 0.9)
            ring_rect = pygame.Rect(0, 0, ring_radius * 2, ring_radius * 2)
            ring_rect.center = self.rect.center

            # 呼吸透明度系数（1.0 = 原效果；warning 时随正弦在 [PULSE_MIN, 1.0] 间循环）
            pulse = 1.0
            if self.shield_remaining <= SHIELD_WARN_SECONDS:
                t = pygame.time.get_ticks() % int(SHIELD_BREATHE_PERIOD)
                sinv = (1.0 + math.sin(2 * math.pi * t / SHIELD_BREATHE_PERIOD)) / 2.0
                pulse = 1.0 - SHIELD_PULSE_MIN + SHIELD_PULSE_MIN * sinv

            # 光圈先画到独立透明层，用可控 alpha 绘制（原效果即 pulse=1.0，视觉一致）
            shield_layer = pygame.Surface(ring_rect.size, pygame.SRCALPHA)
            ring_alpha = int(255 * pulse)
            pygame.draw.ellipse(
                shield_layer,
                (*COLOR_SHIELD_RING, ring_alpha),
                shield_layer.get_rect(),
                max(2, self.rect.width // 12),
            )
            surface.blit(shield_layer, ring_rect)

            # 外侧淡色光晕，alpha 与光圈同步呼吸（原效果 light_alpha=50）
            light_alpha = int(50 * pulse)
            glow = pygame.Surface(ring_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (80, 140, 255, light_alpha), glow.get_rect())
            surface.blit(glow, ring_rect, special_flags=pygame.BLEND_ALPHA_SDL2)

    def _render_trail(self, surface: pygame.Surface) -> None:
        """绘制加速尾焰粒子：青蓝颗粒，越老越小且越淡，形成动态拖尾。"""
        for p in self.trail_particles:
            t = max(0.0, p["life"] / p["ttl"])       # 1→0：越老越小越淡
            size = max(1, int(p["size"] * (0.4 + 0.6 * t)))
            alpha = int(200 * t)
            color = p["color"]
            px, py = int(round(p["x"])), int(round(p["y"]))

            fill = pygame.Surface((size * 2 + 1, size * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(fill, (color[0], color[1], color[2], alpha),
                               (size, size), size)
            surface.blit(fill, (px - size, py - size))

    def render_ammo_ui(self, surface: pygame.Surface, x: int, y: int) -> None:
        """绘制弹药 UI。"""
        slot_size = 18
        slot_gap = 6
        for i in range(MAGAZINE_CAPACITY):
            slot_rect = pygame.Rect(x + i * (slot_size + slot_gap), y, slot_size, slot_size)
            color = COLOR_AMMO_FULL if i < self.ammo else COLOR_AMMO_EMPTY
            pygame.draw.rect(surface, color, slot_rect)
        if self.is_reloading:
            bar_width = MAGAZINE_CAPACITY * slot_size + (MAGAZINE_CAPACITY - 1) * slot_gap
            bar_height = 6
            bar_y = y + slot_size + 4
            bg_rect = pygame.Rect(x, bar_y, bar_width, bar_height)
            pygame.draw.rect(surface, COLOR_AMMO_EMPTY, bg_rect)
            progress = 1.0 - (self.reload_remaining / RELOAD_DURATION)
            progress = min(max(progress, 0.0), 1.0)
            fill_rect = pygame.Rect(x, bar_y, int(bar_width * progress), bar_height)
            pygame.draw.rect(surface, COLOR_AMMO_RELOADING, fill_rect)