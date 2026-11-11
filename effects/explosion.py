# -*- coding: utf-8 -*-
"""
坦克被摧毁的爆炸 / 碎裂特效（世界空间表现层）。

定位：纯表现，不含任何玩法逻辑。沿用 FloatingScore 的范式：
  - update(dt) 推进；render(surface) 绘制；alive 标记生命周期结束。
  - 创建时只传入出生位置 center（+ 可选的 scale 放大系数），不读取游戏状态。

视觉风格（已与用户确认）：线稿卡通、浅色线条。
  游戏实际背景是深灰 (30,30,30) + 彩色坦克，因此线稿"反色"为浅色 (235,238,245)，
  才能在深灰底上清晰可见——保留"细线、无填色、扁平卡通、无写实火焰"的气质。
  若日后把游戏背景改成白底，可把 STROKE_COLOR / FLASH_COLOR 改回黑/白即可。

打击感由 4 层拼成（"快起快收" + 高对比 + 震动）：
  1) 亮核  FLASH ：白盘瞬间膨胀到峰值再快速淡出（几帧内），给"膨胀亮核"冲击。
  2) 冲击波环 RING  ：1 圈描边圆向外扩散并淡出（漫画式的 single shockwave）。
  3) 漫画放射线 COMIC：约 4 帧（~0.07s）的向外短线，漫画"BOOM"爆发感。
  4) 碎片 DEBRIS  ：N 片浅色小三角，径向初速 + 重力 + 自旋 + 淡出，模拟装甲碎裂。

所有可调参数集中在文件顶部常量区，便于统一微调；震动量通过类常量 TRAUMA 暴露，
由接线方在生成爆炸时调用 shake.add_trauma(Explosion.TRAUMA)。

依赖：仅 pygame。渲染全部走临时 SRCALPHA 表面做透明混合，因此无论是直接画到
self.screen 还是画到离屏 world_surface（屏幕震动方案），都能正确半透明叠加。
"""

import math
import random

import pygame

# ---------- 线稿配色（深灰底上可见的浅色）----------
STROKE_COLOR = (235, 238, 245)   # 线稿主色（环 / 放射线 / 碎片）
FLASH_COLOR = (255, 255, 255)    # 亮核白

# ---------- 时长（秒）----------
FLASH_DURATION = 0.12            # 亮核存在时长（快起快收）
RING_DURATION = 0.45             # 冲击波环时长
DEBRIS_LIFETIME = 0.70           # 碎片寿命
COMIC_DURATION = 0.07            # 漫画放射线时长（约 4 帧 @60fps）

# ---------- 尺寸（px，随 scale 放大）----------
FLASH_MAX_RADIUS = 24            # 亮核最大半径
RING_MAX_RADIUS = 88             # 冲击波环最大半径
RING_WIDTH = 3                   # 环线宽
RING_COUNT = 1                   # 环数量（1~2）
DEBRIS_COUNT = 10                # 碎片数量
DEBRIS_SPEED = 190               # 碎片初速（px/s）
DEBRIS_GRAVITY = 430             # 碎片重力（px/s^2）
DEBRIS_SIZE = 6                  # 碎片基础边长
COMIC_LINES = 10                 # 放射线数量
COMIC_LENGTH = 32                # 放射线长度

# ---------- 全局碎片上限（防一波敌人同时死太多时卡顿）----------
MAX_DEBRIS_TOTAL = 260

def _make_shard(size: int) -> pygame.Surface:
    """预渲染一片浅色三角碎片（带透明通道），运行时只做旋转/缩放/blit。"""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2
    pygame.draw.polygon(s, STROKE_COLOR,
                        [(half, 0), (size - 1, size - 1), (0, size - 1)])
    return s


_SHARD = _make_shard(DEBRIS_SIZE)


