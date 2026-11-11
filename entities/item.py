# -*- coding: utf-8 -*-
"""
Phase 5.4.0 - Item Entity（道具实体）

说明：
本文件仅建立道具框架（Item 实体 + 效果接口），不实现任何具体道具效果。
具体效果统一通过 Item.apply() -> player.apply_item_effect() 转发，
由玩家侧（后续子阶段）实现，保持本阶段只做"框架"的边界。
"""
import math
import os

import pygame

from core.game_fonts import game_font
from core.settings import (
    ITEM_BREATH_PERIOD,
    ITEM_FLASH_START,
    TILE_SIZE,
)


# ------------------------------------------------------------------
# 道具模块级默认参数
# 注意：本阶段不修改 settings.py，所需数值暂以模块常量集中于此；
#       后续如需集中管理，可整体迁移到 core.settings。
# ------------------------------------------------------------------
ITEM_SIZE = int(TILE_SIZE * 0.7)     # 道具边长（像素）
ITEM_LIFETIME = 15.0                  # 道具在地图上存在时长（秒）

# 加速道具贴图（用户提供的 PNG，直接作为贴图使用）
_SPEED_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "加速道具.png")
_SPEED_IMG_CACHE = None

# 护盾道具贴图（用户提供的 JPG，直接作为贴图使用）
_SHIELD_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "护盾道具.jpg")
_SHIELD_IMG_CACHE = None

# 霰弹道具贴图（用户提供的 PNG，直接作为贴图使用）
_SHOTGUN_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "霰弹道具.png")
_SHOTGUN_IMG_CACHE = None

# 激光道具贴图（用户提供的 PNG，直接作为贴图使用；加载失败回退程序化图标）
_LASER_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "激光道具图标.png")
_LASER_IMG_CACHE = None

# 追踪导弹道具贴图（用户提供的 PNG，直接作为贴图使用；加载失败回退程序化图标）
_MISSILE_TEXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "追踪导弹导弹道具图标.png")
_MISSILE_IMG_CACHE = None
# 导弹贴图视觉补偿偏移（像素，负值=往左/往下，正值=往右/往上）。
# 原图 30×26 放大到 22px 时人眼对低分辨率箭形有视觉错觉，此处做横/纵微调。
# 改法：X 轴（横，负=往左 / 正=往右）、Y 轴（纵，负=往下 / 正=往上）。
# 例如「往右上角挪一点」= X 加正、Y 加正（如 (1, 1) 或 (2, 1)）。
_MISSILE_VISUAL_XY = (-1, 0)   # (横偏移, 纵偏移)，像素；默认仅往左 1px、纵向不动


class ItemType:
    """道具类型（Phase 5.4 冻结三类型）。"""
    SHOTGUN = "SHOTGUN"   # 霰弹：下一次攻击散射
    SHIELD = "SHIELD"     # 护盾：短暂伤害免疫（10s）
    SPEED = "SPEED"       # 加速：短暂提升移动速度（10s）
    LASER = "LASER"       # 激光：一次性充能（虚线预览弹道 + 快速射线，最多反射 10 次）
    MISSILE = "MISSILE"   # 追踪导弹：发射后追踪最近坦克（可转移目标/可误伤自己）


# 类型 -> 色块颜色（渲染用）
_ITEM_COLORS = {
    ItemType.SHOTGUN: (255, 200, 60),   # 亮黄：霰弹
    ItemType.SHIELD: (90, 160, 255),    # 亮蓝：护盾
    ItemType.SPEED: (110, 230, 120),    # 亮绿：加速
    ItemType.LASER: (255, 120, 220),    # 亮粉：激光
    ItemType.MISSILE: (255, 130, 60),   # 亮橙：追踪导弹
}

# 类型 -> 中央标识字符（渲染用）
_ITEM_LABELS = {
    ItemType.SHOTGUN: "S",
    ItemType.SHIELD: "D",
    ItemType.SPEED: ">",
    ItemType.LASER: "L",
    ItemType.MISSILE: "M",
}


