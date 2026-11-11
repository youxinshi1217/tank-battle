# -*- coding: utf-8 -*-
"""
激光道具实体：虚线预测 + 快速射线（一次性充能）

与普通子弹的关键差异：
  - 发射前先用 trace_laser_path()「预计算整条折线」，反射点为精确交点；
  - 实射时 Laser 沿这条折线高速推进 —— 既不会穿墙（不逐帧步进），
    也不会因速度快而漏判命中（推进时按 <= LASER_TRACE_STEP 子步检测坦克矩形）；
  - 命中坦克 / 达到 LASER_MAX_BOUNCES 次反射即消失。

轨迹追踪 1:1 复刻 Bullet.update 的「逐轴翻转」反射逻辑（同样的 BULLET_SIZE、
边界裁剪、rect_hits_obstacle），保证「虚线预览 == 实际弹道」。
"""
import math
import pygame

from core.settings import (
    BULLET_SIZE,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    LASER_SPEED,
    LASER_WIDTH,
    LASER_TRAIL_LENGTH,
    LASER_TRACE_STEP,
    LASER_TRACE_MAX_STEPS,
    COLOR_LASER_BY_OWNER,
    COLOR_LASER_FALLBACK,
)
from core.collision import rect_hits_obstacle


# ------------------------------------------------------------------
# 轨迹追踪（虚线预览 / 实射路径预计算共用）
# ------------------------------------------------------------------
def _axis_step(x: float, y: float, dx: float, dy: float, rect,
               game_map, distance: float):
    """复刻 Bullet.update 的逐轴移动 + 翻转反射。

    Returns:
        (x, y, dx, dy, bounced_bool)：bounced=True 表示本步发生了至少一次轴向翻转。
    """
    half = BULLET_SIZE / 2
    bounced = False

    # X 轴（与 Bullet.update 判定完全一致）
    new_x = x + dx * distance
    hit_x_boundary = new_x - half < 0 or new_x + half > SCREEN_WIDTH
    if dx != 0:
        test_rect = rect.copy()
        clamped_x = min(max(new_x, half), SCREEN_WIDTH - half)
        test_rect.center = (round(clamped_x), round(y))
        hit_x_wall = rect_hits_obstacle(test_rect, game_map)
        if hit_x_boundary or hit_x_wall:
            dx = -dx
            bounced = True
        else:
            x = new_x

    # Y 轴
    new_y = y + dy * distance
    hit_y_boundary = new_y - half < 0 or new_y + half > SCREEN_HEIGHT
    if dy != 0:
        test_rect = rect.copy()
        clamped_y = min(max(new_y, half), SCREEN_HEIGHT - half)
        test_rect.center = (round(x), round(clamped_y))
        hit_y_wall = rect_hits_obstacle(test_rect, game_map)
        if hit_y_boundary or hit_y_wall:
            dy = -dy
            bounced = True
        else:
            y = new_y

    return x, y, dx, dy, bounced


