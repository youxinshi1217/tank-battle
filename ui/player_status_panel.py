# -*- coding: utf-8 -*-
"""
Phase 7.0-C - Player Status Panel（玩家状态面板 · AMMO 弹药显示）
Phase 7.1 - 新增 SCORE / KILLS 玩家实时状态显示（SCORE 自 HUD 迁入）
Phase 7.2 - SCORE / KILLS 升级为上下并列档案格（标签左上 / 数值右下；P2 右栏镜像）
            档案格横向收于左侧统计区（_CELL_W），避让中央波次档案卡与中场读条。
Phase 7.3 - 换弹读条：常态弹匣打光进入换弹读秒时，AMMO 图标行整体替换为
            高亮黑读条（两端向中央收缩，与中场休息读条同款）+ 倒计时秒数。
Phase 7.4 - 白底祛除：白底子弹贴图裁剪后，框内凹角/过渡白像素在不透明白底下
            残留成可见白渣；新增 _dewhite 两级清洗（纯白透明 + 浅灰按白度衰减），
            仅作用于默认子弹/霰弹两颗图标，玩家坦克图标路径不动。

定位：独立 UI 层，位于游戏区下方 UI 状态区（白色底带）内。
职责：只负责玩家个人状态的纯显示；只从 Game 实例读取数据，不保存任何游戏核心状态。

不负责：
  - 游戏逻辑 / 状态切换 / 菜单 / Victory / Game Over / 按钮。
  - SCORE / WAVE（属于 HUD）。
  - 弹药逻辑（发射 / 消耗 / 重装 / 拾取）——全部由 player_tank 与 main 负责。

Phase 7.0-C AMMO 弹药显示（立正横排 + 两种模式动态切换）：
  - 常态（未持霰弹）：显示玩家默认子弹弹匣 UI。
      数据 = player_tank.ammo（0~MAGAZINE_CAPACITY），
      贴图 = 「坦克炮弹弹匣图标.png」（横版，加载时旋转 90° 立正）。
  - 霰弹模式（捡到霰弹道具后，shotgun_active=True）：
      数据 = player_tank.shotgun_ammo（真实剩余次数，可叠加、不封顶，1~N），
      贴图 = 「霰弹显示图标.png」（用户提供的竖版显示图标，本身立正、无需旋转）。
  - 霰弹剩余次数耗尽（shotgun_ammo 归零）→ 自动切回常态默认弹匣 UI。
  - 子弹图标"立正"后横排摆放，间距紧密；
    弹药显示位于 PLAYER 1 下方独立区域，不与 PLAYER 1 绑定。
  - 已消耗的弹药不显示（无灰色占位格）。
  - 旧的地图左上角弹药 UI（HUD）已移除，本面板为唯一弹药显示。纯表现层，
    只读 player_tank 数据，不修改弹药逻辑 / 任何核心文件。
"""
import colorsys
import math
import os

import pygame

from core.game_fonts import game_font
from core.settings import (
    COLOR_PLAYER3_TANK,
    COLOR_UI_AREA_TEXT,
    UI_AREA_GLOW_RED,
    UI_AREA_GLOW_BLUE,
    HUD_FONT_SIZE,
    INTERMISSION_BAR_FILL,
    INTERMISSION_BAR_H,
    INTERMISSION_BAR_TRACK,
    INTERMISSION_BAR_UI_TOP,
    INTERMISSION_BAR_W,
    INTERMISSION_INCOMING_BREATH_PERIOD,
    INTERMISSION_INCOMING_COLOR,
    INTERMISSION_NUM_COLOR,
    INTERMISSION_NUM_GAP,
    INTERMISSION_NUM_SIZE,
    MAGAZINE_CAPACITY,
    RELOAD_DURATION,
    RELOAD_UI_BAR_H,
    RELOAD_UI_BAR_W,
    RELOAD_UI_BOTTOM_OFFSET,
    RELOAD_UI_FILL,
    RELOAD_UI_NUM_COLOR,
    RELOAD_UI_NUM_GAP,
    RELOAD_UI_NUM_SIZE,
    RELOAD_UI_TRACK,
    SCREEN_WIDTH,
    SHOTGUN_MAGAZINE,
    STATUS_PANEL_HEIGHT,
    UI_AREA_Y,
)

# ------------------------------------------------------------------
# 贴图路径（本模块私有）：位于项目根目录；面板在 ui/ 下，向上两级定位到项目根
# ------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DEFAULT_ICON_FILENAME = "坦克炮弹弹匣图标.png"   # 常态：默认子弹弹夹（横版，需立正）
_SHOTGUN_ICON_FILENAME = "霰弹显示图标.png"        # 霰弹模式：用户提供的竖版显示图标
_P1_ICON_FILENAME = "红色坦克图标.png"             # P1 玩家身份图标（双人模式）
_P2_ICON_FILENAME = "蓝色坦克图标.png"             # P2 玩家身份图标（双人模式）
# P3 无独立贴图文件：复用红坦克贴图做色相旋转染绿（同一套车体艺术，绿色车身），
# 与红/蓝图标风格完全一致；红贴图缺失时回退与 P1/P2 同款的程序化迷你坦克（绿色配色）。
_P3_ICON_FILENAME = _P1_ICON_FILENAME
_P3_ICON_HUE_SHIFT = 1.0 / 3.0                    # 红(色相0°) → 绿(色相120°)

_DEFAULT_ICON_PATH = os.path.join(_PROJECT_ROOT, _DEFAULT_ICON_FILENAME)
_SHOTGUN_ICON_PATH = os.path.join(_PROJECT_ROOT, _SHOTGUN_ICON_FILENAME)
_P1_ICON_PATH = os.path.join(_PROJECT_ROOT, _P1_ICON_FILENAME)
_P2_ICON_PATH = os.path.join(_PROJECT_ROOT, _P2_ICON_FILENAME)
_P3_ICON_PATH = os.path.join(_PROJECT_ROOT, _P3_ICON_FILENAME)

