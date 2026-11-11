# -*- coding: utf-8 -*-
"""
共享物理组件 — 全向移动 + 车控模式

提供两套物理接口：
  update()       — 旧版 target_angle + thrust 模式（历史保留）
  update_car()   — 新版 throttle + steering 模式（供 PlayerTank 使用）

update_car 模式（W/S=前后，A/D=转向）：
  - throttle: +1(W前进), 0(无), -1(S后退)
  - steering: -1(A左转), 0(无), +1(D右转)
  - vx/vy 直接由 facing_angle × current_speed 计算，无方向滞后
  - 松键时使用线性刹车，不叠加指数摩擦
"""
import math
from core.settings import (
    PHYSICS_ACCEL,
    PHYSICS_FRICTION,
    PHYSICS_TURN_SPEED,
    BRAKE_DECELERATION,
    REVERSE_SPEED_LIMIT,
    REVERSE_ACCEL_FACTOR,
)


class TankPhysics:
    """共享物理组件。
    update() 和 update_car() 共用 facing_angle / current_speed / vx / vy / x / y，
    但控制逻辑不同，调用时选择其中一个即可。
    """
    def __init__(self, x: float, y: float,
                 max_speed: float,
                 accel: float = PHYSICS_ACCEL,
                 turn_speed: float = PHYSICS_TURN_SPEED,
                 friction: float = PHYSICS_FRICTION,
                 brake_decel: float = BRAKE_DECELERATION,
                 reverse_max_speed: float = None,
                 reverse_accel_factor: float = REVERSE_ACCEL_FACTOR):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing_angle = 0.0       # 车身朝向（弧度，0=朝上，顺时针为正）
        self.current_speed = 0.0      # 当前速度大小 (px/s)，正=前进，负=后退
        self.max_speed = max_speed
        self.accel = accel
        self.turn_speed = turn_speed
        self.friction = friction
        self.brake_decel = brake_decel
        self.reverse_max_speed = (
            -max_speed * REVERSE_SPEED_LIMIT
            if reverse_max_speed is None
            else reverse_max_speed
        )
        self.reverse_accel_factor = reverse_accel_factor

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def velocity_angle(self) -> float:
        """实际运动方向（弧度）。"""
        if self.speed < 0.01:
            return self.facing_angle
        return math.atan2(self.vx, -self.vy)

    # ------------------------------------------------------------------
    # 旧接口：target_angle + thrust（历史保留，不动）
    # ------------------------------------------------------------------
    def update(self, dt: float, target_angle: float, thrust: float) -> None:
        """每帧物理更新（旧接口）。"""
        # ---- 1. facing_angle 平滑转向 target_angle ----
        diff = target_angle - self.facing_angle
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        max_turn = self.turn_speed * dt
        if abs(diff) <= max_turn:
            self.facing_angle = target_angle
        else:
            self.facing_angle += math.copysign(max_turn, diff)

        # ---- 2. 速度大小：独立加减速 ----
        if thrust > 0:
            self.current_speed += self.accel * dt
            if self.current_speed > self.max_speed:
                self.current_speed = self.max_speed
        else:
            self.current_speed *= math.exp(-self.friction * dt)
            if self.current_speed < 0.01:
                self.current_speed = 0.0

        # ---- 3. 速度方向：追踪 facing_angle ----
        target_vx = math.sin(self.facing_angle) * self.current_speed
        target_vy = -math.cos(self.facing_angle) * self.current_speed
        factor = 1.0 - math.exp(-self.friction * dt * 10)
        self.vx += (target_vx - self.vx) * factor
        self.vy += (target_vy - self.vy) * factor

        # ---- 4. 更新位置 ----
        self.x += self.vx * dt
        self.y += self.vy * dt

    # ------------------------------------------------------------------
    # 新接口：throttle + steering（供 PlayerTank 使用）
    # ------------------------------------------------------------------
    def update_car(self, dt: float, throttle: float, steering: float) -> None:
        """车控模式物理更新。
        Args:
            throttle: 油门，+1(W前进) / 0(无) / -1(S后退)
            steering: 转向，-1(A左转) / 0(无) / +1(D右转)
        """
        # ---- 1. 油门：W/S 控制前后速度 ----
        # （放在转向之前，让转向基于更新后的 current_speed 符号）
        if throttle > 0:
            # 前进加速
            self.current_speed += self.accel * dt
            self.current_speed *= math.exp(-self.friction * dt * 0.5)  # 轻微自然阻力
            if self.current_speed > self.max_speed:
                self.current_speed = self.max_speed
        elif throttle < 0:
            # 倒车
            self.current_speed -= self.accel * self.reverse_accel_factor * dt
            self.current_speed *= math.exp(-self.friction * dt * 0.5)
            if self.current_speed < self.reverse_max_speed:
                self.current_speed = self.reverse_max_speed
        else:
            # 松键：线性刹车，不叠加摩擦
            if self.current_speed > 0.5:
                self.current_speed -= self.brake_decel * dt
                if self.current_speed < 0:
                    self.current_speed = 0
            elif self.current_speed < -0.5:
                self.current_speed += self.brake_decel * dt
                if self.current_speed > 0:
                    self.current_speed = 0
            else:
                self.current_speed = 0.0

        # ---- 2. 转向：基于更新后的 current_speed 符号决定有效转向 ----
        # 倒车时翻转 steering，使 D 始终代表"轨迹向右弯"
        if steering != 0:
            effective_steering = steering
            if self.current_speed < 0:
                effective_steering = -steering
            self.facing_angle += effective_steering * self.turn_speed * dt

        # ---- 3. 速度方向 = facing 方向（无方向滞后） ----
        fx = math.sin(self.facing_angle)
        fy = -math.cos(self.facing_angle)
        self.vx = fx * self.current_speed
        self.vy = fy * self.current_speed

        # ---- 4. 更新位置 ----
        self.x += self.vx * dt
        self.y += self.vy * dt

    # ------------------------------------------------------------------
    # 通用
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """立即停止移动。"""
        self.vx = 0.0
        self.vy = 0.0
        self.current_speed = 0.0