def trace_laser_path(x: float, y: float, dx: float, dy: float, game_map,
                     targets=None, max_bounces: int = 10,
                     step: float = LASER_TRACE_STEP,
                     max_steps: int = LASER_TRACE_MAX_STEPS):
    """预计算激光折线（射线法，反射点为精确交点前的最后一次合法位置）。

    Args:
        x, y:    起点像素坐标（炮口）。
        dx, dy:  初始方向（不必归一化，内部会归一化）。
        game_map: 地图（用于墙体/障碍碰撞）。
        targets: 可提前截断轨迹的坦克对象列表（用其 .rect 判定；命中即收尾）。
        max_bounces: 最大反射次数（达到即结束）。

    Returns:
        (vertices, hit_tank)
          vertices: [(x, y), ...] 折线顶点（起点 + 每次反射点 + 末端点）。
          hit_tank: 折线末端命中的坦克对象；未命中为 None。
    """
    targets = targets or []
    px, py = float(x), float(y)
    norm = math.hypot(dx, dy)
    if norm > 0:
        dx, dy = dx / norm, dy / norm
    else:
        dx, dy = 1.0, 0.0

    rect = pygame.Rect(0, 0, BULLET_SIZE, BULLET_SIZE)
    rect.center = (round(px), round(py))

    vertices = [(px, py)]
    bounces = 0
    hit_tank = None

    for _ in range(max_steps):
        # 连续小步进：任一步撞到目标坦克即收尾（预览中表现为"落点"）
        px, py, dx, dy, bounced = _axis_step(px, py, dx, dy, rect,
                                             game_map, step)
        if bounced:
            bounces += 1
            vertices.append((px, py))
        rect.center = (round(px), round(py))

        # 命中判定：与主循环子弹一致的矩形相交（玩家坦克 TANK_SIZE rect）
        for tank in targets:
            if tank is not None and rect.colliderect(tank.rect):
                hit_tank = tank
                vertices.append((px, py))
                return vertices, hit_tank

        if bounces >= max_bounces:
            # 达到最大反射次数：末端点即最后一次反射点（已在 bounced 分支追加），
            # 此处直接收尾，避免重复追加同一顶点。
            break

    return vertices, hit_tank