class Explosion:
    """世界空间爆炸特效：亮核 + 冲击波环 + 漫画放射线 + 碎片。"""

    TRAUMA = 0.45                # 触发屏幕震动的 trauma 量；玩家被毁可在接线处乘 ~1.8

    def __init__(self, center, scale: float = 1.0, time_scale: float = 1.0):
        self._cx, self._cy = float(center[0]), float(center[1])
        self._scale = float(scale)
        # time_scale < 1 慢放（如玩家被毁 0.5=半速），> 1 快进；仅影响推进速度，
        # 不影响各阶段相对节奏（亮核/环/碎片仍同比例拉长）。
        self._time_scale = float(time_scale)
        self._age = 0.0
        self._lifetime = max(FLASH_DURATION, RING_DURATION,
                             DEBRIS_LIFETIME, COMIC_DURATION) / self._time_scale
        self.alive = True

        rng = random.Random()
        self._debris = []
        for _ in range(DEBRIS_COUNT):
            ang = rng.uniform(0, 2 * math.pi)
            spd = DEBRIS_SPEED * rng.uniform(0.5, 1.2)
            self._debris.append({
                "x": self._cx, "y": self._cy,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - 40,        # 略微上抛，碎裂更自然
                "rot": rng.uniform(0, 2 * math.pi),
                "vr": rng.uniform(-9, 9),             # 自旋角速度
                "life": DEBRIS_LIFETIME * rng.uniform(0.7, 1.0),
                "age": 0.0,
                "scale": rng.uniform(0.6, 1.3),
            })
        self._comic_angles = [rng.uniform(0, 2 * math.pi)
                              for _ in range(COMIC_LINES)]

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self._age += dt * self._time_scale
        for d in self._debris:
            d["age"] += dt
            d["vy"] += DEBRIS_GRAVITY * dt
            d["x"] += d["vx"] * dt
            d["y"] += d["vy"] * dt
            d["rot"] += d["vr"] * dt
        if self._age >= self._lifetime:
            self.alive = False

    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        t = self._age
        s = self._scale

        # 1) 亮核：白盘快速膨胀后淡出
        if t < FLASH_DURATION:
            p = t / FLASH_DURATION
            r = FLASH_MAX_RADIUS * s * (1.0 - (1.0 - p) ** 2)
            alpha = int(255 * (1.0 - p))
            self._blit_disc(surface, self._cx, self._cy, r, FLASH_COLOR, alpha)

        # 2) 冲击波环：描边圆外扩淡出
        for i in range(RING_COUNT):
            rt = t - i * 0.05
            if 0.0 <= rt < RING_DURATION:
                p = rt / RING_DURATION
                r = RING_MAX_RADIUS * s * p
                alpha = int(210 * (1.0 - p))
                self._blit_ring(surface, self._cx, self._cy, r, RING_WIDTH, alpha)

        # 3) 漫画放射线：约 4 帧的向外短线
        if t < COMIC_DURATION:
            p = t / COMIC_DURATION
            alpha = int(255 * (1.0 - p))
            length = COMIC_LENGTH * s * (0.4 + 0.6 * p)
            for ang in self._comic_angles:
                self._blit_line(surface, self._cx, self._cy, ang, length, alpha)

        # 4) 碎片：浅色小三角，抛物线飞散 + 自旋 + 淡出
        for d in self._debris:
            if d["age"] >= d["life"]:
                continue
            p = d["age"] / d["life"]
            alpha = int(255 * (1.0 - p))
            self._blit_shard(surface, d, alpha)

    # ---- 绘制基元（均经临时 SRCALPHA 表面做透明混合）----
    @staticmethod
    def _blit_disc(surface, x, y, r, color, alpha):
        if r <= 0:
            return
        d = int(r * 2) + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(tmp, color, (d // 2, d // 2), int(r))
        tmp.set_alpha(int(alpha))
        surface.blit(tmp, (int(x - r), int(y - r)))

    @staticmethod
    def _blit_ring(surface, x, y, r, w, alpha):
        if r <= 0:
            return
        d = int(r * 2) + w * 2 + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(tmp, STROKE_COLOR, (d // 2, d // 2), int(r), w)
        tmp.set_alpha(int(alpha))
        surface.blit(tmp, (int(x - d / 2), int(y - d / 2)))

    @staticmethod
    def _blit_line(surface, x, y, ang, length, alpha):
        if length <= 0:
            return
        tmp = pygame.Surface((int(length) + 2, 4), pygame.SRCALPHA)
        pygame.draw.line(tmp, STROKE_COLOR, (0, 2), (int(length), 2), 2)
        rot = pygame.transform.rotate(tmp, -math.degrees(ang))
        surface.blit(rot, (int(x - rot.get_width() / 2),
                           int(y - rot.get_height() / 2)))

    @staticmethod
    def _blit_shard(surface, d, alpha):
        img = pygame.transform.rotozoom(_SHARD, math.degrees(d["rot"]), d["scale"])
        img.set_alpha(int(alpha))
        surface.blit(img, (int(d["x"] - img.get_width() / 2),
                           int(d["y"] - img.get_height() / 2)))
