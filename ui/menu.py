# -*- coding: utf-8 -*-
"""
Phase UI 第一步 - MenuSystem（多级菜单导航系统）

定位：表现层（ui/）。仅负责菜单页面的构建、导航、绘制与输入分发；
      不持有任何游戏核心状态（画面 / 战斗逻辑归 main.Game）。
      难度、模式等用户选择通过回调回传给 main.Game 处理。

组成：
  - UiButton    : 一个按钮（矩形 + 标签 + 点击回调 + 可用态）。
  - MenuScreen  : 一个菜单页（标题 + 若干按钮 + 可选 on_draw 动态区 + 返回）。
  - MenuSystem  : 页面栈驱动的前进 / 返回导航，负责绘制与鼠标/键盘输入。

导航规则：
  - 点击按钮 / 回车：执行按钮回调（通常 push 新页，或 pop 返回）。
  - ESC / Backspace / 上排返回按钮：pop 返回上一页（根页不动作）。
  - ↑ ↓ 切换焦点，Enter/Space 确认。

交互反馈：
  - 鼠标悬停 / 键盘焦点：高亮描边。
  - 按钮点击：播放 AudioManager 的 ui_click 音效（音频不可用时静默）。
"""

import math

import pygame

from core.game_fonts import game_font
from core.settings import (
    COLOR_BG,
    COLOR_FOOTER_BG,
    COLOR_FOOTER_TEXT,
    COLOR_TEXT,
    FOOTER_AUTHOR,
    FOOTER_BG_ALPHA,
    FOOTER_YEAR,
    GAME_VERSION,
    MENU_BTN_GAP,
    MENU_BTN_H,
    MENU_BTN_TOP,
    MENU_BTN_W,
    MENU_FOOTER_H,
    MENU_TITLE_Y,
    PREVIEW_CARD_BG,
    PREVIEW_CARD_BORDER,
    PREVIEW_CARD_PAD,
    PREVIEW_CARD_RADIUS,
    PREVIEW_CELL_SIZE,
    PREVIEW_GAP,
    PREVIEW_GROUND,
    PREVIEW_LABEL_COLOR,
    PREVIEW_LABEL_GAP,
    PREVIEW_LABEL_H,
    PREVIEW_SCALE_MIN,
    PREVIEW_SLIDE,
    PREVIEW_SMOOTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SFX_BUTTON_HOVER_VOLUME,
    SFX_NAME_CLICK,
    SFX_NAME_HOVER,
    TRIANGLE_ANIM_AMPLITUDE,
    TRIANGLE_ANIM_SPEED,
    TRIANGLE_GAP,
    TRIANGLE_HALF_RATIO,
    TRIANGLE_LEN,
    WINDOW_HEIGHT,
)

# 菜单配色（沿用项目的金属感，悬停提亮）
COLOR_BTN_BG = (80, 80, 90)
COLOR_BTN_BORDER = (220, 220, 225)
COLOR_BTN_HOVER = (120, 130, 150)
COLOR_BTN_DISABLED = (45, 45, 50)
COLOR_BTN_DISABLED_TEXT = (110, 110, 115)
COLOR_TITLE = (255, 235, 160)


def _draw_select_triangles(surface, rect, color) -> None:
    """高亮指示三角：左右各一、尖端都指向按钮（沿按钮垂直中心对称），并做镜像摆动。

    左三角形底边朝左、顶点向右（正对按钮左缘）；
    右三角形底边朝右、顶点向左（正对按钮右缘）。
    摆动：左右共用同一相位 → 左箭右移时右箭同步左移（镜像对向），
    幅度 ≤ TRIANGLE_GAP 保证尖端始终不进入按钮区域、不重叠字体。
    """
    half = max(4, int(rect.h * TRIANGLE_HALF_RATIO))
    cy = rect.centery
    t = pygame.time.get_ticks() / 1000.0
    dx = TRIANGLE_ANIM_AMPLITUDE * math.sin(t * TRIANGLE_ANIM_SPEED)
    pygame.draw.polygon(surface, color, [              # 左三角：尖端朝右
        (rect.left - TRIANGLE_GAP + dx, cy),
        (rect.left - TRIANGLE_GAP - TRIANGLE_LEN + dx, cy - half),
        (rect.left - TRIANGLE_GAP - TRIANGLE_LEN + dx, cy + half),
    ])
    pygame.draw.polygon(surface, color, [              # 右三角：尖端朝左
        (rect.right + TRIANGLE_GAP - dx, cy),
        (rect.right + TRIANGLE_GAP + TRIANGLE_LEN - dx, cy - half),
        (rect.right + TRIANGLE_GAP + TRIANGLE_LEN - dx, cy + half),
    ])