# ------------------------------------------------------------------
# 激光实体（接口与 Bullet 对齐：update / render / alive / rect / owner / emitter）
# ------------------------------------------------------------------
class Laser:
    """沿预计算折线高速推进的激光头（可反射，命中坦克或满反射次数即消失）。"""

    def __init__(self, vertices, owner: str = "player"):
        self.vertices = [(float(x), float(y)) for x, y in vertices]
        # 相邻重复点剔除（零长段会导致推进除零）
        cleaned = [self.vertices[0]] if self.vertices else []
        for p in self.vertices[1:]:
            if (abs(p[0] - cleaned[-1][0]) > 1e-9
                    or abs(p[1] - cleaned[-1][1]) > 1e-9):
                cleaned.append(p)
        self.vertices = cleaned if len(cleaned) >= 2 else [cleaned[0], cleaned[0]]

        self.owner = owner           # "player" / "p1" / "p2"
        # 激光颜色按发射方阵营走（红方红 / 蓝方蓝；未知 owner 用兜底色）
        self.color = COLOR_LASER_BY_OWNER.get(owner, COLOR_LASER_FALLBACK)
        self.emitter = None          # 激光归属实体（由 main 层补）
        self.alive = True
        self.bounce_count = 0        # 已完成的反射次数（随折线段推进递增）
        self.hit_tank = None         # 运行时确认命中的坦克（main 层据此结算）

        self.x, self.y = self.vertices[0]
        self.rect = pygame.Rect(0, 0, BULLET_SIZE, BULLET_SIZE)
        self.rect.center = (round(self.x), round(self.y))

        # 各折线段长度缓存
        self._seg_lengths = []
        for i in range(len(self.vertices) - 1):
            (x1, y1), (x2, y2) = self.vertices[i], self.vertices[i + 1]
            self._seg_lengths.append(math.hypot(x2 - x1, y2 - y1))
        self._seg = 0                # 当前段索引
        self._seg_prog = 0.0         # 当前段内已推进距离
        self._targets = []           # 运行时命中检测目标（坦克对象列表）

    def set_targets(self, targets) -> None:
        """设置运行时要进行命中检测的坦克对象列表。"""
        self._targets = list(targets)

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        remaining = LASER_SPEED * dt
        seg_count = len(self._seg_lengths)
        while (remaining > 1e-9 and self.alive
               and self._seg < seg_count):
            seg_len = self._seg_lengths[self._seg]
            left_in_seg = seg_len - self._seg_prog
            if remaining < left_in_seg:
                self._move_within(remaining)
                remaining = 0.0
            else:
                self._move_within(left_in_seg)
                remaining -= left_in_seg
                self._seg += 1
                self._seg_prog = 0.0
                if self._seg < seg_count:
                    self.bounce_count = self._seg
                else:
                    # 走完整条折线（反射次数满，未命中）：消失
                    self.alive = False
                    return

    def _move_within(self, dist: float) -> None:
        """在当前折线段内推进 dist 像素；按 <= LASER_TRACE_STEP 子步检测命中，
        避免激光头一帧移动过远而穿透坦克矩形（高速不穿目标）。"""
        if not self.alive or self._seg >= len(self._seg_lengths):
            return
        seg_len = self._seg_lengths[self._seg]
        (x1, y1), (x2, y2) = self.vertices[self._seg], self.vertices[self._seg + 1]
        seg_dx, seg_dy = (x2 - x1), (y2 - y1)

        left = dist
        while left > 1e-9 and self.alive:
            step = min(left, LASER_TRACE_STEP)
            self._seg_prog += step
            if seg_len > 0:
                ratio = self._seg_prog / seg_len
                self.x = x1 + seg_dx * ratio
                self.y = y1 + seg_dy * ratio
            self.rect.center = (round(self.x), round(self.y))
            # 坦克命中检测（主循环据此结算护盾免疫 / 摧毁）
            for tank in self._targets:
                if tank is not None and self.rect.colliderect(tank.rect):
                    self.hit_tank = tank
                    self.alive = False
                    return
            left -= step

    def _head_progress(self) -> float:
        """激光头沿折线的累计弧长（已完成段长 + 当前段内进度）。"""
        return sum(self._seg_lengths[:self._seg]) + self._seg_prog

    def _slice_points(self, s0: float, s1: float):
        """取折线上弧长区间 [s0, s1] 的点序列（两端插值；s1 之后不收顶点）。
        用于曳光拖尾：头部以全速飞出、光束按固定弧长滞后展开。"""
        if s1 - s0 < 1e-9:
            return [(self.x, self.y), (self.x, self.y)]
        pts = []
        acc = 0.0
        for i, seg_len in enumerate(self._seg_lengths):
            seg_end = acc + seg_len
            # 起点插值：s0 首次落在某段内（含恰在该段起点 t=0）
            if not pts and s0 < seg_end:
                t = 0.0 if seg_len <= 0 else min(1.0, max(0.0, (s0 - acc) / seg_len))
                (x1, y1), (x2, y2) = self.vertices[i], self.vertices[i + 1]
                pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
            # 已起始：收集中间顶点，直至终点插值后收尾
            if pts:
                if s1 >= seg_end:
                    vx, vy = self.vertices[i + 1]
                    if (abs(pts[-1][0] - vx) > 1e-9
                            or abs(pts[-1][1] - vy) > 1e-9):
                        pts.append((vx, vy))
                else:
                    t = 0.0 if seg_len <= 0 else min(1.0, max(0.0, (s1 - acc) / seg_len))
                    (x1, y1), (x2, y2) = self.vertices[i], self.vertices[i + 1]
                    ex, ey = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                    if (abs(pts[-1][0] - ex) > 1e-9
                            or abs(pts[-1][1] - ey) > 1e-9):
                        pts.append((ex, ey))
                    break
            acc = seg_end
        if not pts:
            pts = [(self.x, self.y), (self.x, self.y)]
        return pts

    def render(self, surface: pygame.Surface) -> None:
        """曳光弹式渲染：激光头以全速飞出炮口，光束按 LASER_TRAIL_LENGTH
        弧长滞后头部展开——出膛瞬间拖尾为 0，随后整条光条脱离炮口；
        经过反射点时拖尾沿折线拐弯。命中/满反射消亡时整条消失（alive=False）。"""
        if not self.alive:
            return
        head_s = self._head_progress()
        tail_s = max(0.0, head_s - LASER_TRAIL_LENGTH)
        pts = self._slice_points(tail_s, head_s)
        if len(pts) >= 2:
            pygame.draw.lines(surface, self.color, False, pts, LASER_WIDTH + 2)
            pygame.draw.lines(surface, (255, 255, 240), False, pts, LASER_WIDTH)
        pygame.draw.circle(surface, self.color,
                           (round(self.x), round(self.y)), LASER_WIDTH + 3)