# ------------------------------------------------------------------
# 布局常量：子弹立正 + 横排、间距紧密、与 PLAYER 1 分离
# ------------------------------------------------------------------
_LABEL_X = 20              # 左侧内边距
_LABEL_MARGIN = 20         # 面板边缘文字内边距（左栏左边 / 右栏右边）
_PANEL_MID_X = SCREEN_WIDTH // 2   # 左右分栏中线（PVP：左栏 [0,mid) 右栏 [mid,width)）
_LABEL_TOP = 12            # PLAYER 1 标签距 UI 区顶部（独立区；单人保持原位）
_LABEL_TOP_DUAL = 27       # 双人模式 PLAYER 标签垂直中心（与 50px 图标中心对齐，图标左置）
_AMMO_TOP = 48             # AMMO 弹药行距 UI 区顶部（单人；图标与下方档案格分离）
_AMMO_TOP_DUAL = 54        # 双人模式 AMMO 行保持 54 不动（用户要求，不随标签移动）
# 玩家坦克图标（仅双人模式，50px 左置于标签左侧、垂直居中于上区）：
_PLAYER_ICON_SIZE = 50     # 图标边长（18→36→50 用户要求 2.8 倍；等比 fit 后居中于透明板）
_PLAYER_ICON_TOP = 2       # 图标顶 y（双人模式；图标底 y=52 与 AMMO 顶 54 留 2px 空隙）
_PLAYER_ICON_GAP = 8       # 图标与右侧 PLAYER 文字的间距
_P2_ICON_BRIGHTNESS = 1.45 # P2 蓝色坦克提亮系数（HSV 亮度 V 倍率，防深色发黑）
_P2_ICON_SAT_SCALE = 0.75  # P2 提亮时饱和度缩放（压低过饱和蓝，观感更亮更清）
_P1_ICON_FALLBACK = ((204, 30, 30), (40, 5, 5))    # 红色坦克（同 COLOR_PLAYER_TANK 配色兜底）
_P2_ICON_FALLBACK = ((60, 90, 210), (10, 10, 60))  # 蓝色坦克（同 COLOR_P2_TANK 配色兜底）
_P3_ICON_FALLBACK = ((46, 190, 92), (8, 42, 20))   # 绿色坦克（同 COLOR_P3_TANK 配色兜底）
# 档案格（SCORE/KILLS）：上下各占一行、统计区宽度（标签左上 / 数值右下，P2 镜像）
_CELL_TOP = 88             # 第一个档案格顶 y（清波读条数字下方）
_CELL_H = 29               # 档案格高
_CELL_GAP = 4              # 两格间距
_CELL_MARGIN_X = 20        # 格左右内边距（与 _LABEL_MARGIN 一致）
_CELL_W = 130              # 档案格宽（260→130 用户要求减半；仍收于左/右缘，避让中央波次卡）
_CELL_RADIUS = 8           # 档案格圆角（克制档案系）
_CELL_BG = (40, 40, 46)            # 档案格底色（深色，适配深色驾驶舱底带）
_CELL_BORDER = (70, 70, 78)         # 档案格中性描边（默认；P1/P2 用阵营描边覆盖）
_CELL_STROKE_P1 = UI_AREA_GLOW_RED  # P1 档案格描边（红，与坦克同色）
_CELL_STROKE_P2 = UI_AREA_GLOW_BLUE # P2 档案格描边（蓝，与坦克同色）
_CELL_STROKE_P3 = COLOR_PLAYER3_TANK  # P3 档案格描边（绿，与坦克同色；三人混战中栏）
_CELL_LABEL_COLOR = (224, 224, 228) # 标签色（浅灰，深色底清晰）
_CELL_VALUE_COLOR = (255, 255, 255) # 数值色（纯白，深色底醒目）
_CELL_LABEL_PAD_X = 8      # 标签横内边距
_CELL_LABEL_PAD_Y = 3      # 标签顶内边距
_CELL_VALUE_PAD_X = 10     # 数值横内边距
_CELL_VALUE_PAD_Y = 5      # 数值底内边距
_CELL_LABEL_SIZE = 12      # 标签字号（小字静默）
_CELL_VALUE_SIZE = 20      # 数值基准字号（加粗圆润；行高超限时自动降号）
_ICON_ROTATE = 90          # 让子弹图标"立正"（旋转角度；方向不对改成 -90）
_ICON_SLOT_W = 22          # 立正后目标框宽度
_ICON_SLOT_H = 32          # 立正后目标框高度
_ICON_GAP = 0              # 图标横向间距（0=子弹紧贴）
_CROP_TOLERANCE = 25       # 背景留白裁剪容差：与背景色差 <= 该值视为留白
_ICON_TEXT_GAP = 12         # AMMO 文字与首颗子弹图标的间隔；图标起点改由文字实际宽度动态推算，避免重叠

# 白底祛除（Phase 7.4）：白底贴图抠图后，裁剪框内的凹角/过渡白像素仍会残留，
# 在不透明白底下成为可见白渣。按"通道白度"两级处理：
#   min(RGB) >= _DEWHITE_MAX_CHANNEL → 纯白/近白，alpha 置 0（彻底透明）
#   min(RGB) 在 [MIN, MAX) 之间      → 浅灰过渡边，alpha 按白度线性衰减
#   min(RGB) < _DEWHITE_MIN_CHANNEL  → 彩色/深色主体，零损伤
_DEWHITE_MAX_CHANNEL = 245
_DEWHITE_MIN_CHANNEL = 200

