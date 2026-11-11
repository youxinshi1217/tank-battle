# -*- coding: utf-8 -*-
"""
追踪导弹（MISSILE）实体

行为规则（与策划最终版一致）：
  - 发射后沿炮口方向以 |MISSILE_SPEED|（=1 倍坦克移速，150px/s）前飞；
  - 无目标时保持当前方向匀速直线巡航（撞墙照样翻方向，10 秒寿命内无限反弹）；
  - 锁定目标后按 MISSILE_TURN_RATE 转向追击（弧线咬人），每 MISSILE_RETARGET_INTERVAL
    秒重评一次：只锁弹头正前方 180° 扇形（±90°）内、且与导弹之间没有墙遮挡
    （"看得见"）的坦克，取其中最近者，扇形内更近则转移目标；
  - 追踪强度衰减：首次锁定后 MISSILE_TRACK_FULL_TIME 秒内全强度（贴目标转弯），
    之后每 MISSILE_TRACK_DECAY_STEP 秒按 MISSILE_TRACK_DECAY_STAGES 降一档
    （转向速率乘数 0.6→0.35→0.15→0.05，只减不增）——持续拐弯的目标会被甩开，
    直线/静止目标照样命中；换目标、丢锁重锁均不重置计时（防"换目标续命"）；
  - 发射后 MISSILE_GRACE 秒内不会锁/撞发射者自己（防出膛自爆）；射手在导弹身后
    时本就在扇形外、锁不到 —— 只有撞墙反弹/绕圈后射手进入前方扇形，才会追着
    自己打 —— "容易误伤自己"；
  - 撞到任何在场坦克即消失（护盾拦截 / 命中对方 / 自毁由 main 层结算）；
  - 寿命 MISSILE_FUEL 到头未命中 → 化作一团灰色烟雾慢慢消散（无伤害）。

视觉：
  - 弹体/弹尖/尾焰/尾烟颜色 = 当前目标坦克颜色（未锁定目标前为深灰 + 淡灰烟）；
  - 弹体后方持续拉出同色烟迹：向后扩散、逐渐变淡、像被风吹散一样自然消散；
  - 转移目标时旧烟保持原色散尽、新烟立即换成新目标色，弹体同步变色。

音效状态机（audio 可为 None，无音频环境下降级为静音）：
  flight  → 出膛播放飞行音效一次；
  locked  → 每次锁定/换目标播放锁定音效一次；
  warn    → 与当前目标距离 <= MISSILE_WARN_DISTANCE（4~5 车身）时，
            锁定音效淡出、播放"即将命中"音效一次；
  死亡    → 以上在响音效统一 MISSILE_SND_FADEOUT 秒淡出后停止。
"""
import math
import random

import pygame

from core.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TILE_SIZE,
    GRID_SIZE,
    MISSILE_SPEED,
    MISSILE_SIZE,
    MISSILE_FUEL,
    MISSILE_GRACE,
    MISSILE_CONE_HALF_ANGLE,
    MISSILE_TURN_RATE,
    MISSILE_TRACK_FULL_TIME,
    MISSILE_TRACK_DECAY_STEP,
    MISSILE_TRACK_DECAY_STAGES,
    MISSILE_RETARGET_INTERVAL,
    MISSILE_WARN_DISTANCE,
    MISSILE_SUBSTEP,
    MISSILE_DISSOLVE_TIME,
    MISSILE_SND_FADEOUT,
    MISSILE_LOCK_FADEOUT,
    MISSILE_LOS_STEP,
    MISSILE_SMOKE_PER_FRAME,
    MISSILE_SMOKE_LIFE,
    MISSILE_SMOKE_SIZE_MIN,
    MISSILE_SMOKE_SIZE_MAX,
    MISSILE_SMOKE_EXPAND,
    MISSILE_SMOKE_DRIFT,
    MISSILE_SMOKE_ALPHA,
    MISSILE_SMOKE_BURST,
    SFX_MISSILE_FLIGHT,
    SFX_MISSILE_FLIGHT_VOLUME,
    SFX_MISSILE_LOCK,
    SFX_MISSILE_LOCK_VOLUME,
    SFX_MISSILE_WARN,
    SFX_MISSILE_WARN_VOLUME,
)
from core.collision import rect_hits_obstacle
from maps.tile import TileType