class Item:
    """战场道具实体：占据空间、存在生命周期、可被玩家拾取并应用效果。"""

    def __init__(self, x: float, y: float,
                 item_type,
                 lifetime: float = ITEM_LIFETIME):
        self.x = float(x)
        self.y = float(y)
        self.item_type = item_type
        self.lifetime = float(lifetime)
        self.time_left = self.lifetime
        self.alive = True
        self.rect = pygame.Rect(0, 0, ITEM_SIZE, ITEM_SIZE)
        self.rect.center = (round(self.x), round(self.y))

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """每帧递减剩余时长；到期后 alive=False（由外层负责移除）。"""
        if not self.alive:
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0.0
            self.alive = False

    @property
    def expired(self) -> bool:
        """是否已到期（等待移除）。"""
        return not self.alive

    @property
    def blinking(self) -> bool:
        """是否进入最后 ITEM_FLASH_START 秒的提醒阶段（呼吸灯）。"""
        return self.time_left <= ITEM_FLASH_START

    # ------------------------------------------------------------------
    # 效果接口（Phase 5.4.0 仅转发，不实现任何具体效果）
    # ------------------------------------------------------------------
    def apply(self, player) -> None:
        """拾取后应用效果。

        Phase 5.4.0 边界：
          - 仅作接口转发，不做任何具体效果实现。
          - 只允许调用 player.apply_item_effect()，由玩家侧（后续子阶段）执行。
        """
        player.apply_item_effect(self.item_type)

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        color = _ITEM_COLORS.get(self.item_type, (255, 255, 255))
        label = _ITEM_LABELS.get(self.item_type, "?")

        # 提醒阶段：呼吸灯（透明度随实时时间正弦呼吸，周期 ITEM_BREATH_PERIOD）
        # 0.6+0.4·sin：谷值 ~51 / 峰值 255，中央图标全程基本可见，明暗柔和。
        alpha = 255
        if self.blinking:
            t = pygame.time.get_ticks() / 1000.0
            alpha = int(255 * (0.6 + 0.4 * math.sin(
                t * (2 * math.pi / ITEM_BREATH_PERIOD))))

        cell = pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(cell, (*color, alpha), cell.get_rect())
        pygame.draw.rect(cell, (*color, 255), cell.get_rect(), 2)
        surface.blit(cell, self.rect)

        # 中央图标：按类型绘制；SHIELD 用盾牌、SHOTGUN 用炮管散射、SPEED 用多重箭头
        if alpha > 60:
            if self.item_type == ItemType.SHIELD:
                if not self._blit_texture(surface, "shield"):
                    self._draw_shield_icon(surface, self.rect, alpha)
            elif self.item_type == ItemType.SHOTGUN:
                if not self._blit_texture(surface, "shotgun"):
                    self._draw_shotgun_icon(surface, self.rect, alpha)
            elif self.item_type == ItemType.SPEED:
                if not self._blit_texture(surface, "speed"):
                    self._draw_speed_icon(surface, self.rect, alpha)
            elif self.item_type == ItemType.LASER:
                if not self._blit_texture(surface, "laser"):
                    self._draw_laser_icon(surface, self.rect)
            elif self.item_type == ItemType.MISSILE:
                if not self._blit_texture(surface, "missile"):
                    self._draw_missile_icon(surface, self.rect)
            else:
                font = game_font(max(10, ITEM_SIZE // 2))
                text = font.render(label, True, (0, 0, 0))
                text_rect = text.get_rect(center=(self.rect.centerx, self.rect.centery))
                surface.blit(text, text_rect)

    def _draw_shield_icon(self, surface: pygame.Surface, rect, alpha: int) -> None:
        """绘制游戏护盾风格图标：盾牌造型（小号居中，带中带横梁）。
        尺寸刻意收小，顶部平、两侧下沉、底部小收尖，避免被误读为三角形。"""
        w = rect.width * 0.60          # 缩小到格内约 60%，四周留白
        h = rect.height * 0.70
        cx, cy = rect.centerx, rect.centery
        # 盾牌外轮廓：顶部平直、侧边下沉、底部收成钝尖
        shield_points = [
            (cx - w / 2, cy - h / 2),         # 左上
            (cx + w / 2, cy - h / 2),         # 右上
            (cx + w / 2, cy - h / 10),        # 右下侧
            (cx + w * 0.28, cy + h / 10),     # 右下收拢
            (cx, cy + h / 2),                 # 底部尖
            (cx - w * 0.28, cy + h / 10),     # 左下收拢
            (cx - w / 2, cy - h / 10),        # 左下侧
        ]
        # 浅色盾面（半透明填充，跟随闪烁）
        fill = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(fill, (235, 245, 255, alpha), shield_points)
        surface.blit(fill, (0, 0))
        # 深色描边
        pygame.draw.polygon(surface, (40, 60, 120), shield_points, 2)
        # 中带横梁（横向贯穿盾面中部，强化"盾"辨识，而非三角）
        y_mid = cy + h * 0.06
        pygame.draw.line(surface, (40, 60, 120),
                         (int(cx - w * 0.46), int(y_mid)),
                         (int(cx + w * 0.46), int(y_mid)), 2)

    def _draw_shotgun_icon(self, surface: pygame.Surface, rect, alpha: int) -> None:
        """绘制霰弹道具图标：一根炮管朝右，前方发散出一簇散射小弹丸。"""
        cx, cy = rect.centerx, rect.centery
        lw = rect.width * 0.16          # 炮管粗
        bl = rect.width * 0.42          # 炮管半长（中心点左右）
        # 炮管主体（水平粗线，从中心左侧延伸至右侧炮口）
        pygame.draw.line(surface, (70, 70, 70), (cx - bl, cy), (cx + bl, cy), int(lw))
        # 炮口（右端）加粗节
        pygame.draw.circle(surface, (40, 40, 40), (int(cx + bl), int(cy)), int(lw * 0.7))
        # 散射小弹丸：右侧扇形发散（水平向右 = 0 度，Y 朝下）
        r = rect.width * 0.22
        for deg in (-70, -35, 0, 35, 70):
            rad = deg * math.pi / 180.0
            px = cx + math.cos(rad) * r
            py = cy - math.sin(rad) * r
            pygame.draw.circle(surface, (255, 90, 40), (int(px), int(py)), max(2, lw // 2))
            pygame.draw.line(
                surface, (255, 90, 40),
                (int(cx + bl), int(cy)),
                (int(px), int(py)), 1,
            )

    def _blit_texture(self, surface: pygame.Surface, which: str) -> bool:
        """把用户提供的道具贴图直接贴到道具格中央。

        Args:
            which: "shield" -> 护盾贴图；"speed" -> 加速贴图；"shotgun" -> 霰弹贴图；
                   "laser" -> 激光贴图；"missile" -> 追踪导弹贴图。

        Returns:
            True  : 贴图加载并绘制成功。
            False : 贴图缺失/加载失败（调用方回退到程序化绘制）。
        """
        global _SHIELD_IMG_CACHE, _SPEED_IMG_CACHE, _SHOTGUN_IMG_CACHE
        global _LASER_IMG_CACHE, _MISSILE_IMG_CACHE
        registry = {
            "shield": (_SHIELD_TEXTURE, "shield"),
            "speed": (_SPEED_TEXTURE, "speed"),
            "shotgun": (_SHOTGUN_TEXTURE, "shotgun"),
            "laser": (_LASER_TEXTURE, "laser"),
            "missile": (_MISSILE_TEXTURE, "missile"),
        }
        if which not in registry:
            return False
        path, key = registry[which]
        cache = {"shield": _SHIELD_IMG_CACHE,
                 "speed": _SPEED_IMG_CACHE,
                 "shotgun": _SHOTGUN_IMG_CACHE,
                 "laser": _LASER_IMG_CACHE,
                 "missile": _MISSILE_IMG_CACHE}[which]
        try:
            if cache is None:
                img = pygame.image.load(path)
                img = img.convert_alpha()
                if key == "shield":
                    _SHIELD_IMG_CACHE = img
                elif key == "speed":
                    _SPEED_IMG_CACHE = img
                elif key == "shotgun":
                    _SHOTGUN_IMG_CACHE = img
                elif key == "laser":
                    _LASER_IMG_CACHE = img
                else:
                    _MISSILE_IMG_CACHE = img
            else:
                img = cache
        except (pygame.error, FileNotFoundError):
            return False
        # 按道具格内缩放，保持宽高比，居中（霰弹/激光/导弹放大至贴满整格边缘，突出图标）
        target_ratio = 1.0 if which in ("shotgun", "laser", "missile") else 0.8
        target = ITEM_SIZE * target_ratio
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return False
        scale = min(target / iw, target / ih)
        tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
        scaled = pygame.transform.smoothscale(img, (tw, th))
        surf_rect = scaled.get_rect(center=self.rect.center)
        # 导弹贴图视觉补偿：按常量横/纵微调（负值=往左/往下，正值=往右/往上）
        _MISSILE_VISUAL_XY = (1, -1)
        if which == "missile" and any(_MISSILE_VISUAL_XY):
            surf_rect = surf_rect.move(*_MISSILE_VISUAL_XY)
        # 闪烁阶段微调不透明度
        if self.blinking:
            scaled = scaled.copy()
            scaled.set_alpha(120)
        surface.blit(scaled, surf_rect)
        return True

    def _draw_speed_icon(self, surface: pygame.Surface, rect, alpha: int) -> None:
        """绘制加速道具图标：三个相连的向上三角形（黑色），模仿参考图中的加速符号。
        三个"山形"三角形水平并排连结，表达"速度提升"。"""
        cx = rect.centerx
        cy = rect.centery
        # 三个向上的三角形：顶尖朝上、底边朝下，水平并排相连
        count = 3
        tw = rect.width * 0.22                 # 单三角宽
        th = rect.height * 0.42                # 单三角高
        x0 = cx - count * tw / 2               # 整体左端（相连无间距）
        y_top = cy - th / 2                    # 顶点（上）
        y_bottom = cy + th / 2                 # 底边（下）
        for i in range(count):
            xl = x0 + i * tw                   # 三角左端
            pygame.draw.polygon(surface, (0, 0, 0), [
                (int(xl + tw / 2), int(y_top)),   # 顶点（上）
                (int(xl), int(y_bottom)),          # 左下
                (int(xl + tw), int(y_bottom)),     # 右下
            ])

    def _draw_laser_icon(self, surface: pygame.Surface, rect) -> None:
        """绘制激光道具图标：一条虚线（弹道预测）+ 右端箭头（快速射线命中点）。"""
        cx, cy = rect.centerx, rect.centery
        y = cy
        x0 = cx - rect.width * 0.34            # 虚线左端
        x1 = cx + rect.width * 0.10            # 虚线右端（箭头前收住）
        # 虚线：等距 dash/gap 循环（深色，与其它道具图标一致的"载体"色）
        dash, gap = rect.width * 0.10, rect.width * 0.07
        x = x0
        while x < x1:
            xe = min(x + dash, x1)
            pygame.draw.line(surface, (30, 30, 30),
                             (int(x), y), (int(xe), y),
                             max(2, rect.width // 14))
            x = xe + gap
        # 右端箭头（实心三角，指向命中点）
        ax = cx + rect.width * 0.22
        s = rect.width * 0.15
        pygame.draw.polygon(surface, (30, 30, 30), [
            (int(ax), int(y - s)),                 # 上
            (int(ax + s * 1.3), int(y)),           # 右尖
            (int(ax), int(y + s)),                 # 下
        ])

    def _draw_missile_icon(self, surface: pygame.Surface, rect) -> None:
        """绘制追踪导弹道具图标：竖直小火箭（弹尖朝上）。
        造型对齐用户提供的参考图：深色弹体 + 浅色弹头条纹 + 两侧外张尾翼 + 底部尾焰。"""
        cx, cy = rect.centerx, rect.centery
        bw = rect.width * 0.30          # 弹体宽
        bh = rect.height * 0.56         # 弹体高
        body = pygame.Rect(0, 0, int(bw), int(bh))
        body.center = (int(cx), int(cy + bh * 0.10))   # 弹体略偏下，给弹头和尾焰留位
        # 尾焰（弹体下方：小号橙黄火焰）
        fy = body.bottom - 1
        fw = bw * 0.42
        fh = bh * 0.26
        pygame.draw.polygon(surface, (255, 150, 40), [
            (int(cx - fw / 2), int(fy)),
            (int(cx + fw / 2), int(fy)),
            (int(cx), int(fy + fh)),
        ])
        # 弹体（深色）
        pygame.draw.rect(surface, (45, 45, 50), body, border_radius=max(2, int(bw * 0.3)))
        # 弹头（弹体上方浅色尖三角）
        nose = [
            (int(body.left), int(body.top + 1)),
            (int(body.right), int(body.top + 1)),
            (int(cx), int(body.top - bh * 0.34)),
        ]
        pygame.draw.polygon(surface, (215, 215, 220), nose)
        # 弹体浅色条纹（中部横带）
        stripe = pygame.Rect(0, 0, int(bw * 0.9), max(2, int(bh * 0.12)))
        stripe.center = (int(cx), int(body.centery))
        pygame.draw.rect(surface, (215, 215, 220), stripe)
        # 两侧外张尾翼（深色小翼）
        fw2 = bw * 0.55                   # 翼展半宽
        fh2 = bh * 0.34                   # 翼高
        fy2 = body.bottom - fh2 * 0.2
        for side in (-1, 1):
            pygame.draw.polygon(surface, (28, 28, 33), [
                (int(cx + side * bw * 0.35), int(fy2 - fh2)),
                (int(cx + side * fw2), int(fy2)),
                (int(cx + side * bw * 0.35), int(fy2)),
            ])