# 中文字体候选（按优先级）：consolas 无中文字形（中文标签渲染成方块），
# 档案格标签（分数/击毁/胜局）须优先匹配系统中文字体，与 hud.py 同款候选。
_CJK_FONT_CANDIDATES = (
    "microsoftyahei", "microsoftyaheiui", "dengxian",
    "simhei", "simsun", "kaiti",
)


class PlayerStatusPanel:
    """玩家状态面板：render(surface, game)，在游戏区下方 UI 状态区内绘制。"""

    def __init__(self, font_size: int = 20):
        # 面板只持有字体资源与静态贴图，不持有任何游戏状态
        self._font = game_font(font_size)
        # SCORE/KILLS 档案格字体：标签小字（中文候选字体）+ 数值加粗圆润（同倒计时口味）
        self._cell_label_font = self._make_cjk_label_font()
        self._cell_value_font = self._make_cell_value_font()
        # 「即将来敌」字体（与卡片同字号的中文字体，画在读条上方）
        self._incoming_font = self._make_cjk_label_font(HUD_FONT_SIZE)
        self._num_font = None   # 读条倒计时数字字体（懒加载，仅休息态用到）
        self._reload_num_font = None  # 换弹读条数字字体（懒加载，仅换弹态用到）
        # 默认子弹为白底贴图，加载时先祛白再旋转 90° 立正（Phase 7.4）；
        # 霰弹显示图标本身是透明底竖版素材，无需旋转也无需祛白（其近白像素是
        # 画面真实的亮色高光，祛白会误伤）。
        self._default_icon = self._load_icon(_DEFAULT_ICON_PATH, rotate=True,
                                             dewhite=True)
        self._shotgun_icon = self._load_icon(_SHOTGUN_ICON_PATH, rotate=False,
                                             dewhite=False)
        # 玩家身份图标（双人模式 P1 红 / P2 蓝；缺失时回退程序化迷你坦克，P2 额外提亮）
        self._p1_icon = self._load_player_icon(_P1_ICON_PATH, _P1_ICON_FALLBACK)
        self._p2_icon = self._brighten_icon(
            self._load_player_icon(_P2_ICON_PATH, _P2_ICON_FALLBACK))
        # P3（三人混战中栏 · 绿）：复用红坦克贴图色相旋转染绿（同套车体艺术），
        # 红贴图也缺失时 _load_player_icon 已回退程序化红坦克，旋转后即绿色迷你坦克
        self._p3_icon = self._hue_shift_icon(
            self._load_player_icon(_P3_ICON_PATH, _P1_ICON_FALLBACK),
            _P3_ICON_HUE_SHIFT)

    # ------------------------------------------------------------------
    # 贴图加载
    # ------------------------------------------------------------------
    def _load_icon(self, path, rotate: bool = False, dewhite: bool = False):
        """加载贴图：裁剪四周留白，可选去白祛底（Phase 7.4），可选旋转立正。

        dewhite=True 时对裁剪结果做白底祛除（只用于白底子弹/霰弹图标，
        玩家坦克图标保持原路径）：先祛白再旋转，旋转就不产生黑/白插值灰边。
        失败返回 None。
        """
        try:
            img = pygame.image.load(path)
            try:
                img = img.convert_alpha()
            except Exception:
                pass
            img = self._auto_crop(img)
            if dewhite:
                img = self._dewhite(img)
            if rotate and _ICON_ROTATE:
                img = pygame.transform.rotate(img, _ICON_ROTATE)
                if dewhite:
                    # 二次清洗：旋转插值会把透明白与黑色混合出低透明度浅灰像素，
                    # 留在图标边缘形成隐约白边；再祛一次将其压到近透明。
                    img = self._dewhite(img)
            return img
        except Exception:
            return None

    def _dewhite(self, img):
        """白底祛除（Phase 7.4）：把近白像素透明化，消除抠图残留的白渣。

        独立创建 SRCALPHA 表面并逐像素复制（不依赖源图 alpha 标志，headless
        下 convert_alpha 失败也稳定）。两级处理见 _DEWHITE_* 常量注释。
        """
        w, h = img.get_size()
        if w <= 0 or h <= 0:
            return img
        band = _DEWHITE_MAX_CHANNEL - _DEWHITE_MIN_CHANNEL
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                c = img.get_at((x, y))
                r, g, b = c.r, c.g, c.b
                m = min(r, g, b)
                a = c.a
                if m >= _DEWHITE_MAX_CHANNEL:
                    a = 0                      # 纯白/近白 → 彻底透明
                elif m >= _DEWHITE_MIN_CHANNEL:
                    a = int(round(a * (1.0 - (m - _DEWHITE_MIN_CHANNEL) / band)))
                out.set_at((x, y), (r, g, b, a))
        return out

    def _auto_crop(self, img):
        """裁掉图标四周的背景/透明留白，只保留图案本体。

        背景判断：以左上角色为背景色，与背景色差 <= _CROP_TOLERANCE 视为留白；
        若带 alpha 通道则同时忽略透明像素。用于消除 56x38 画布内的大片近白留白，
        让立正子弹在 0 间距下真正紧贴。全背景图则不裁剪。
        """
        w, h = img.get_size()
        if w <= 2 or h <= 2:
            return img
        has_alpha = bool(img.get_flags() & pygame.SRCALPHA)
        bg = img.get_at((0, 0))
        min_x, min_y, max_x, max_y = w, h, -1, -1
        for y in range(h):
            for x in range(w):
                c = img.get_at((x, y))
                if has_alpha and c.a <= 16:
                    continue  # 透明像素
                if (
                    abs(c.r - bg.r) <= _CROP_TOLERANCE
                    and abs(c.g - bg.g) <= _CROP_TOLERANCE
                    and abs(c.b - bg.b) <= _CROP_TOLERANCE
                ):
                    continue  # 背景留白
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
        if max_x < min_x or max_y < min_y:
            return img  # 全背景，不裁剪
        return img.subsurface((min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)).copy()

    def _load_player_icon(self, path, fallback_colors):
        """加载玩家身份图标（P1 红 / P2 蓝），等比 fit 到 18×18 透明板。

        复用 _load_icon 的留白裁剪；文件缺失/加载失败时回退程序化迷你坦克
        （同玩家坦克配色），保证双人模式标签上方永远有态可显。
        """
        img = self._load_icon(path, rotate=False)
        if img is None:
            return self._make_fallback_icon(fallback_colors)
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return self._make_fallback_icon(fallback_colors)
        scale = min(_PLAYER_ICON_SIZE / iw, _PLAYER_ICON_SIZE / ih)
        w, h = max(1, int(iw * scale)), max(1, int(ih * scale))
        img = pygame.transform.smoothscale(img, (w, h))
        out = pygame.Surface((_PLAYER_ICON_SIZE, _PLAYER_ICON_SIZE), pygame.SRCALPHA)
        out.blit(img, ((_PLAYER_ICON_SIZE - w) // 2, (_PLAYER_ICON_SIZE - h) // 2))
        return out

    def _make_fallback_icon(self, colors):
        """程序化迷你坦克（车身矩形 + 炮塔圆 + 炮管，同玩家坦克造型语言）。

        以 18px 基准几何按 _PLAYER_ICON_SIZE 等比放大（放大后保持一致身形）。
        """
        body, outline = colors
        s = pygame.Surface((_PLAYER_ICON_SIZE, _PLAYER_ICON_SIZE), pygame.SRCALPHA)
        scale = _PLAYER_ICON_SIZE / 18

        def sc(*vals):
            return tuple(max(1, int(v * scale)) for v in vals)

        # 车体：描边外框 + 填充内框，炮塔圆，右侧炮管（近似场上坦克朝向）
        pygame.draw.rect(s, outline, sc(2, 7, 14, 9))
        pygame.draw.rect(s, body, sc(3, 8, 12, 7))
        cx, cy = sc(9, 11)
        pygame.draw.circle(s, outline, (cx, cy), int(3 * scale))
        pygame.draw.circle(s, body, (cx, cy), max(1, int(2 * scale)))
        pygame.draw.rect(s, outline, sc(14, 10, 3, 2))
        return s

    def _brighten_icon(self, img):
        """HSV 提亮滤镜（仅 P2 蓝色坦克用）。

        原 COLOR_P2_TANK=(60,90,210) 整体偏暗、深蓝描边厚重，缩成图标后观感近黑。
        对每个非透明像素：HSV 亮度 V × _P2_ICON_BRIGHTNESS（clamp 1.0）、
        饱和度 S × _P2_ICON_SAT_SCALE，再转回 RGB；透明像素原样保留。
        在 __init__ 一次性完成（~2500 像素，毫秒级），帧渲染零开销。
        """
        if img is None:
            return None
        w, h = img.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(w):
            for y in range(h):
                r, g, b, a = img.get_at((x, y))
                if a <= 8:
                    out.set_at((x, y), (r, g, b, a))
                    continue
                hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                vv = min(1.0, vv * _P2_ICON_BRIGHTNESS)
                ss = min(1.0, ss * _P2_ICON_SAT_SCALE)
                nr, ng, nb = colorsys.hsv_to_rgb(hh, ss, vv)
                out.set_at((x, y),
                           (int(round(nr * 255)), int(round(ng * 255)),
                            int(round(nb * 255)), a))
        return out

    def _hue_shift_icon(self, img, shift: float):
        """HSV 色相旋转滤镜（P3 绿坦克图标用）。

        项目只有红/蓝坦克贴图，没有绿色文件。直接把红贴图整体色相 +120°
        得到同套车体艺术的绿色图标（与 P1/P2 图标风格完全一致）；对每个
        非透明像素旋转色相、保留饱和度与亮度，透明像素原样保留。
        在 __init__ 一次性完成（毫秒级），帧渲染零开销。
        """
        if img is None:
            return None
        w, h = img.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(w):
            for y in range(h):
                r, g, b, a = img.get_at((x, y))
                if a <= 8:
                    out.set_at((x, y), (r, g, b, a))
                    continue
                hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                hh = (hh + shift) % 1.0
                nr, ng, nb = colorsys.hsv_to_rgb(hh, ss, vv)
                out.set_at((x, y),
                           (int(round(nr * 255)), int(round(ng * 255)),
                            int(round(nb * 255)), a))
        return out

    def _make_cjk_label_font(self, size: int = _CELL_LABEL_SIZE):
        """中文标签字体（分数/击毁/胜局/即将来敌等），一律加粗（高亮醒目）。

        改用随包内置中文字体（避免 SysFont/match_font 触发系统字体枚举，
        打包 exe 后该枚举可能因注册表异常值而崩溃）。
        """
        return game_font(size, bold=True)

    def _make_cell_value_font(self):
        """档案格数值字体：内置中文字体加粗（数字更肥、圆润，同倒计时口味）。

        若字体行高超出档案格可用高度则逐步降号，保证数值永不裁切出格。
        """
        budget = _CELL_H - _CELL_VALUE_PAD_Y
        size = _CELL_VALUE_SIZE
        while size > 12 and game_font(size).get_height() > budget:
            size -= 1
        return game_font(size, bold=True)

    def render(self, surface: "pygame.Surface", game) -> None:
        """在 UI 状态区（白色底带）上绘制玩家状态面板内容。

        Args:
            surface: 目标绘图表面（白色底带已由 main._render_ui_area() 绘制）。
            game:    游戏主实例，面板从中读取玩家数据。
        """
        mode = getattr(game, "match_mode", None)
        p3_tank = getattr(game, "player3_tank", None)
        is_dual = (mode in ("pvp", "pvpe")
                   and getattr(game, "player2_tank", None) is not None)
        if mode == "pvp3" and p3_tank is not None:
            # 三人混战：左红 P1 / 中绿 P3 / 右蓝 P2，屏宽三等分栏。
            # 每栏与双人模式完全同一套渲染代码（图标/标签/AMMO/档案格），
            # 仅水平位置与栏内对齐不同：左右两栏同双人模式（左对齐/右对齐），
            # 中栏整体居中于自己的三分之一。
            third = SCREEN_WIDTH // 3
            self._render_player(surface, game, game.player_tank, "PLAYER 1",
                                left=0, right=third,
                                align="left", with_icon=True)
            self._render_player(surface, game, p3_tank, "PLAYER 3",
                                left=third, right=third * 2,
                                align="center", with_icon=True)
            self._render_player(surface, game, game.player2_tank, "PLAYER 2",
                                left=third * 2, right=SCREEN_WIDTH,
                                align="right", with_icon=True)
        elif is_dual:
            # 双人模式（PVP 对抗 / PvPvE 协作）：左右分栏，P1 左栏 / P2 右栏。
            # 布局与 PVP 完全一致；PvPvE 为协作模式，SCORE/KILLS 显示全局团队分数
            # （_stat_values 非 pvp 分支返回全局值，无需额外处理）。
            self._render_player(surface, game, game.player_tank, "PLAYER 1",
                                left=0, right=_PANEL_MID_X,
                                align="left", with_icon=True)
            self._render_player(surface, game, game.player2_tank, "PLAYER 2",
                                left=_PANEL_MID_X, right=SCREEN_WIDTH,
                                align="right", with_icon=True)
        else:
            # 单人：单面板全宽左对齐，几何与现状一致
            self._render_player(surface, game, game.player_tank, "PLAYER 1",
                                left=0, right=SCREEN_WIDTH,
                                align="left", with_icon=False)
        # 清波中场休息读条（仅休息态显示；PVP/非休息态自然不绘制）
        self._render_intermission_bar(surface, game)

    def _render_player(self, surface: "pygame.Surface", game, tank,
                       label: str, left: int, right: int,
                       align: str = "left", with_icon: bool = False) -> None:
        """渲染单个玩家面板单元（三栏共用一套代码，按 align 镜像/居中定位）。

        Args:
            left/right: 面板水平边界（三人模式三等分；双人模式左右各半；单人全宽）。
            align:     栏内对齐方式——"left" 左对齐（P1）/ "right" 右对齐（P2，
                       镜像）/ "center" 整体居中（三人混战中栏 P3）。
            with_icon: 顶部是否画玩家坦克图标（双人/三人模式；标签随之下移）。
        """
        cx = (left + right) // 2
        # 0) 玩家身份图标（按坦克身份取色：P1 红 / P2 蓝 / P3 绿）
        if with_icon:
            if tank is getattr(game, "player2_tank", None):
                icon = self._p2_icon
            elif tank is getattr(game, "player3_tank", None):
                icon = self._p3_icon
            else:
                icon = self._p1_icon
            icon_y = UI_AREA_Y + _PLAYER_ICON_TOP
            if align == "left":
                surface.blit(icon, (left + _LABEL_MARGIN, icon_y))
            elif align == "right":
                surface.blit(icon, icon.get_rect(
                    topright=(right - _LABEL_MARGIN, icon_y)))
            else:
                # 中栏：图标+标签作为整体居中于栏中线
                gx = cx - (_PLAYER_ICON_SIZE + _PLAYER_ICON_GAP
                           + self._font.size(label)[0]) // 2
                surface.blit(icon, (gx, icon_y))
        # 1) 玩家身份标签：双人/三人模式下标签右移（P1 图标右侧 / P2 图标左侧）、
        #    垂直中心与图标中心对齐；单人保持左对齐原位
        label_img = self._font.render(label, True, COLOR_UI_AREA_TEXT)
        label_cy = UI_AREA_Y + (_LABEL_TOP_DUAL if with_icon else _LABEL_TOP)
        if with_icon:
            text_off = _LABEL_MARGIN + _PLAYER_ICON_SIZE + _PLAYER_ICON_GAP
            if align == "left":
                surface.blit(label_img, label_img.get_rect(
                    midleft=(left + text_off, label_cy)))
            elif align == "right":
                surface.blit(label_img, label_img.get_rect(
                    midright=(right - text_off, label_cy)))
            else:
                gx = cx - (_PLAYER_ICON_SIZE + _PLAYER_ICON_GAP
                           + label_img.get_width()) // 2
                surface.blit(label_img, label_img.get_rect(
                    midleft=(gx + _PLAYER_ICON_SIZE + _PLAYER_ICON_GAP, label_cy)))
        elif align == "left":
            surface.blit(label_img,
                         label_img.get_rect(midleft=(left + _LABEL_MARGIN, label_cy)))
        else:
            surface.blit(label_img,
                         label_img.get_rect(midright=(right - _LABEL_MARGIN, label_cy)))
        # 2) AMMO 弹药显示（独立区域，图标横排方向随栏位镜像/居中）
        self._render_ammo(surface, game, tank,
                          left=left, right=right, align=align,
                          top=_AMMO_TOP_DUAL if with_icon else _AMMO_TOP)
        # 3) SCORE / KILLS：上下两个整宽档案格（标签左上 / 数值右下；P2 镜像）
        self._render_stat_cells(surface, game, tank, left, right, align)

    def _stat_values(self, game, tank) -> tuple:
        """本玩家 SCORE/KILLS 数值（纯只读，不修改任何状态）。

        PVP：各自战绩 = round_manager 中该玩家的胜局数（每局有效击杀 = 1 击杀 = 1 分，
        与全局 score 的 PVP 语义一致：PVP 下 score_manager 唯一写入即玩家互射击杀）。
        PvPvE：各自个人战绩 = Game 层 _p1/_p2 的亲手击杀得分与击杀数
        （有竞争感；波次/流程奖励不计入，保证个人分 = 纯亲手击杀）。
        其他模式：全局总分/总击杀（现状语义不变）。

        Returns:
            (score, kills) 两个整数，由档案格渲染为"标签 + 大数值"。
        """
        mode = getattr(game, "match_mode", None)
        if mode == "pvp":
            rm = getattr(game, "round_manager", None)
            a = rm.side_a_wins if rm is not None else 0
            b = rm.side_b_wins if rm is not None else 0
            if tank is getattr(game, "player2_tank", None):
                return b, b
            return a, a
        if mode == "pvp3":
            # 三人混战：各自战绩 = 系列赛胜局（P1→side_a / P2→side_b / P3→side_c，
            # 与 1v1 语义一致：每局最终存活 = 1 胜 = 1 分）
            rm = getattr(game, "round_manager", None)
            if tank is getattr(game, "player2_tank", None):
                w = rm.side_b_wins if rm is not None else 0
            elif tank is getattr(game, "player3_tank", None):
                w = rm.side_c_wins if rm is not None else 0
            else:
                w = rm.side_a_wins if rm is not None else 0
            return w, w
        if mode == "pvpe":
            if tank is getattr(game, "player2_tank", None):
                return (getattr(game, "_p2_score", 0),
                        getattr(game, "_p2_kills", 0))
            return (getattr(game, "_p1_score", 0),
                    getattr(game, "_p1_kills", 0))
        sm = getattr(game, "score_manager", None)
        return (getattr(sm, "current_score", 0),
                getattr(sm, "kill_count", 0))

    def _render_stat_cells(self, surface: "pygame.Surface", game, tank,
                           left: int, right: int, align: str) -> None:
        """SCORE/KILLS 上下并列档案格（统计区宽度；P2 右栏镜像 / 中栏居中）。

        每个格子 = 浅灰圆角底 + 细描边，标签小字居左上角、数值加粗圆体靠
        右下角（P2 镜像：标签右上 / 数值左下，与整栏右对齐视觉一致；
        三人混战中栏 P3 与左栏同向，整格居中于自己的三分之一）。
        宽取 _CELL_W 收于栏外侧，避免盖住白色状态栏中央的波次档案卡与中场读条。
        """
        score, kills = self._stat_values(game, tank)
        # 标签文案按模式：非 PVP = 分数/击毁；PVP/三人混战第二格为胜局数
        # （每局有效击杀=+1 胜=+1 分）
        if getattr(game, "match_mode", None) in ("pvp", "pvp3"):
            labels = ("分数", "胜局")
        else:
            labels = ("分数", "击毁")
        if align == "left":
            x0 = left + _CELL_MARGIN_X
            x1 = x0 + _CELL_W
        elif align == "right":
            x1 = right - _CELL_MARGIN_X
            x0 = x1 - _CELL_W
        else:
            x0 = (left + right) // 2 - _CELL_W // 2
            x1 = x0 + _CELL_W
        # 描边按玩家身份取阵营色（P1 红 / P2 蓝 / P3 绿；单人模式中性描边）
        if tank is getattr(game, "player2_tank", None):
            stroke = _CELL_STROKE_P2
        elif tank is getattr(game, "player3_tank", None):
            stroke = _CELL_STROKE_P3
        elif getattr(game, "match_mode", None) in ("pvp", "pvpe", "pvp3"):
            stroke = _CELL_STROKE_P1
        else:
            stroke = _CELL_BORDER
        for i, (label, value) in enumerate(((labels[0], score), (labels[1], kills))):
            rect = pygame.Rect(x0, UI_AREA_Y + _CELL_TOP + i * (_CELL_H + _CELL_GAP),
                               x1 - x0, _CELL_H)
            pygame.draw.rect(surface, _CELL_BG, rect, border_radius=_CELL_RADIUS)
            pygame.draw.rect(surface, stroke, rect, width=1,
                             border_radius=_CELL_RADIUS)
            label_img = self._cell_label_font.render(label, True, _CELL_LABEL_COLOR)
            value_img = self._cell_value_font.render(str(value), True, _CELL_VALUE_COLOR)
            if align == "right":
                surface.blit(label_img, label_img.get_rect(
                    topright=(rect.right - _CELL_LABEL_PAD_X,
                              rect.y + _CELL_LABEL_PAD_Y)))
                surface.blit(value_img, value_img.get_rect(
                    bottomleft=(rect.x + _CELL_VALUE_PAD_X,
                                rect.bottom - _CELL_VALUE_PAD_Y)))
            else:
                surface.blit(label_img, (rect.x + _CELL_LABEL_PAD_X,
                                         rect.y + _CELL_LABEL_PAD_Y))
                surface.blit(value_img, value_img.get_rect(
                    bottomright=(rect.right - _CELL_VALUE_PAD_X,
                                 rect.bottom - _CELL_VALUE_PAD_Y)))

    # ------------------------------------------------------------------
    # 清波中场休息读条（下一波生成倒计时）
    # ------------------------------------------------------------------
    def _render_intermission_bar(self, surface: "pygame.Surface", game) -> None:
        """白色状态栏中央绘制"即将来敌 + 距下一波倒计时读条"。

        仅当 spawn_manager 处于清波休息（in_intermission=True）时绘制，自上而下：
          「即将来敌」（高亮红 + 呼吸灯，读条正上方居中，周期略快于道具）
          读条（浅灰轨道 + 高亮黑填充两端向中央收缩）
          倒计时数字（高亮黑粗体圆润，读条下方居中）
        SCORE/KILLS 档案格收于左右两侧，中央列留空给本组件。非休息态 / PVP 不绘制。
        """
        sm = getattr(game, "spawn_manager", None)
        if sm is None or not getattr(sm, "in_intermission", False):
            return
        total = max(0.0, getattr(sm, "wave_intermission", 0.0) or 0.0)
        remain = max(0.0, getattr(sm, "intermission_timer", 0.0) or 0.0)
        ratio = min(1.0, remain / total) if total > 0 else 0.0

        cx = SCREEN_WIDTH // 2
        bar_w, bar_h = INTERMISSION_BAR_W, INTERMISSION_BAR_H
        # 读条位于白色栏卡片正下方中央列（INTERMISSION_BAR_UI_TOP 为条顶部在白色栏内偏移）
        bar_y = UI_AREA_Y + INTERMISSION_BAR_UI_TOP

        # 「即将来敌」：读条正上方居中，深红 + 呼吸灯（周期略快于道具）
        t = pygame.time.get_ticks() / 1000.0
        alpha = int(255 * (0.6 + 0.4 * math.sin(
            t * (2 * math.pi / INTERMISSION_INCOMING_BREATH_PERIOD))))
        incoming = self._incoming_font.render(
            "即将来敌", True, INTERMISSION_INCOMING_COLOR)
        incoming.set_alpha(alpha)
        incoming_cy = bar_y - INTERMISSION_NUM_GAP - incoming.get_height() // 2
        surface.blit(incoming, incoming.get_rect(center=(cx, incoming_cy)))

        track = pygame.Rect(cx - bar_w // 2, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, INTERMISSION_BAR_TRACK, track,
                         border_radius=bar_h // 2)
        half = int(bar_w / 2 * ratio)
        fill = pygame.Rect(cx - half, bar_y, half * 2, bar_h)
        if fill.width > 0:
            pygame.draw.rect(surface, INTERMISSION_BAR_FILL, fill,
                             border_radius=bar_h // 2)
        # 倒计时数字（粗体，读条下方居中；圆润视觉同开场读条数字）
        if self._num_font is None:
            self._num_font = game_font(INTERMISSION_NUM_SIZE, bold=True)
        num_img = self._num_font.render(f"{remain:.1f}s", True, INTERMISSION_NUM_COLOR)
        num_cy = bar_y + bar_h + INTERMISSION_NUM_GAP + num_img.get_height() // 2
        surface.blit(num_img, num_img.get_rect(center=(cx, num_cy)))

    # ------------------------------------------------------------------
    # AMMO 弹药显示（模式切换 + 立正横排）
    # ------------------------------------------------------------------
    def _current_ammo_info(self, tank):
        """根据玩家状态返回 (图标, 剩余数, 弹匣容量)。

        霰弹模式（shotgun_active=True）→ 霰弹图标 / shotgun_ammo（真实剩余，可叠加）；
        否则常态 → 默认子弹弹匣图标 / ammo / MAGAZINE_CAPACITY。
        只读，缺失/非法值按 0 兜底，不修改玩家对象。
        """
        if tank is None:
            return None, 0, MAGAZINE_CAPACITY
        if bool(getattr(tank, "shotgun_active", False)):
            count = max(0, int(getattr(tank, "shotgun_ammo", 0)))
            return self._shotgun_icon, count, count
        count = max(0, int(getattr(tank, "ammo", 0)))
        return self._default_icon, min(count, MAGAZINE_CAPACITY), MAGAZINE_CAPACITY

    def _render_ammo(self, surface: "pygame.Surface", game, tank,
                     left: int, right: int, align: str,
                     top: int = _AMMO_TOP) -> None:
        """绘制 AMMO 文字 + 立正子弹图标横排（栏内向左/向右镜像，中栏整体居中）。

        top: 行首距 UI 区顶部的 y 偏移（单人=_AMMO_TOP；双人下移=_AMMO_TOP_DUAL）。

        Phase 7.3：常态弹匣打光进入换弹读秒时（count==0 且 is_reloading），
        图标行整行空白，改为绘制换弹读条 + 倒计时数字（与图标二选一，不共存）。
        """
        icon, count, _capacity = self._current_ammo_info(tank)

        caption = self._font.render("AMMO", True, COLOR_UI_AREA_TEXT)
        caption_w = caption.get_width()
        row_cy = UI_AREA_Y + top + _ICON_SLOT_H // 2

        # 横排：图标自栏内起点向侧边铺开（左栏从左往右 / 右栏从右往左 / 中栏居中，
        # 无灰色占位格）
        if icon is None or count <= 0:
            # 弹药打光 → 换弹读条取代图标行（霰弹模式无换弹计时，天然不触发）
            if align == "left":
                surface.blit(caption, caption.get_rect(
                    midleft=(left + _LABEL_MARGIN, row_cy)))
            elif align == "right":
                surface.blit(caption, caption.get_rect(
                    midright=(right - _LABEL_MARGIN, row_cy)))
            else:
                surface.blit(caption, caption.get_rect(
                    center=((left + right) // 2, row_cy)))
            # 换弹读条：仅活人绘制（阵亡坦克死亡即清零 reload_remaining，
            # 双保险防"死人定格读条"——死亡路径不推进 update_ammo，计时器会冻结）
            dead = getattr(game, "_dead_players", set())
            if count <= 0 and getattr(tank, "is_reloading", False) \
                    and tank not in dead:
                self._render_reload_bar(surface, tank, left, right, align, top)
            return
        # 图标基础尺寸（按目标框缩放，同行复用）
        base = self._scale_icon(icon)
        base_w, base_h = base.get_width(), base.get_height()
        gap = _ICON_GAP

        # 图标行起点由 AMMO 文字实际宽度动态推算（左栏从左往右 / 右栏从右往左）
        if align == "left":
            x_start = left + _LABEL_MARGIN + caption_w + _ICON_TEXT_GAP
            avail = (right - _LABEL_MARGIN) - x_start
        elif align == "right":
            x_start = right - _LABEL_MARGIN - caption_w - _ICON_TEXT_GAP - base_w
            avail = x_start - (left + _LABEL_MARGIN)
        else:
            # 中栏：整组（AMMO 文字 + 图标行）居中于栏中线
            x_start = None
            avail = (right - _LABEL_MARGIN) - (left + _LABEL_MARGIN)

        # 叠加后数量远超一行容量时自动缩小图标，保证一行放得下、不挤出栏外
        need = max(0, count * (base_w + gap) - (gap if count > 0 else 0))
        if need > avail and avail > 0:
            k = min(1.0, avail / need)
            scaled = pygame.transform.smoothscale(
                base, (max(1, int(base_w * k)), max(1, int(base_h * k))))
        else:
            scaled = base
        icon_w, icon_h = scaled.get_width(), scaled.get_height()
        icons_w = max(0, count * (icon_w + gap) - (gap if count > 0 else 0))

        # 按方向铺开图标（无灰色占位格，打一发少一个，所见即所得）
        if align == "left":
            x = x_start
            cap_pos = caption.get_rect(midleft=(left + _LABEL_MARGIN, row_cy))
        elif align == "right":
            x = right - _LABEL_MARGIN - caption_w - _ICON_TEXT_GAP - icon_w
            cap_pos = caption.get_rect(midright=(right - _LABEL_MARGIN, row_cy))
        else:
            group_left = (left + right) // 2 - (caption_w + _ICON_TEXT_GAP + icons_w) // 2
            x = group_left + caption_w + _ICON_TEXT_GAP
            cap_pos = caption.get_rect(midleft=(group_left, row_cy))
        surface.blit(caption, cap_pos)
        for _ in range(count):
            surface.blit(scaled, (x, row_cy - icon_h // 2))
            x += (icon_w + gap) if align != "right" else -(icon_w + gap)

    def _render_reload_bar(self, surface: "pygame.Surface", tank,
                           left: int, right: int, align: str,
                           top: int) -> None:
        """绘制换弹读条（Phase 7.3）：与中场休息读条同款的视觉语言。

        读条落在 AMMO 行内底部空白带（行高 32px，图标打光后整行空闲）：
          - 浅灰圆角轨道 + 高亮黑填充"两端向中央收缩"（比例=剩余换弹时间占比）；
          - 右侧（P1）/左侧（P2 镜像）并排一颗高亮黑倒计时秒数；
            三人混战中栏（P3）读条居中于自己的三分之一，秒数并排于条右侧。
        数据只读 tank.reload_remaining / RELOAD_DURATION，不修改任何玩家状态。
        """
        total = max(0.0, float(RELOAD_DURATION))
        remain = max(0.0, float(getattr(tank, "reload_remaining", 0.0)))
        ratio = min(1.0, remain / total) if total > 0 else 0.0

        # 行内底部空白带：条底 = 行底 - 距底偏移
        bar_bottom = UI_AREA_Y + top + _ICON_SLOT_H - RELOAD_UI_BOTTOM_OFFSET
        bar_y = bar_bottom - RELOAD_UI_BAR_H
        bar_w, bar_h = RELOAD_UI_BAR_W, RELOAD_UI_BAR_H
        # 水平居中于图标行起点（与 _render_ammo 同款动态推算，保证换弹条与子弹同列对齐）
        caption_w = self._font.size("AMMO")[0]
        if align == "left":
            cx = left + _LABEL_MARGIN + caption_w + _ICON_TEXT_GAP + bar_w // 2
        elif align == "right":
            cx = right - _LABEL_MARGIN - caption_w - _ICON_TEXT_GAP - bar_w // 2
        else:
            cx = (left + right) // 2

        # 轨道：浅灰圆角；填充：高亮黑，比例收缩（两端向中央）
        track = pygame.Rect(cx - bar_w // 2, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, RELOAD_UI_TRACK, track,
                         border_radius=bar_h // 2)
        half = int(bar_w / 2 * ratio)
        fill = pygame.Rect(cx - half, bar_y, half * 2, bar_h)
        if fill.width > 0:
            pygame.draw.rect(surface, RELOAD_UI_FILL, fill,
                             border_radius=bar_h // 2)

        # 倒计时数字：读条右侧（P1）/左侧（P2 镜像）并排，竖直居中于读条
        if self._reload_num_font is None:
            self._reload_num_font = game_font(RELOAD_UI_NUM_SIZE, bold=True)
        num_img = self._reload_num_font.render(
            f"{remain:.1f}s", True, RELOAD_UI_NUM_COLOR)
        num_cy = bar_y + bar_h // 2
        if align == "right":
            surface.blit(num_img, num_img.get_rect(
                midright=(track.left - RELOAD_UI_NUM_GAP, num_cy)))
        else:
            surface.blit(num_img, num_img.get_rect(
                midleft=(track.right + RELOAD_UI_NUM_GAP, num_cy)))

    def _scale_icon(self, img):
        """按目标框等比缩放图标（保持宽高比；立正旋转已在加载时完成）。"""
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return img
        scale = min(_ICON_SLOT_W / iw, _ICON_SLOT_H / ih)
        w, h = max(1, int(iw * scale)), max(1, int(ih * scale))
        return pygame.transform.smoothscale(img, (w, h))