def _lighten(color, factor: float = 1.45):
    """把颜色按比例提亮（弹尖/尾焰用），各通道钳制 0~255。"""
    return tuple(min(255, int(c * factor)) for c in color[:3])


def _fade_channel(channel, seconds: float) -> None:
    """安全淡出并停止 pygame 播放通道（channel 可为 None）。"""
    if channel is None:
        return
    try:
        if channel.get_busy():
            channel.fadeout(int(seconds * 1000))
    except (pygame.error, AttributeError):
        # 通道已结束/无效时静默忽略（fadeout 对已停止通道本就不会报错）
        pass


# ------------------------------------------------------------------
# 追踪导弹实体（接口与 Bullet 对齐：update / render / alive / rect / owner / emitter）
# ------------------------------------------------------------------
class Missile:
    """追踪导弹：直线巡航 + 弧线追击 + 目标转移 + 无限反弹 + 目标色烟迹。"""

    def __init__(self, x: float, y: float, dx: float, dy: float,
                 game_map, owner: str = "player", audio=None):
        """
        Args:
            x, y:    出膛位置（炮口）像素坐标。
            dx, dy:  发射方向（单位化，来自 tank.get_direction_vector()）。
            game_map: 地图（墙体/障碍碰撞）。
            owner:    "player" / "p1" / "p2"（PVP 归属判定用）。
            audio:    AudioManager 实例（None 时静音运行，供无音频环境/测试使用）。
        """
        self.game_map = game_map
        norm = math.hypot(dx, dy)
        if norm > 0:
            dx, dy = dx / norm, dy / norm
        else:
            dx, dy = 1.0, 0.0
        # 行进方向（角度，标准数学向、y 轴朝下）。MISSILE_SPEED 为用户口径
        # "1 倍坦克移速"（150px/s，与坦克同速）；速率取绝对值沿炮口方向前飞。
        self.dir_angle = math.atan2(dy, dx)
        self.speed = abs(MISSILE_SPEED)

        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(0, 0, MISSILE_SIZE, MISSILE_SIZE)
        self.rect.center = (round(self.x), round(self.y))

        self.owner = owner
        self.emitter = None               # 发射坦克（由 main 层补；自伤识别用）
        self.alive = True
        self.hit_tank = None              # 命中的坦克对象（main 层据此结算）

        # 寿命 / 消散
        self.age = 0.0
        self.fuel = MISSILE_FUEL
        self.dying = False                # 寿命到头：进入灰烟消散阶段（无碰撞/无移动）
        self.die_timer = 0.0

        # 追踪状态
        self.target = None                # 当前目标坦克对象
        self.target_color = None          # 当前目标坦克颜色（None=深灰弹体+淡灰烟）
        self._retarget_timer = 0.0
        self._lock_age = None             # 首次锁定起累计追踪时长（秒）；None=还没锁定过。
                                           # 只减不增的强度计时：换目标/丢锁重锁均不重置

        # 尾烟粒子（dict: x, y, vx, vy, r, life, ttl, color）
        self.smoke = []

        # ---- 音效状态机 ----
        self.audio = audio
        self._ch_flight = None            # 飞行音效通道（出膛即播一次）
        self._ch_lock = None              # 锁定音效通道
        self._ch_warn = None              # 即将命中音效通道
        self._phase = "flight"            # flight / locked / warn
        if audio is not None:
            self._ch_flight = audio.play(
                SFX_MISSILE_FLIGHT, volume_scale=SFX_MISSILE_FLIGHT_VOLUME)

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def discard(self) -> None:
        """立即报废（换关/重开时由 main 调用）：淡出全部在响音效并消失，不结算。"""
        self._fade_all_sounds()
        self.alive = False

    # ------------------------------------------------------------------
    # 主更新
    # ------------------------------------------------------------------
    def update(self, dt: float, targets=None) -> None:
        """推进一帧。

        Args:
            dt:      帧时长（秒）。
            targets: [(tank, color), ...] 可锁定/可命中的在场坦克列表（main 层
                     过滤阵亡者；颜色用于弹体/烟迹染色）。
        """
        if not self.alive:
            return
        self.age += dt
        # 追踪时长只增不减（首次锁定后开始计；未锁定/丢锁期间照计，
        # 因为强度只取决于"这枚导弹追了多久"，与当前是否锁着无关）
        if self._lock_age is not None:
            self._lock_age += dt

        # ---- 灰烟消散阶段：只推粒子，等自然消失 ----
        if self.dying:
            self.die_timer -= dt
            self._update_smoke(dt)
            if self.die_timer <= 0.0:
                self.alive = False
            return

        # ---- 寿命到头：化灰 ----
        self.fuel -= dt
        if self.fuel <= 0.0:
            self._dissolve()
            return

        # ---- 目标重评（每 RETARGET_INTERVAL 秒；更近则转移）----
        self._retarget_timer -= dt
        if self._retarget_timer <= 0.0:
            self._retarget_timer = MISSILE_RETARGET_INTERVAL
            self._select_target(targets or [])

        # ---- 转向（仅锁定目标时；无目标保持当前方向）----
        # 转向速率 = MISSILE_TURN_RATE × 当前追踪强度（全强度→逐级衰减）
        if self.target is not None:
            tx, ty = self.target.rect.center
            desired = math.atan2(ty - self.y, tx - self.x)
            diff = (desired - self.dir_angle + math.pi) % (2 * math.pi) - math.pi
            max_turn = MISSILE_TURN_RATE * self._track_strength() * dt
            self.dir_angle += max(-max_turn, min(max_turn, diff))
        ux = math.cos(self.dir_angle)
        uy = math.sin(self.dir_angle)

        # ---- 移动（子步进防穿透；撞墙翻方向、不计数、不消失）----
        remaining = self.speed * dt
        while remaining > 1e-9 and self.alive:
            step = min(remaining, MISSILE_SUBSTEP)
            remaining -= step
            ux, uy = self._move_axis(ux, uy, step)
            self.dir_angle = math.atan2(uy, ux)
            self.rect.center = (round(self.x), round(self.y))
            # 坦克命中检测（宽限期内不碰发射者自己）
            for tank, _color in (targets or []):
                if tank is self.emitter and self.age < MISSILE_GRACE:
                    continue
                if self.rect.colliderect(tank.rect):
                    self.hit_tank = tank
                    self.alive = False
                    self._fade_all_sounds()
                    return

        if not self.alive:
            return

        # ---- 尾烟：弹体后方持续拉出目标同色烟迹 ----
        self._emit_smoke(ux, uy)
        self._update_smoke(dt)

        # ---- "即将命中"：贴近当前目标即顶替锁定音效 ----
        if (self.target is not None and self._phase == "locked"):
            tx, ty = self.target.rect.center
            if math.hypot(tx - self.x, ty - self.y) <= MISSILE_WARN_DISTANCE:
                self._enter_warn()

    # ------------------------------------------------------------------
    # 内部：移动 / 墙反弹（1:1 复刻 Bullet.update 逐轴判定，但不限反弹次数）
    # ------------------------------------------------------------------
    def _move_axis(self, ux: float, uy: float, distance: float):
        """逐轴移动 + 撞墙翻方向（1:1 复刻 Bullet.update 判定，但不限反弹次数）。

        Returns:
            (ux, uy)：可能被墙翻转后的方向分量。
        """
        half = MISSILE_SIZE / 2
        # X 轴
        new_x = self.x + ux * distance
        hit_x_boundary = new_x - half < 0 or new_x + half > SCREEN_WIDTH
        if ux != 0:
            test_rect = self.rect.copy()
            clamped_x = min(max(new_x, half), SCREEN_WIDTH - half)
            test_rect.center = (round(clamped_x), round(self.y))
            if hit_x_boundary or rect_hits_obstacle(test_rect, self.game_map):
                ux = -ux
            else:
                self.x = new_x
        # Y 轴
        new_y = self.y + uy * distance
        hit_y_boundary = new_y - half < 0 or new_y + half > SCREEN_HEIGHT
        if uy != 0:
            test_rect = self.rect.copy()
            clamped_y = min(max(new_y, half), SCREEN_HEIGHT - half)
            test_rect.center = (round(self.x), round(clamped_y))
            if hit_y_boundary or rect_hits_obstacle(test_rect, self.game_map):
                uy = -uy
            else:
                self.y = new_y
        return ux, uy

    # ------------------------------------------------------------------
    # 内部：目标选择 / 音效状态机
    # ------------------------------------------------------------------
    def _select_target(self, targets) -> None:
        """重评目标：只锁弹头正前方 180° 扇形（±90°）内、且与导弹之间没有
        墙遮挡（"看得见"）的坦克，取其中最近者。

        扇形规则的效果：
          - 发射时射手在导弹身后（180° 反向），锁不到 → 不会一出门就自追；
          - 只有撞墙反弹/绕圈后射手进入前方扇形，才可能误伤自己；
          - 扇形内暂无目标则直飞巡航。
        视线规则的效果：
          - 隔着墙/钢墙的目标一律不可锁（不能说隔着障碍物还探测得到）；
          - 目标被墙挡住时直飞巡航，绕出遮挡后才重新锁定。
        宽限期内仍排除发射者自己；目标变化则进入 locked 阶段。
        强度计时：只有"从无到有的首次锁定"才把 _lock_age 置 0；之后换目标、
        丢锁再重锁都不重置（防换目标续满强度），详见 _track_strength。
        """
        candidates = []
        for tank, color in targets:
            if tank is None:
                continue
            if tank is self.emitter and self.age < MISSILE_GRACE:
                continue
            tx, ty = tank.rect.center
            dx, dy = tx - self.x, ty - self.y
            if dx == 0.0 and dy == 0.0:
                candidates.append((tank, color))     # 完全重合：视作在扇形内
                continue
            # 目标方向 vs 弹头行进方向的夹角（最短角，0=正前方，π=正后方）
            off = abs(math.atan2(dy, dx) - self.dir_angle)
            off = abs((off + math.pi) % (2 * math.pi) - math.pi)
            if off > MISSILE_CONE_HALF_ANGLE:
                continue                            # 扇形外：不可锁定
            if not self._can_see(tank):
                continue                            # 隔着墙：看不见，不可锁定
            candidates.append((tank, color))
        if not candidates:
            # 当前目标脱离扇形 / 被墙遮挡：丢失锁定，恢复直飞巡航，
            # 弹体退回深灰色，锁定/即将命中音效淡出（不残留"隔墙还在追"的错觉）。
            if self.target is not None:
                self.target = None
                self.target_color = None
                self._phase = "flight"
                _fade_channel(self._ch_lock, MISSILE_LOCK_FADEOUT)
                self._ch_lock = None
                _fade_channel(self._ch_warn, MISSILE_LOCK_FADEOUT)
                self._ch_warn = None
            return
        # 取扇形内中心距最近者
        best_tank, best_color = min(
            candidates,
            key=lambda tc: (tc[0].rect.centerx - self.x) ** 2
                           + (tc[0].rect.centery - self.y) ** 2)
        if best_tank is self.target:
            return
        if self._lock_age is None:
            self._lock_age = 0.0            # 首次锁定：开始强度计时（之后不重置）
        self.target = best_tank
        self.target_color = best_color
        self._enter_locked()

    def _track_strength(self) -> float:
        """当前追踪强度（转向速率乘数，1.0=全强度）。

        时间线（以 _lock_age 即"首次锁定起累计追踪时长"计）：
          0 ~ FULL_TIME            → 1.0（全强度，贴目标转弯）
          之后每 DECAY_STEP 秒     → 按 DECAY_STAGES 逐档下降（0.6→0.35→0.15→0.05）
          最后一档之后            → 保持 STAGES[-1]（基本拧不动头，直到燃料耗尽化灰）
        强度只减不增；换目标/丢锁重锁均不重置 _lock_age（见 _select_target）。
        """
        if self._lock_age is None:
            return 1.0                      # 未锁定过：无转向发生，值不重要
        if self._lock_age <= MISSILE_TRACK_FULL_TIME:
            return 1.0
        over = self._lock_age - MISSILE_TRACK_FULL_TIME
        stage = int(over // MISSILE_TRACK_DECAY_STEP)
        if stage >= len(MISSILE_TRACK_DECAY_STAGES):
            stage = len(MISSILE_TRACK_DECAY_STAGES) - 1
        return MISSILE_TRACK_DECAY_STAGES[stage]

    def _can_see(self, tank) -> bool:
        """视线判定：导弹中心与目标中心之间的直线通道上没有任何障碍。

        ★ 2026-10-23：Stage 5 起改问**连续几何**（game_map.geometry）。
          原来查格子：方块化的墙团比真实形状大一圈，导弹会隔着半个身位
          误判「看不见」。现在直接对圆/圆环浮点几何采样，看到即判定。
          老关卡没有 geometry，仍走格子路径，行为不变。
        """
        tx, ty = tank.rect.center
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist <= 0.0:
            return True                             # 完全重合：当然看得见
        ux, uy = dx / dist, dy / dist
        steps = max(1, int(dist / MISSILE_LOS_STEP))
        geometry = getattr(self.game_map, "geometry", None)
        for i in range(1, steps + 1):
            px = self.x + ux * dist * i / steps
            py = self.y + uy * dist * i / steps
            if geometry is not None:
                if geometry.point_solid(px, py):
                    return False                    # 通道上有墙：不可见
                continue
            col = int(px // TILE_SIZE)
            row = int(py // TILE_SIZE)
            if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
                return False                        # 通道越出地图：不可见
            if self.game_map.get_tile(row, col) != TileType.EMPTY:
                return False                        # 通道上有墙：不可见
        return True

    def _enter_locked(self) -> None:
        """每次锁定 / 换目标：先淡出上一条锁定音（防快速换目标叠音），再播新锁定音；
        若之前在即将命中阶段，其音效也一并淡出重来。"""
        self._phase = "locked"
        _fade_channel(self._ch_lock, MISSILE_LOCK_FADEOUT)
        self._ch_lock = None
        _fade_channel(self._ch_warn, MISSILE_LOCK_FADEOUT)
        self._ch_warn = None
        if self.audio is not None:
            self._ch_lock = self.audio.play(
                SFX_MISSILE_LOCK, volume_scale=SFX_MISSILE_LOCK_VOLUME)

    def _enter_warn(self) -> None:
        """贴近目标：锁定音效淡出，播放"即将命中"音效。"""
        self._phase = "warn"
        _fade_channel(self._ch_lock, MISSILE_LOCK_FADEOUT)
        self._ch_lock = None
        if self.audio is not None:
            self._ch_warn = self.audio.play(
                SFX_MISSILE_WARN, volume_scale=SFX_MISSILE_WARN_VOLUME)

    def _fade_all_sounds(self) -> None:
        """导弹死亡：在响的三个音效统一淡出后停止。"""
        for ch in (self._ch_flight, self._ch_lock, self._ch_warn):
            _fade_channel(ch, MISSILE_SND_FADEOUT)
        self._ch_flight = None
        self._ch_lock = None
        self._ch_warn = None

    # ------------------------------------------------------------------
    # 内部：尾烟粒子
    # ------------------------------------------------------------------
    def _emit_smoke(self, ux: float, uy: float) -> None:
        """弹体后方（行进反方向）喷出目标同色烟粒：向后扩散 + 随机漂移。"""
        color = self.target_color if self.target_color is not None else (150, 150, 150)
        tail_len = MISSILE_SIZE * 0.7
        for _ in range(MISSILE_SMOKE_PER_FRAME):
            px = self.x - ux * tail_len + random.uniform(-2, 2)
            py = self.y - uy * tail_len + random.uniform(-2, 2)
            # 向后飘 + 侧向随机漂移（像被风吹散）
            vx = -ux * random.uniform(10, 45) + random.uniform(
                -MISSILE_SMOKE_DRIFT, MISSILE_SMOKE_DRIFT)
            vy = -uy * random.uniform(10, 45) + random.uniform(
                -MISSILE_SMOKE_DRIFT, MISSILE_SMOKE_DRIFT)
            self.smoke.append({
                "x": px, "y": py,
                "vx": vx, "vy": vy,
                "r": float(random.randint(MISSILE_SMOKE_SIZE_MIN,
                                           MISSILE_SMOKE_SIZE_MAX)),
                "life": MISSILE_SMOKE_LIFE, "ttl": MISSILE_SMOKE_LIFE,
                "color": color,
            })

    def _emit_gray_burst(self) -> None:
        """寿命到头：一次性喷出一团灰色烟雾（消散特效）。"""
        for _ in range(MISSILE_SMOKE_BURST):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(15, 70)
            self.smoke.append({
                "x": self.x + random.uniform(-3, 3),
                "y": self.y + random.uniform(-3, 3),
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "r": float(random.randint(MISSILE_SMOKE_SIZE_MIN + 1,
                                          MISSILE_SMOKE_SIZE_MAX + 3)),
                "life": MISSILE_SMOKE_LIFE * 1.4,
                "ttl": MISSILE_SMOKE_LIFE * 1.4,
                "color": (140, 140, 140),   # 灰烟
            })

    def _dissolve(self) -> None:
        """寿命到头：进入灰烟消散阶段（音效同步淡出）。"""
        self.dying = True
        self.die_timer = MISSILE_DISSOLVE_TIME
        self.target = None
        self.target_color = None
        self._emit_gray_burst()
        self._fade_all_sounds()

    def _update_smoke(self, dt: float) -> None:
        remaining = []
        for p in self.smoke:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.96
            p["vy"] *= 0.96
            p["r"] += MISSILE_SMOKE_EXPAND * dt
            p["life"] -= dt
            if p["life"] > 0:
                remaining.append(p)
        self.smoke = remaining

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        # 1) 尾烟（目标同色/灰烟；越老越淡越大，像被风吹散）
        for p in self.smoke:
            t = max(0.0, p["life"] / p["ttl"])
            alpha = int(MISSILE_SMOKE_ALPHA * t)
            r = max(1, int(p["r"]))
            fill = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(
                fill, (p["color"][0], p["color"][1], p["color"][2], alpha),
                (r, r), r)
            surface.blit(fill, (int(round(p["x"])) - r, int(round(p["y"])) - r))

        # 2) 弹体（消散阶段不画）
        if self.dying:
            return
        color = self.target_color if self.target_color is not None else (80, 80, 85)
        self._render_body(surface, color)

    def _render_body(self, surface: pygame.Surface, color) -> None:
        """画一枚指向行进方向的小火箭：弹体+弹尖+两侧尾翼+尾部火焰。
        画布上火箭朝 +x，再按 dir_angle 旋转（与坦克 render 同一套旋转约定）。"""
        size = MISSILE_SIZE * 4
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        ccx, ccy = size // 2, size // 2
        length = MISSILE_SIZE * 1.7
        width = MISSILE_SIZE * 0.66
        # 弹体
        body = pygame.Rect(0, 0, int(length), int(width))
        body.center = (ccx, ccy)
        pygame.draw.rect(canvas, color, body, border_radius=max(2, int(width * 0.35)))
        # 弹尖（行进方向前端，浅色三角）
        nose_len = length * 0.28
        pygame.draw.polygon(canvas, _lighten(color, 1.5), [
            (body.right - 1, body.top),
            (body.right - 1, body.bottom),
            (body.right + int(nose_len), ccy),
        ])
        # 尾翼（后端上下两片，深色）
        fin_len = length * 0.34
        fin_h = width * 0.95
        for side in (-1, 1):
            pygame.draw.polygon(canvas, (30, 30, 36), [
                (body.left, ccy + side * width * 0.32),
                (body.left - int(fin_len), ccy + side * (width * 0.32 + fin_h)),
                (body.left, ccy + side * width * 0.32 + side * width * 0.1),
            ])
        # 尾部火焰（颜色同弹体提亮，长度随机抖动营造喷射感）
        flame_len = MISSILE_SIZE * random.uniform(0.5, 1.1)
        flame_col = _lighten(color, 1.55)
        pygame.draw.polygon(canvas, flame_col, [
            (body.left, ccy - width * 0.30),
            (body.left, ccy + width * 0.30),
            (body.left - int(flame_len), ccy),
        ])

        rotated = pygame.transform.rotate(canvas, -math.degrees(self.dir_angle))
        rotated_rect = rotated.get_rect(center=(round(self.x), round(self.y)))
        surface.blit(rotated, rotated_rect)