def _ease_out_cubic(p: float) -> float:
    """三次缓出：慢起快落，用于预览卡弹出动画。"""
    return 1.0 - (1.0 - p) ** 3


def column_button_rect(index: int, count: int) -> pygame.Rect:
    """按索引生成按钮矩形：列从标题下方 MENU_BTN_TOP 起，在剩余空间内垂直居中。"""
    total_h = count * MENU_BTN_H + (count - 1) * MENU_BTN_GAP
    free = SCREEN_HEIGHT - MENU_BTN_TOP
    top = MENU_BTN_TOP + max(0, (free - total_h) // 2)
    x = (SCREEN_WIDTH - MENU_BTN_W) // 2
    y = top + index * (MENU_BTN_H + MENU_BTN_GAP)
    return pygame.Rect(x, y, MENU_BTN_W, MENU_BTN_H)


def bottom_button_rect() -> pygame.Rect:
    """固定在窗口下部的按钮矩形（用于「游戏说明」等需上方留白展示文本的页）。"""
    return pygame.Rect(
        (SCREEN_WIDTH - MENU_BTN_W) // 2,
        WINDOW_HEIGHT - MENU_FOOTER_H - 90 - MENU_BTN_H,
        MENU_BTN_W,
        MENU_BTN_H,
    )


_TITLE_SIDE_MARGIN = 36   # 标题左右安全边距（含 3px 描边 + 4px 投影外扩）
_TITLE_MIN_SIZE = 24      # 自适应缩放下限，避免极端长标题缩到不可读
_TITLE_FIT_CACHE = {}     # (text, 基准高度, 可用宽度) -> 缩好的字体，避免每帧新建


def _fit_title_font(text, font, max_width):
    """标题自适应字号：文字宽度超出可视区时等比缩小，保证首尾不被窗口裁切。

    背景：菜单标题统一按 SCREEN_WIDTH 居中绘制，长标题（如
    「双人对战 · 钢铁废墟 · 选择对局数」）在 64px 下实测 938px > 800px，
    两侧各溢出约 69px，导致首字「双」与末字「数」被挤到窗口外。
    这里改为按实际测量宽度反推字号（宽度已够则原样返回，零开销）。
    """
    if font is None:
        return font
    if font.size(text)[0] <= max_width:
        return font
    key = (text, font.get_height(), max_width)
    cached = _TITLE_FIT_CACHE.get(key)
    if cached is not None:
        return cached

    # 中文字体的行高 ≈ 字号 × 1.328（实测 msyh：64→85、88→117），据此反推基准字号
    size = max(_TITLE_MIN_SIZE, int(round(font.get_height() / 1.328)))
    bold = font.get_bold() if hasattr(font, "get_bold") else False
    cand = game_font(size, bold=bold)
    # 先按超宽比例一步缩到位，再逐级微调，保证最终宽度严格不越界
    while size > _TITLE_MIN_SIZE and cand.size(text)[0] > max_width:
        ratio = max_width / float(cand.size(text)[0])
        size = max(_TITLE_MIN_SIZE, min(size - 1, int(size * ratio * 0.995)))
        cand = game_font(size, bold=bold)
    _TITLE_FIT_CACHE[key] = cand
    return cand


def _draw_styled_title(surface, text, font, center) -> None:
    """绘制游戏风标题文字：金色填充 + 深色描边 + 投影。

    用于替代模糊的 AI 标题图——真实字体渲染，100% 清晰，
    且只是透明文字层，不会凭空多出底部背景，与周围界面自然融合。
    """
    main_color = COLOR_TITLE          # (255, 235, 160) 金色
    outline_color = (18, 16, 10)      # 近黑描边
    shadow_color = (0, 0, 0)          # 投影

    # 1) 投影（向下偏移 + 半透明）
    shadow = font.render(text, True, shadow_color)
    shadow.set_alpha(130)
    surface.blit(shadow, shadow.get_rect(center=(center[0] + 4, center[1] + 7)))

    # 2) 描边：8 方向偏移铺深色文字，形成轮廓
    outline = font.render(text, True, outline_color)
    orect = outline.get_rect(center=center)
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            if dx == 0 and dy == 0:
                continue
            surface.blit(outline, orect.move(dx, dy))

    # 3) 主体文字（金色）
    main = font.render(text, True, main_color)
    surface.blit(main, main.get_rect(center=center))


def _draw_styled_char(surface, ch, font, pos) -> None:
    """在 pos（字符中心）绘制单个游戏风文字：阴影 + 描边 + 金填充。"""
    main_color = COLOR_TITLE
    outline_color = (18, 16, 10)
    shadow_color = (0, 0, 0)

    shadow = font.render(ch, True, shadow_color)
    shadow.set_alpha(130)
    surface.blit(shadow, shadow.get_rect(center=(pos[0] + 4, pos[1] + 7)))

    outline = font.render(ch, True, outline_color)
    orect = outline.get_rect(center=pos)
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            if dx == 0 and dy == 0:
                continue
            surface.blit(outline, orect.move(dx, dy))

    main = font.render(ch, True, main_color)
    surface.blit(main, main.get_rect(center=pos))


def _draw_arced_title(surface, text, font, center_x, base_y, offsets, step=None) -> None:
    """按逐字垂直偏移绘制弧形标题。offsets[i] 为第 i 字相对基线的 y 偏移（正=向下）。"""
    n = len(text)
    if step is None:
        # 按字形实际宽度排版，仅留极细间隙，避免字距过宽
        step = int(font.size(text[0])[0] * 1.06)
    start_x = center_x - step * (n - 1) / 2.0
    for i, ch in enumerate(text):
        _draw_styled_char(surface, ch, font, (start_x + step * i, base_y + offsets[i]))


def draw_footer(surface, font) -> None:
    """在窗口最底部绘制半透明页脚栏：主背景透出 + 作者 · 版权 · 版本。"""
    rect = pygame.Rect(0, WINDOW_HEIGHT - MENU_FOOTER_H, SCREEN_WIDTH, MENU_FOOTER_H)
    # 半透明白底：pygame.draw.rect 不支持 alpha，须用 SRCALPHA 表面填充后贴图
    strip = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    strip.fill((*COLOR_FOOTER_BG, FOOTER_BG_ALPHA))
    surface.blit(strip, rect)
    cy = rect.centery
    left = font.render(FOOTER_AUTHOR, True, COLOR_FOOTER_TEXT)
    surface.blit(left, left.get_rect(midleft=(24, cy)))
    center = font.render(FOOTER_YEAR, True, COLOR_FOOTER_TEXT)
    surface.blit(center, center.get_rect(center=(SCREEN_WIDTH // 2, cy)))
    right = font.render(GAME_VERSION, True, COLOR_FOOTER_TEXT)
    surface.blit(right, right.get_rect(midright=(SCREEN_WIDTH - 24, cy)))


class UiButton:
    """单个按钮。label 可含文本；enabled=False 表示锁定（灰显，不可点）。"""

    def __init__(self, rect, label, on_click=None, enabled=True, note="",
                 preview_stage=None):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.enabled = enabled
        self.note = note   # 可选小字说明（如「已通关」）
        self.preview_stage = preview_stage  # 可选：关联的地图预览索引（悬停时按钮右侧弹出迷你图）

    def render(self, surface, font, focused):
        if not self.enabled:
            bg, border, text_color = COLOR_BTN_DISABLED, COLOR_BTN_DISABLED, COLOR_BTN_DISABLED_TEXT
        elif focused:
            bg, border, text_color = COLOR_BTN_HOVER, COLOR_TITLE, COLOR_TEXT
        else:
            bg, border, text_color = COLOR_BTN_BG, COLOR_BTN_BORDER, COLOR_TEXT
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        label = self.label
        if not self.enabled:
            label = "🔒 " + label
        text = font.render(label, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))
        if focused:
            # 高亮指示三角：左右各一、尖端指向按钮（与描边同色）
            _draw_select_triangles(surface, self.rect, COLOR_TITLE)


class MenuScreen:
    """一个菜单页。on_draw 用于绘制按钮区以外的动态信息（如当前音量值）。
    background：可选整屏背景图像素面（已按窗口尺寸缩放），缺失时用纯色底。
    title_image：可选标题图（如首页 Logo），命中时替代文字标题绘制。
    """

    def __init__(self, screen_id, title, background=None, title_image=None,
                 title_font=None, title_offsets=None):
        self.id = screen_id
        self.title = title
        self.background = background
        self.title_image = title_image
        self.title_font = title_font   # 可选：覆盖系统标题字体（如首页大字粗体）
        self.title_offsets = title_offsets  # 可选：逐字 y 偏移，做弧形标题
        self.buttons = []
        self.on_draw = None   # callable(surface, font, menu_system)

    def add(self, *buttons):
        for b in buttons:
            self.buttons.append(b)
        return self

    def on_enter(self):
        """进入本页时由 MenuSystem 调用（可被子类/回调复用）。"""
        pass


class MenuSystem:
    """页栈驱动的多级菜单导航与输入分发。"""

    def __init__(self, audio=None, preview_loader=None):
        self.audio = audio
        self.preview_loader = preview_loader   # callable(stage_index) -> 预渲染卡片 Surface | None
        self._base_font = None
        self._title_font = None
        self._stack = []               # 页面栈，栈底为根页
        self._focus = 0                # 当前页焦点按钮索引（键盘导航用）
        self._hover = None             # 当前鼠标悬停的按钮索引（None=不在任一按钮上，
                                       # 用于"移入边沿才播悬停音"的一次性判定）
        self._preview_progress = 0.0   # 预览卡弹出动画进度 0..1（帧率无关插值）
        self._preview_tick = 0         # 上一帧时间戳（ms），用于计算 dt

    def set_fonts(self, base_font, title_font):
        self._base_font = base_font
        self._title_font = title_font

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------
    @property
    def current(self) -> MenuScreen:
        return self._stack[-1] if self._stack else None

    def push(self, screen: MenuScreen) -> None:
        self._stack.append(screen)
        self._focus = 0
        self._hover = None
        self._reset_preview()
        screen.on_enter()

    def pop(self) -> None:
        """返回上一页；已在根页则不动作。"""
        if len(self._stack) > 1:
            self._stack.pop()
            self._focus = 0
            self._hover = None
            self._reset_preview()
            if self.current:
                self.current.on_enter()

    def reset_to_main(self) -> None:
        """回到根页（重开游戏 / 返回菜单时调用）。"""
        if self._stack:
            self._stack = self._stack[:1]
            self._focus = 0
            self._hover = None
            self._reset_preview()
            if self.current:
                self.current.on_enter()

    def _reset_preview(self) -> None:
        """切页/返回时清空预览动画进度，避免残留。"""
        self._preview_progress = 0.0
        self._preview_tick = 0

    # ------------------------------------------------------------------
    # 输入
    # ------------------------------------------------------------------
    def _play_click(self):
        if self.audio is not None:
            self.audio.play(SFX_NAME_CLICK)

    def _play_hover(self):
        """鼠标移入按钮时播悬停提示音（音量缩放适中，过低避免盖过其它反馈）。"""
        if self.audio is not None:
            self.audio.play(SFX_NAME_HOVER,
                            volume_scale=SFX_BUTTON_HOVER_VOLUME)

    def handle_mouse(self, pos) -> bool:
        """处理鼠标移动：命中可用按钮则更新焦点并播一次性悬停音。返回是否命中。"""
        scr = self.current
        if scr is None:
            return False
        for i, b in enumerate(scr.buttons):
            # 仅 enabled 按钮参与悬停（与 handle_click 一致，锁定按钮不响不聚焦）。
            if b.rect.collidepoint(pos) and b.enabled:
                # 移入边沿：上一个悬停目标 ≠ 当前按钮（含 None=首次移入）才播一次，
                # 同一按钮内移动不重复；同时同步键盘焦点保持高亮一致。
                if i != self._hover:
                    self._play_hover()
                    self._hover = i
                if i != self._focus:
                    self._focus = i
                return True
        # 未命中任何可用按钮 → 清除悬停标记（离开按钮区）
        self._hover = None
        return False

    def handle_click(self, pos) -> bool:
        """处理左键点击：命中可用按钮则执行回调并播点击音。"""
        scr = self.current
        if scr is None:
            return False
        for b in scr.buttons:
            if b.rect.collidepoint(pos) and b.enabled and b.on_click is not None:
                self._play_click()
                b.on_click()
                return True
        return False

    def handle_key(self, key) -> None:
        """处理键盘导航（ESC/Backspace=返回，↑↓=焦点，Enter/Space=确认）。"""
        scr = self.current
        if scr is None or not scr.buttons:
            return
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            if len(self._stack) > 1:
                self.pop()
                self._play_click()
            return
        n = len(scr.buttons)
        if key in (pygame.K_UP, pygame.K_DOWN):
            step = -1 if key == pygame.K_UP else 1
            for _ in range(n):
                self._focus = (self._focus + step) % n
                if scr.buttons[self._focus].enabled:
                    break
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            b = scr.buttons[self._focus]
            if b.enabled and b.on_click is not None:
                self._play_click()
                b.on_click()

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def render(self, surface) -> None:
        scr = self.current
        if scr is None:
            return
        surface.fill(COLOR_BG)
        if scr.background is not None:
            surface.blit(scr.background, (0, 0))
        # 标题：优先绘制标题图（首页 Logo）；否则以「游戏风文字」渲染
        if scr.title_image is not None:
            surface.blit(scr.title_image,
                         scr.title_image.get_rect(center=(SCREEN_WIDTH // 2, MENU_TITLE_Y)))
        elif self._title_font is not None:
            # 标题自适应字号：长标题按测量宽度缩小，避免首尾被窗口裁切
            title_font = _fit_title_font(
                scr.title, scr.title_font or self._title_font,
                SCREEN_WIDTH - 2 * _TITLE_SIDE_MARGIN,
            )
            if scr.title_offsets:
                _draw_arced_title(surface, scr.title, title_font,
                                  SCREEN_WIDTH // 2, MENU_TITLE_Y, scr.title_offsets)
            else:
                _draw_styled_title(surface, scr.title, title_font,
                                   (SCREEN_WIDTH // 2, MENU_TITLE_Y))
        font = self._base_font
        for i, b in enumerate(scr.buttons):
            b.render(surface, font, focused=(i == self._focus and b.enabled))
        if scr.on_draw is not None:
            scr.on_draw(surface, font, self)
        draw_footer(surface, font)
        self._draw_preview(surface, scr)

    def _draw_preview(self, surface, scr) -> None:
        """悬停带 preview_stage 的按钮时，在按钮右侧绘制弹出的地图预览卡（丝滑动画）。

        进度用真实时间做指数平滑插值（帧率无关），并做缓出缩放/淡入/上浮。
        """
        # 1) 推进动画进度：目标 = 悬停到"带预览的按钮"且能取到卡片 → 1，否则 → 0
        now = pygame.time.get_ticks()
        dt = (now - self._preview_tick) / 1000.0 if self._preview_tick else 0.0
        self._preview_tick = now

        card = None
        hovered = None
        if self._hover is not None:
            hovered = scr.buttons[self._hover]
            if (hovered.preview_stage is not None
                    and self.preview_loader is not None):
                card = self.preview_loader(hovered.preview_stage)
        target = 1.0 if card is not None else 0.0
        if dt > 0:
            k = min(1.0, dt * PREVIEW_SMOOTH)
            self._preview_progress += (target - self._preview_progress) * k
            if abs(self._preview_progress - target) < 0.001:
                self._preview_progress = target
        # else: 首帧仅记录时间戳，进度保持（从 0 开始缓入，避免瞬跳到目标）

        # 2) 进度足够大才绘制（避免贴近 0 时缩放成 0 像素的噪声帧）
        if card is None or self._preview_progress < 0.004:
            return
        e = _ease_out_cubic(self._preview_progress)
        cw, ch = card.get_size()
        sw = max(1, int(cw * (PREVIEW_SCALE_MIN + (1.0 - PREVIEW_SCALE_MIN) * e)))
        sh = max(1, int(ch * (PREVIEW_SCALE_MIN + (1.0 - PREVIEW_SCALE_MIN) * e)))
        scaled = pygame.transform.smoothscale(card, (sw, sh))
        scaled.set_alpha(int(255 * e))
        x = hovered.rect.right + PREVIEW_GAP
        y = hovered.rect.centery - sh // 2 - int((1.0 - e) * PREVIEW_SLIDE)
        surface.blit(scaled, (x, y))