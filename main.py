# -*- coding: utf-8 -*-
"""
坦克大战 - 主程序入口
纯双人模式（PVP 1v1）：无 AI 敌人、无单人 / 波次系统。
"""
import os
import sys
import random
import math

import pygame
from core.audio_manager import AudioManager
from core.game_fonts import game_font
from core.game_state import GameState
from core.item_spawn_manager import ItemSpawnManager
from core.level_manager import LevelManager
from core.score_manager import ScoreManager
from core.settings import (
    BULLET_FIRE_COOLDOWN,
    COLOR_BG,
    COLOR_GRID_LINE,
    COLOR_HELP_TEXT,
    COLOR_TEXT,
    FPS,
    GRID_SIZE,
    HELP_TEXT,
    MAGAZINE_CAPACITY,
    MENU_BG_CROP_MAX_RATIO,
    MENU_BG_BLACK_THRESH,
    MENU_BG_IMAGE,
    MENU_BG_PATH,
    MENU_FOOTER_H,
    MENU_TITLE_IMAGE,
    MENU_TITLE_PATH,
    MENU_TITLE_W,
    MENU_VOLUME_STEP,
    PAUSE_ALLOWED_DURING_INTRO,
    PAUSE_AUDIO_LABELS,
    PAUSE_AUDIO_TITLE,
    PAUSE_BTN_GAP,
    PAUSE_BTN_H,
    PAUSE_BTN_LABELS,
    PAUSE_BTN_TOP,
    PAUSE_BTN_W,
    PAUSE_HELP_LABELS,
    PAUSE_HELP_TITLE,
    PAUSE_HOVER_BORDER,
    PAUSE_INFO_TOP,
    PAUSE_OVERLAY_ALPHA,
    PAUSE_SETTINGS_LABELS,
    PAUSE_SETTINGS_TITLE,
    PAUSE_TITLE,
    PAUSE_TITLE_Y,
    PREVIEW_CARD_BG,
    PREVIEW_CARD_BORDER,
    PREVIEW_CARD_PAD,
    PREVIEW_CARD_RADIUS,
    PREVIEW_CELL_SIZE,
    PREVIEW_GROUND,
    PREVIEW_BRICK,
    PREVIEW_LABEL_COLOR,
    PREVIEW_LABEL_GAP,
    PREVIEW_LABEL_H,
    PREVIEW_LABEL_SIZE,
    PREVIEW_STEEL,
    PVP_ROULETTE_ARROW,
    PVP_ROULETTE_CAPTION_SIZE,
    PVP_ROULETTE_CARD_GAP,
    PVP_ROULETTE_CELL,
    PVP_ROULETTE_DURATION_MAX,
    PVP_ROULETTE_DURATION_MIN,
    PVP_ROULETTE_FINAL_INSET,
    PVP_ROULETTE_LABEL_SIZE,
    PVP_ROULETTE_LINE,
    PVP_ROULETTE_RESULT_Y,
    PVP_ROULETTE_SLOTS,
    PVP_ROULETTE_SPIN_CARDS,
    PVP_ROULETTE_STRIP_Y,
    MENU_BTN_H,
    RESULT_BTN_H,
    RESULT_BTN_TOP,
    RESULT_BTN_W,
    RESULT_CARD_BG,
    RESULT_CARD_BORDER,
    RESULT_CARD_LINE_GAP,
    RESULT_CARD_PAD_X,
    RESULT_CARD_PAD_Y,
    RESULT_CARD_TOP,
    RESULT_CARD_W,
    RESULT_LABEL_COLOR,
    RESULT_LOSE_COLOR,
    RESULT_SERIES_TOP,
    RESULT_TITLE_Y,
    RESULT_VALUE_COLOR,
    RESULT_WIN_COLOR,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATUS_PANEL_HEIGHT,
    TANK_SIZE,
    TANK_SPEED,
    TILE_SIZE,
    UI_AREA_Y,
    UI_AREA_BG_TOP,
    UI_AREA_BG_BOTTOM,
    UI_AREA_BG_TOP,
    UI_AREA_BG_BOTTOM,
    UI_AREA_VIGNETTE,
    UI_AREA_GLOW_GREEN,
    UI_AREA_GLOW_RED,
    UI_AREA_GLOW_BLUE,
    UI_AREA_GLOW_ALPHA,
    UI_AREA_GLOW_RED_SCALE,
    UI_AREA_GLOW_GREEN_SCALE,
    UI_AREA_GLOW_BLUE_SCALE,
    UI_AREA_GLOW_GREEN_BREATH_SCALE,
    UI_AREA_GLOW_RED_BREATH_SCALE,
    UI_AREA_SEAM_TOP,
    UI_AREA_SEAM_BOTTOM,
    UI_AREA_BRUSH,
    UI_AREA_BRUSH_ALPHA,
    UI_AREA_VS_BG,
    UI_AREA_VS_RING,
    UI_AREA_VS_INNER,
    UI_AREA_VS_TEXT,
    UI_AREA_VS_RADIUS,
    UI_AREA_DYNAMIC,
    UI_AREA_GLOW_BREATH_AMP,
    UI_AREA_GLOW_BREATH_PERIOD,
    UI_AREA_RELOAD_BOOST,
    UI_AREA_FLASH_DURATION,
    UI_AREA_FLASH_BOOST,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    SHOTGUN_PELLETS,
    SHOTGUN_SPREAD_RADIANS,
    LASER_MAX_BOUNCES,
    LASER_PREVIEW_BOUNCES,
    COLOR_LASER_BY_OWNER,
    COLOR_LASER_FALLBACK,
    COLOR_PLAYER_TANK,
    LASER_PREVIEW_FLOW_SPEED,
    SFX_CANNON_FIRE,
    SFX_CANNON_FIRE_PATH,
    SFX_CANNON_FIRE_VOLUME,
    SFX_ITEM_PICKUP,
    SFX_ITEM_PICKUP_PATH,
    SFX_ITEM_PICKUP_VOLUME,
    SFX_LASER_FIRE,
    SFX_LASER_FIRE_PATH,
    SFX_LASER_FIRE_VOLUME,
    SFX_MISSILE_FLIGHT,
    SFX_MISSILE_FLIGHT_PATH,
    SFX_MISSILE_FLIGHT_VOLUME,
    SFX_MISSILE_LOCK,
    SFX_MISSILE_LOCK_PATH,
    SFX_MISSILE_LOCK_VOLUME,
    SFX_MISSILE_WARN,
    SFX_MISSILE_WARN_PATH,
    SFX_MISSILE_WARN_VOLUME,
    SFX_MISSILE_EXPLODE,
    SFX_MISSILE_EXPLODE_PATH,
    SFX_MISSILE_EXPLODE_VOLUME,
    SFX_PLAYER_DESTROYED,
    SFX_PLAYER_DESTROYED_PATH,
    SFX_PLAYER_DESTROYED_VOLUME,
    SFX_BGM_MENU,
    SFX_BGM_MENU_PATH,
    SFX_BGM_STAGE1,
    SFX_BGM_STAGE1_PATH,
    BGM_STAGE1_FADEIN,
    BGM_STAGE1_FADEOUT,
    BGM_STAGE1_TARGET_VOLUME,
    SFX_BGM_STAGE2,
    SFX_BGM_STAGE2_PATH,
    BGM_STAGE2_FADEIN,
    BGM_STAGE2_FADEOUT,
    BGM_STAGE2_TARGET_VOLUME,
    SFX_BGM_STAGE3,
    SFX_BGM_STAGE3_PATH,
    BGM_STAGE3_FADEIN,
    BGM_STAGE3_FADEOUT,
    BGM_STAGE3_TARGET_VOLUME,
    SFX_BGM_STAGE4,
    SFX_BGM_STAGE4_PATH,
    BGM_STAGE4_FADEIN,
    BGM_STAGE4_FADEOUT,
    BGM_STAGE4_TARGET_VOLUME,
    STAGE_BGM_MAP,
    BGM_STOP_FADE,
    SFX_BUTTON_HOVER_PATH,
    SFX_BUTTON_HOVER_VOLUME,
    SFX_NAME_CLICK,
    SFX_NAME_HOVER,
    TRIANGLE_ANIM_AMPLITUDE,
    TRIANGLE_ANIM_SPEED,
    TRIANGLE_GAP,
    TRIANGLE_HALF_RATIO,
    TRIANGLE_LEN,
    ITEM_LIFETIME,
    ITEM_MAX_ACTIVE,
    ITEM_MIN_SPACING,
    ITEM_SPAWN_INTERVAL,
    ITEM_SPAWN_WEIGHTS,
    LEVEL_BG_ENABLED,
    LEVEL_BG_PATH,
    LEVEL_BG_UI_ALPHA,
    LEVEL_BG_OFFSET_Y,
)
from ui.menu import UiButton, MenuScreen, MenuSystem, _ease_out_cubic, bottom_button_rect, column_button_rect
from core.collision import rect_hits_obstacle
from core import spawn_rules
from core.match_config import PVP_ROUNDS_CHOICES
from core.round_manager import RoundManager
from maps.game_map import GameMap
from maps.map_renderer import MapRenderer
from maps import ljr_zone
from maps.tile import TileType
from stages.stage_01 import STAGE_CONFIG as STAGE_01
from stages.stage_02 import STAGE_CONFIG as STAGE_02
from stages.stage_03 import STAGE_CONFIG as STAGE_03
from stages.stage_04 import STAGE_CONFIG as STAGE_04
from stages.stage_05 import STAGE_CONFIG as STAGE_05
from entities.player_tank import PlayerTank
from entities.laser import Laser, trace_laser_path
from entities.player2_tank import Player2Tank, COLOR_P2_TANK
from entities.player3_tank import Player3Tank, COLOR_P3_TANK
from entities.bullet import Bullet
from entities.shotgun_pellet import ShotgunPellet
from entities.missile import Missile
from entities.item import Item
from ui.player_status_panel import PlayerStatusPanel
from effects.floating_score import FloatingScore
from effects.explosion import Explosion
from effects.screen_shake import CameraShake

# 项目根目录（本文件所在目录）：关卡背景等资源文件按此定位，与运行 cwd 无关。
# 与 core.settings 的 _PROJECT_ROOT 同一定义；曾被遗漏导致 _build_level_bg
# 抛 NameError、关卡背景静默丢失，勿删。
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Phase 8.0/8.1：多 Stage 配置列表。追加新关 = 新增 map_XX/stage_XX 数据文件
# 后，在此列表追加一项 STAGE_CONFIG（Phase 8.1 已落地 Stage 1/2/3；Phase 8.5 追加 Stage 4；
# Phase 8.6 追加 Stage 5「戈壁环岛」）。
# 注意：PVP 随机地图池全程动态读本列表（选图页/ 卡带/ 卡宽），无需额外改动。
STAGES = [STAGE_01, STAGE_02, STAGE_03, STAGE_04, STAGE_05]

# ------------------------------------------------------------------
# Phase 5.4.3 道具系统回退开关
# 注意：本子阶段"只允许修改 main.py"，故暂以模块常量形式存放；
#       后续可整体迁移到 core.settings。False 时完全禁用道具系统
#       （不初始化 / 不更新 / 不渲染），行为等价 Phase 5.3。
# ------------------------------------------------------------------
ITEM_SYSTEM_ENABLED = True

# ------------------------------------------------------------------
# 自弹反弹自伤总开关（PVP 生效）
# 模块常量便于验证脚本运行时 toggle。False 时完全不生效，行为回到现状。
# 规则：玩家自己射出的子弹经反弹（bounce_count>=1）后飞回命中自己，
#       与被敌方子弹击中同等结算（护盾免疫 → 否则被摧毁）。
# ------------------------------------------------------------------
SELF_HIT_ENABLED = True


class ItemSpawnManagerEx(ItemSpawnManager):
    """道具刷新增强（T7）：以 settings 的 ITEM_LIFETIME 创建道具，覆盖冻结文件默认 15s。

    不改冻结文件 item_spawn_manager.py；刷新间隔/数量经构造参数传入（main._load_stage）。
    多玩家避让：PVP 中把 P2 的 rect 并入 update() 的 enemy_rects 列表即可。
    T7.3 道具间距：刷新点与已存在道具保持 ITEM_MIN_SPACING 以上，避免刷在一起。
    """

    def _spawn_one(self, player_rect, enemy_rects):
        pos = self._find_spawn_position(player_rect, enemy_rects)
        if pos is None:
            return None
        cx, cy = pos
        item = Item(cx, cy, self._choose_type(), lifetime=ITEM_LIFETIME)
        self._bind_density(item)
        return item

    def _choose_type(self):
        """按 settings 的 ITEM_SPAWN_WEIGHTS 加权抽选道具类型（全模式统一）。

        权重表缺失/为空/权重全为 0 时回退父类等概率，保证任何配置下都可正常生成。
        """
        kinds = list(ITEM_SPAWN_WEIGHTS.keys())
        weights = [max(0.0, float(ITEM_SPAWN_WEIGHTS[k])) for k in kinds]
        if not kinds or not weights or sum(weights) <= 0:
            return super()._choose_type()
        return random.choices(kinds, weights=weights, k=1)[0]

    def _find_spawn_position(self, player_rect, enemy_rects):
        """父类刷新点选择 + 道具间距限制：与已存在道具中心距 >= ITEM_MIN_SPACING
        （一个范围内只生成一个，避免道具堆叠在一起）。"""
        spacing2 = ITEM_MIN_SPACING * ITEM_MIN_SPACING
        sr, sc = self.player_spawn_tile
        for _ in range(50):
            col = random.randint(0, GRID_SIZE - 1)
            row = random.randint(0, GRID_SIZE - 1)
            if (row, col) == (sr, sc):
                continue
            if self.game_map.get_tile(row, col) != TileType.EMPTY:
                continue
            if spawn_rules.is_spawn_blocked(row, col):
                continue
            cx = col * TILE_SIZE + TILE_SIZE / 2
            cy = row * TILE_SIZE + TILE_SIZE / 2
            test_rect = pygame.Rect(0, 0, self.item_size, self.item_size)
            test_rect.center = (cx, cy)
            if rect_hits_obstacle(test_rect, self.game_map):
                continue
            if player_rect is not None and test_rect.colliderect(player_rect):
                continue
            if any(test_rect.colliderect(er) for er in enemy_rects):
                continue
            # T7.3 道具间距：与场上存活道具中心距 >= ITEM_MIN_SPACING
            if any((cx - it.x) ** 2 + (cy - it.y) ** 2 < spacing2
                   for it in self.items if it.alive):
                continue
            return (cx, cy)
        return None

# ------------------------------------------------------------------
# PVP 局制常量：获胜/判负/开局提示停留秒数
# ------------------------------------------------------------------
PLAYER_KILL_SCORE = 1          # PVP 亲手击杀对方玩家 +1 分
ROUND_PAUSE_SECONDS = 3.0      # 获胜 3s
ROUND_LOSS_PAUSE_SECONDS = 3.0 # 判负 3s
ROUND_INTRO_SECONDS = 3.0      # 首局开战 3s
# 击毁后"先播爆炸、再弹胜利提示"的延迟（秒）：须 ≥ 爆炸特效完整生命周期（约 0.7s）
PVP_EXPLOSION_HOLD_SECONDS = 1.5
# 阵亡玩家坦克移出战场坐标（单位已击毁不留尸体：不渲染、不占空间、不挡路）
PLAYER_DEAD_OFFSCREEN = (-1000, -1000)


# 中文字体候选（按优先级）：consolas 不含中文字形，菜单/按钮/结算的中文会渲染成 “?”，
# 故优先匹配系统中文字体，找不到再回退到 consolas（仍可正常显示英文/数字）。
_CJK_FONT_CANDIDATES = (
    "microsoftyahei",   # 微软雅黑
    "dengxian",         # 等线
    "simhei",           # 黑体
    "simsun",           # 宋体
    "kaiti",            # 楷体
)


def _create_font(size: int, has_cjk: bool = True):
    """创建一个字体对象（委托统一工具，加载随包内置中文字体，避免系统字体枚举崩溃）。"""
    return game_font(size)


# ------------------------------------------------------------------
# 菜单页的 on_draw 辅助（模块级纯函数，保持 Game 代码精简）
# ------------------------------------------------------------------
def _bottom_note(surface, font, text, cy=None, color=None):
    """在窗口底部居中绘制一行提示文字。cy 缺省为紧贴页脚栏上方；color 缺省为 COLOR_TEXT。"""
    y = cy if cy is not None else (WINDOW_HEIGHT - MENU_FOOTER_H - 40)
    t = font.render(text, True, color or COLOR_TEXT)
    surface.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, y)))


def _draw_bottom_note(text):
    """返回一个绑定固定文本的 on_draw 回调。"""
    def draw(surface, font, _menu):
        _bottom_note(surface, font, text)
    return draw


def _volume_value(game, kind):
    """音量 / 音效页的动态区：显示当前百分比 + 是否静音。"""
    def draw(surface, font, _menu):
        cur = game.audio.master if kind == "master" else game.audio.sfx
        name = "音量" if kind == "master" else "音效"
        if game.audio.muted:
            state = "已静音（点恢复开关取消）"
        else:
            state = f"{int(round(cur * 100))}%"
        _bottom_note(surface, font, f"{name}：{state}")
    return draw


def _draw_dashed_polyline(surface, points, color, dash: float = 9.0,
                          gap: float = 6.0, width: int = 2,
                          phase: float = 0.0) -> None:
    """沿折线画等距虚线（激光预测预览用）：每段按 dash/gap 交替绘制。

    phase 为沿折线弧长的"流动相位"（像素）：dash 图案沿整条折线连续向
    落点方向流动（走马灯效果），经过拐点时相位不间断。调用方按时间递增
    phase（如 ticks*speed）即可获得流动动画；phase=0 时退化为静止虚线。
    """
    period = dash + gap
    if period <= 1e-6:
        return
    # 归一化相位到一个周期：弧长游标从 +offset 起，phase 增大时 dash 图案
    # 整体向路径末端（炮口->落点）前移，视觉上从炮管朝前方流动
    offset = math.fmod(phase, period)
    if offset < 0:
        offset += period
    cursor = offset                    # 全局弧长游标（跨段连续，拐点不断流）
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg <= 1e-6:
            continue
        ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
        while cursor < seg:
            start = max(cursor, 0.0)
            end = min(cursor + dash, seg)
            if end > start:
                pygame.draw.line(surface, color,
                                 (int(round(x1 + ux * start)), int(round(y1 + uy * start))),
                                 (int(round(x1 + ux * end)), int(round(y1 + uy * end))),
                                 width)
            cursor += period
        cursor -= seg                   # 换算为下一段的段内坐标


def _draw_help(surface, font, _menu):
    """游戏说明页：逐行渲染 HELP_TEXT（顶部左侧排列，浅色背景上用黑色文字）。"""
    x, y = 90, 240
    for line in HELP_TEXT:
        if line:
            t = font.render(line, True, COLOR_HELP_TEXT)
            surface.blit(t, (x, y))
            y += t.get_height() + 4
        else:
            y += 12
    _bottom_note(surface, font, "↑↓ 选择 · Enter 确认 · ESC 返回",
                 cy=WINDOW_HEIGHT - MENU_FOOTER_H - 172, color=COLOR_HELP_TEXT)


class Game:
    """游戏主类：负责初始化、主循环、事件处理、渲染"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        # 中文字体优先（菜单/按钮/结算中文不再乱码），big 用于标题
        self.font = _create_font(20, has_cjk=True)
        self.big_font = _create_font(64, has_cjk=True)
        # 局间信息面板字体（主标题 / 比分行）
        self._inter_font_title = _create_font(42, has_cjk=True)
        self._inter_font_score = _create_font(26, has_cjk=True)
        # 状态栏中央 VS 徽记字体（Phase 7.5-B）
        self._ui_area_vs_font = _create_font(22, has_cjk=True)
        self._ui_area_vs_font.set_bold(True)
        # 倒计时数字专用字体：微软雅黑（数字圆润）+ 加粗（更肥、更有分量）
        self._inter_font_countdown = _create_font(32, has_cjk=True)
        self._inter_font_countdown.set_bold(True)
        # 首页「坦克大战」标题：专用大字粗体（清晰、游戏感），替代模糊的 AI 标题图
        self.title_font = _create_font(88, has_cjk=True)
        self.title_font.set_bold(True)

        # 关卡战斗背景图：每关一张专属图（关卡配置 bg 字段），由 _load_stage() 按关卡加载。
        # 启动时先置空占位；实际背景在首关/切关时按 stage_config["bg"] 生成（_load_level_bg_for_stage）。
        # 图片缺失/加载失败 或 LEVEL_BG_ENABLED=False 时 self.level_bg=None，渲染回退旧行为（纯色底 + 不透明白带）。
        # 注意：图片为 8-bit RGB（无 alpha），用 convert() 直接铺满；display 已在 set_mode 初始化。
        # LEVEL_BG_OFFSET_Y>0 时整图垂直下移：左上角商标避开关卡顶部障碍物；顶部露出的条带
        # 用"图片上边缘平均色 → 纯色底"纵向渐变软填充（一次性合成，每帧零额外开销）。
        self.level_bg = None
        # 首关/切关时由 _load_stage() 调用 _load_level_bg_for_stage() 按需生成。

        # Phase UI 第一步：音频 / 进度 / 多级菜单（持久化于 save/ 下）
        self.audio = AudioManager()
        # 追踪导弹音效并发较多（飞行/锁定/即将命中可同时响），扩容通道防抢通道
        self.audio.ensure_channels(16)
        # 注册玩家开炮音效（文件缺失 / 无音频设备时安全跳过，不抛异常）
        self.audio.register_sound(SFX_CANNON_FIRE, SFX_CANNON_FIRE_PATH)
        # 注册道具拾取音效（MP3，保持小音量）
        self.audio.register_sound(SFX_ITEM_PICKUP, SFX_ITEM_PICKUP_PATH)
        # 注册激光射线发射音效（wav，0.19s；对标开炮音效）
        self.audio.register_sound(SFX_LASER_FIRE, SFX_LASER_FIRE_PATH)
        # 注册追踪导弹音效（4 个 MP3：飞行 / 锁定 / 即将命中 / 命中爆炸）
        self.audio.register_sound(SFX_MISSILE_FLIGHT, SFX_MISSILE_FLIGHT_PATH)
        self.audio.register_sound(SFX_MISSILE_LOCK, SFX_MISSILE_LOCK_PATH)
        self.audio.register_sound(SFX_MISSILE_WARN, SFX_MISSILE_WARN_PATH)
        self.audio.register_sound(SFX_MISSILE_EXPLODE, SFX_MISSILE_EXPLODE_PATH)
        # 注册玩家坦克被摧毁爆炸音效（仅取爆炸录音前 0.5s）
        self.audio.register_sound(SFX_PLAYER_DESTROYED, SFX_PLAYER_DESTROYED_PATH)
        # 注册悬停提示音（菜单/结果按钮悬停时播放一次；此前仅有常量未注册，实际无声）
        self.audio.register_sound(SFX_NAME_HOVER, SFX_BUTTON_HOVER_PATH)
        # 注册大厅主菜单 BGM（ogg，受控循环 + 首尾淡入淡出）
        self.audio.register_bgm(SFX_BGM_MENU, SFX_BGM_MENU_PATH)
        # 注册第一关战斗 BGM（mp3，受控循环；淡入/循环尾淡出/目标音量按每曲参数接管）
        self.audio.register_bgm(SFX_BGM_STAGE1, SFX_BGM_STAGE1_PATH,
                                fadein=BGM_STAGE1_FADEIN,
                                fadeout=BGM_STAGE1_FADEOUT,
                                target=BGM_STAGE1_TARGET_VOLUME)
        # 注册第二关战斗 BGM（flac，实测 pygame.mixer 可直接加载；参数惯例同第一关，独立常量便于单关微调）
        self.audio.register_bgm(SFX_BGM_STAGE2, SFX_BGM_STAGE2_PATH,
                                fadein=BGM_STAGE2_FADEIN,
                                fadeout=BGM_STAGE2_FADEOUT,
                                target=BGM_STAGE2_TARGET_VOLUME)
        # 注册第三关战斗 BGM（mp3，与第一关同格式，实测可加载；参数惯例同上，独立常量便于单关微调）
        self.audio.register_bgm(SFX_BGM_STAGE3, SFX_BGM_STAGE3_PATH,
                                fadein=BGM_STAGE3_FADEIN,
                                fadeout=BGM_STAGE3_FADEOUT,
                                target=BGM_STAGE3_TARGET_VOLUME)
        # 注册第四关战斗 BGM（mp3，与第一/三关同格式，实测可加载；参数惯例同上，独立常量便于单关微调）
        self.audio.register_bgm(SFX_BGM_STAGE4, SFX_BGM_STAGE4_PATH,
                                fadein=BGM_STAGE4_FADEIN,
                                fadeout=BGM_STAGE4_FADEOUT,
                                target=BGM_STAGE4_TARGET_VOLUME)
        self.selected_stage = 0
        self._build_menu()
        # 选关地图预览卡：懒渲染缓存 + 标签字体（首次悬停某关才生成，进页零开销）
        self._preview_cards = {}
        self._preview_font = None
        # PVP 随机开图转盘：统一尺寸卡带缓存 / 标签字体 / 动画状态 / 落点注入（测试用）
        self._roulette_cards_cache = None
        self._roulette_font = None
        self._roulette_caption_font = None   # 落定状态文字：圆润粗体（雅黑 + bold），懒创建
        self._roulette_state = None
        self._force_pvp_random = None
        # 转盘落定「就用这张图开局」回调：PVP → _pick_pvp_map
        self._roulette_pick = None

        # Phase 7.0-B Player Status Panel（表现层）：仅 PLAYING 时调用；
        # 玩家状态面板：P1/P2 得分 / 击杀 / 弹药显示
        self.player_status_panel = PlayerStatusPanel()

        self.running = True
        self.game_over_flag = False
        self._result_hover = False     # 结果页“返回菜单”按钮悬停态（进入结果状态时复位）
        # 暂停菜单状态（Phase UI Step 1-B；PAUSED 下工作，占位初始化防属性缺失）
        self._pause_section = "main"   # main / settings / help / audio_master / audio_sfx
        self._pause_focus = 0          # 键盘焦点按钮下标
        self._pause_hover = None       # 鼠标悬停按钮下标（None=不在任何按钮上）
        # Phase 6.2：主循环从 MENU 开始（完整生命周期
        # MENU → PLAYING → GAME_OVER/VICTORY → MENU → PLAYING ...）。
        # 首次即初始化一局战斗数据（等价经过一次 reset）。
        self._new_combat()
        self.state = GameState.MENU

    # ------------------------------------------------------------------
    # Phase 6.2 生命周期：重置 / 开始 / 结束
    # 重开一律走 Game.reset()，绝不重新创建 Game 对象（复用窗口/字体/时钟）。
    # ------------------------------------------------------------------
    def _new_combat(self) -> None:
        """初始化一局全新战斗数据。供 __init__ 首次与 reset() 复用。"""
        # Phase 8.0：多 Stage 关卡流程管理（每局重建回 Stage 1）
        self.level_manager = LevelManager(STAGES)
        # 玩家对象在切关复用（跨关保留，不重新创建），故置 None 标记未创建
        self.player_tank = None
        # 双玩家框架（PVP 使用）：P2 恒在场
        self.player2_tank = None
        # 第三玩家（三人混战 pvp3 使用）：鼠标控制，不在场时为 None
        self.player3_tank = None
        # 道具管理器在 _load_stage 内按需创建/复用于切关；先置 None 标记未创建
        self.item_spawn_manager = None
        # 建立首关战斗环境（地图 / 玩家 / 道具 / 战斗列表）
        self._load_stage(self.level_manager.current_stage)

        # Phase 6.4 独立分数系统：每局重建即归零（重开经由 reset()->_new_combat()）
        self.score_manager = ScoreManager()

        # 局制管理（系列赛）：PVP 默认 5 局，start_pvp 按玩家选择重建
        self.round_manager = RoundManager("pvp", rounds=PVP_ROUNDS_CHOICES[0])
        self.match_mode = "pvp"        # pvp=双人 1v1；pvp3=三人混战（P3 鼠标）
        # 菜单入口记忆：地图选择/对局数页据此决定开局调 start_pvp 还是 start_pvp3
        self._menu_mode = "pvp"
        # 三人混战系列赛胜局账（owner -> 胜局数；仅 pvp3 有意义）
        self._series_wins = {"p1": 0, "p2": 0, "p3": 0}
        self._pvp3_winner = None       # 三人混战系列赛最终胜者（owner）
        self._last_round_winner = None # 刚结束一局的胜者（owner；供局间文案）
        self.round_over_pause = 0.0    # 单局结算后、进下一局前的停留剩余（秒）
        # 档位 C 命中闪光计时器（p1 红 / p2 蓝 / p3 绿 三色各自独立；
        # 2026-10-24 曾删红蓝辉光条、仅留中绿，本次按用户要求恢复红蓝并重做，三色分区等幅）。
        self._ui_flash_p1 = 0.0        # 红方（P1 击杀/自毁）闪光计时器
        self._ui_flash_p2 = 0.0        # 蓝方（P2 击杀/自毁）闪光计时器
        self._ui_flash_p3 = 0.0        # 绿方（P3 击杀/自毁）闪光计时器
        self._pause_after = None       # 暂停结束后的动作：None / 'intro'(开局提示) / 'round'(进下一局) / 'result'(进结算页)
        self._round_overlay_hold = 0.0 # 结算暂停中"覆盖层出现前"的剩余延迟（秒）：先播完爆炸再弹胜利提示
        self._last_round_a_win = None  # 刚结束的该局是否为 side_a 胜（供局间文案；None=未定）
        self._pvp_destroyed = {}       # PVP 本帧被摧毁者 -> 击杀者 owner
        self._dead_players = set()     # PVP 本局内已阵亡玩家（死亡后不参与交互；每局重置）
        self._round_locked = False     # 单局已出结果并锁定：倒计时内战斗不冻结，后续击毁不改胜负
        # 敌方列表（纯 PVP 恒为空；保留字段供验证脚本/历史断言兼容）
        self.enemy_tanks = []

        # 开火冷却（P1/P2/P3 各自独立，互不拦截）
        self.fire_cooldown_remaining = 0.0
        self.fire_cooldown_p2_remaining = 0.0
        self.fire_cooldown_p3_remaining = 0.0
        self.game_over_flag = False

    def _pick_random_player_spawn(self):
        """从当前地图的合法出生区随机选一个（Phase 8.3-F 随机出生）。

        规则：EMPTY ∧ 非 Protected Zone ∧ 周围 ∃ 移动空间（3×3 邻域开放格数达标）
        ∧ **几何矩形精查**（坦克 25×25 矩形不与连续几何重叠）。
        保证玩家出生不会卡死。保留 (3,3) 作为合法候选（若存在）。

        ★ 2026-10-23 加几何精查的原因：格子只按中心点判定，环带/钢球边缘的格子
          「格心是空的、但坦克矩形压上去一半」——实测老规则 421 个候选里
          88 个（21%）会贴着墙出生。Stage 5 起物理走连续几何，出生点也必须
          用同一把尺子量，否则又会「位置不一样」。
        """
        grid = self.game_map.grid
        tank_rect = pygame.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        cands = []
        for r in range(1, GRID_SIZE - 1):
            for c in range(1, GRID_SIZE - 1):
                if grid[r][c] != TileType.EMPTY:
                    continue
                if ljr_zone.is_ljr_protected(r, c):
                    continue
                open_n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                            if grid[nr][nc] == TileType.EMPTY:
                                open_n += 1
                if open_n >= 5:   # 保证出生后有移动空间
                    # 几何精查：与物理碰撞同一把尺子（连续几何关卡生效）
                    tank_rect.center = (c * TILE_SIZE + TILE_SIZE / 2,
                                        r * TILE_SIZE + TILE_SIZE / 2)
                    if rect_hits_obstacle(tank_rect, self.game_map):
                        continue
                    cands.append((r, c))
        if not cands:
            r, c = 3, 3
        else:
            r, c = random.choice(cands)
        return c * TILE_SIZE + TILE_SIZE / 2, r * TILE_SIZE + TILE_SIZE / 2

    def _load_stage(self, stage_config) -> None:
        """初始化「当前关战斗环境」，首关与切关共用（Phase 8.0）。

        只调整当前关内容：地图切换、玩家跨关复位、敌人生成/波次/道具、战斗列表、
        单关分数清零；不触碰总分/击毁（跨关保留）。
        """
        # 1) 地图
        grid, deco = stage_config["map_data"]()
        self.game_map = GameMap.from_map_data(grid, deco)
        # Phase 8.3-F 视觉层：若该 Stage 提供区域配色，将其附加到 GameMap（纯视觉，不改碰撞）
        visual_fn = stage_config.get("visual_fn")
        self.game_map.visual_colors = visual_fn() if visual_fn else None
        # Phase 8.4 装饰覆盖层：警示灯/泄漏/蒸汽/管线（纯观感，不参与碰撞）
        deco_fn = stage_config.get("deco_fn")
        self.game_map.decorations = deco_fn() if deco_fn else None
        # Phase 8.6 平滑形状层：真圆弧沙洲/ 真圆钢球 / LJR 水印（纯观感）。
        # 无 shape_fn 的关卡为None，MapRenderer 会自动跳过形状层，老关卡行为不变。
        shape_fn = stage_config.get("shape_fn")
        self.game_map.shapes = shape_fn() if shape_fn else None
        # Phase 8.6+ 连续几何层（Stage 5 起）：物理碰撞的真口径。
        # 无 geometry_fn 的关卡为 None，core/collision.py 自动回退格子路径。
        geometry_fn = stage_config.get("geometry_fn")
        self.game_map.geometry = geometry_fn() if geometry_fn else None
        self.map_renderer = MapRenderer(self.game_map)

        # 2.5) 关卡专属背景：按 stage_config["bg"] 加载对应图（每关一张，绝不串台）。
        #      图缺失 / LEVEL_BG_ENABLED=False 时自动回退纯色底，不会崩。
        self._load_level_bg_for_stage(stage_config)

        # 3) 玩家出生点（Phase 8.3-F：随机取合法 EMPTY，过滤墙/保护区/障碍）
        spawn_x, spawn_y = self._pick_random_player_spawn()

        # 3) 玩家对象：首关新建；切关复用对象 + 复位位置/弹药/Buff（Game 层完成，
        #    不修改冻结文件 player_tank.py）
        if self.player_tank is None:
            self.player_tank = PlayerTank(spawn_x, spawn_y, self.game_map)
        else:
            self._reset_player_for_stage(spawn_x, spawn_y)

        # 4) 敌方列表（纯 PVP 恒为空；保留字段供验证脚本/历史断言兼容）
        self.enemy_tanks = []

        # 5) 道具系统（切关：指向新地图 + 清除地图道具/生成状态/临时 Buff 由玩家复位覆盖）
        if ITEM_SYSTEM_ENABLED:
            if self.item_spawn_manager is None:
                # T7：增强类 + 全局调优参数（间隔/数量），寿命由子类按 settings 注入
                self.item_spawn_manager = ItemSpawnManagerEx(
                    self.game_map,
                    spawn_interval=ITEM_SPAWN_INTERVAL,
                    max_active=ITEM_MAX_ACTIVE,
                )
            else:
                # 道具属于当前关：切关清除道具 + 生成计时，下一关重新生成
                self.item_spawn_manager.game_map = self.game_map
                self.item_spawn_manager.reset()

        # 6) 战斗列表清空（敌人已清，这里兜底清子弹/激光/导弹/飘字）
        #    在飞的追踪导弹先淡出各自音效再清列表（防换关/重开后残留飞行/锁定音）
        for _m in getattr(self, "missiles", []):
            _m.discard()
        self.bullets = []
        self.lasers = []
        self.missiles = []
        self.floating_scores = []
        # Phase 7.1 爆炸/碎裂特效 + 屏幕震动（表现层）
        self.shake = CameraShake()
        self.explosions = []
        # 屏幕震动用的离屏缓冲：整窗尺寸，游戏世界先画到这里再以偏移贴回 self.screen
        self.world_surface = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))

        # 7) 波次系统已退役（纯 PVP 无波次）；保留小节占位。

    def _reset_player_for_stage(self, spawn_x: float, spawn_y: float,
                                tank=None) -> None:
        """切关时的玩家跨关复位（Game 层完成，不修改冻结文件 player_tank.py）。

        保留 PlayerTank 对象；复位：位置 / 朝向 / 速度 / 弹药 / Buff 状态 / 尾焰。
        默认复位 P1；传入 tank 可复位指定玩家（如 _start_round 重定位 P2）。
        """
        pt = tank if tank is not None else self.player_tank
        pt.game_map = self.game_map
        # 位置
        pt.physics.x = spawn_x
        pt.physics.y = spawn_y
        pt.x = spawn_x
        pt.y = spawn_y
        pt.rect.center = (round(spawn_x), round(spawn_y))
        # 速度 / 朝向
        pt.physics.vx = 0.0
        pt.physics.vy = 0.0
        pt.physics.current_speed = 0.0
        pt.physics.facing_angle = 0
        pt.angle = 0
        # 弹药（每关开始：满弹匣）
        pt.ammo = MAGAZINE_CAPACITY
        pt.reload_remaining = 0
        # Buff 状态（护盾 / 加速 / 霰弹 / 激光充能 / 追踪导弹 清空）
        pt.shield_remaining = 0.0
        pt.speed_remaining = 0.0
        pt.speed_multiplier = 1.0
        pt.shotgun_ammo = 0
        pt.laser_charged = False
        pt.missile_ammo = 0
        pt.physics.max_speed = TANK_SPEED
        # 加速尾焰粒子
        pt.trail_particles = []

    @property
    def score(self) -> int:
        """保留委托：统一读取 ScoreManager，保证单一数据源。"""
        return self.score_manager.current_score

    def start_pvp(self, rounds: int = 5) -> None:
        """PVP 纯 1v1 双人对战启动：无难度、P2 恒在场、按对局数走系列赛。

        地图取自玩家在地图选择页选中的 self.selected_stage（默认 0=第 1 关）。
        """
        self.match_mode = "pvp"
        self.state = GameState.PLAYING
        self.game_over_flag = False
        self.level_manager.start_game_at(self.selected_stage)
        self.score_manager.reset()
        self.round_manager = RoundManager("pvp", rounds=rounds)
        self.player2_tank = Player2Tank(600, 600, self.game_map)
        self._pvp_destroyed = {}
        self._start_round()
        # 首局开战版：3s 展示
        self.round_over_pause = ROUND_INTRO_SECONDS
        self._pause_after = "intro"
        self._round_overlay_hold = 0.0   # 开局提示无"先播爆炸"阶段
        self._last_round_a_win = None

    def start_pvp3(self, rounds: int = 5) -> None:
        """三人混战启动：P1(红, WASD+J) / P2(蓝, 方向键+空格) / P3(绿, 鼠标)。

        规则：一局内三方混战，仅最后存活者胜该局（同帧全毁则本局作废重开）；
        先胜 ⌈N/2⌉ 局者赢系列赛。地图取自 self.selected_stage。
        """
        self.match_mode = "pvp3"
        self.state = GameState.PLAYING
        self.game_over_flag = False
        self.level_manager.start_game_at(self.selected_stage)
        self.score_manager.reset()
        self.round_manager = RoundManager("pvp3", rounds=rounds)
        self._series_wins = {"p1": 0, "p2": 0, "p3": 0}
        self._pvp3_winner = None
        self._last_round_winner = None
        self.player2_tank = Player2Tank(600, 600, self.game_map)
        self.player3_tank = Player3Tank(200, 200, self.game_map)
        self._pvp_destroyed = {}
        self._start_round()
        # 首局开战版：3s 展示
        self.round_over_pause = ROUND_INTRO_SECONDS
        self._pause_after = "intro"
        self._round_overlay_hold = 0.0   # 开局提示无"先播爆炸"阶段
        self._last_round_a_win = None

    def reset(self) -> None:
        """重开：不销毁 Game 对象，重置一局战斗数据并回到 MENU（根页）。"""
        self._new_combat()
        self.selected_stage = 0
        self.state = GameState.MENU
        self.menu.reset_to_main()

    def handle_events(self):
        # ★ 输入法锁定：防止中文输入法在 PLAYING 状态下拦截键盘事件导致崩溃
        # Windows 中文输入法会发送 IME 组合事件，可能引发 pygame 异常
        if self.state == GameState.PLAYING:
            # 尝试切换回英文输入模式（需要管理员权限，失败则静默忽略）
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info()['window']
                thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
                # 获取当前键盘布局句柄并切换到英文
                kbd_layout = ctypes.windll.user32.GetKeyboardLayout(thread_id)
                # 切换到英文布局（保留原布局的高16位，只改低16位为英文）
                new_layout = (kbd_layout & 0xFFFF0000) | 0x00000409
                ctypes.windll.user32.ActivateKeyboardLayout(hwnd, new_layout)
            except Exception:
                pass  # 权限不足或 API 不可用，静默忽略

        for event in pygame.event.get():
            # ★ 过滤 IME 相关事件，防止中文输入法触发崩溃
            # TEXTINPUT: 输入法提交的字符（如拼音输入时的候选字）
            # TEXTEDITING: 输入法组合中的文本（如拼音输入过程中的中间状态）
            if event.type in (pygame.TEXTINPUT, pygame.TEXTEDITING):
                continue  # 忽略输入法组合事件，不传递给游戏逻辑
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEMOTION:
                # 菜单内悬停高亮
                if self.state == GameState.MENU:
                    self.menu.handle_mouse(event.pos)
                elif self.state == GameState.PAUSED:
                    self._pause_handle_mouse(event.pos)
                # 结果页：返回按钮悬停态（移入边沿播悬停音，离开不播）
                elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                    new_hover = self._result_menu_button_rect().collidepoint(event.pos)
                    if new_hover and not self._result_hover:
                        self.audio.play(SFX_NAME_HOVER,
                                        volume_scale=SFX_BUTTON_HOVER_VOLUME)
                    self._result_hover = new_hover
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 三人混战：P3 鼠标左键点击一次发射一枚子弹
                # （开局提示冻结期内不响应，避免子弹悬停等解冻）
                if (self.state == GameState.PLAYING
                        and self.match_mode == "pvp3"
                        and event.button == 1
                        and self._pause_after != "intro"):
                    self._try_fire_p3()
                if event.button != 1:
                    continue
                if self.state == GameState.MENU:
                    self.menu.handle_click(event.pos)
                elif self.state == GameState.PAUSED:
                    if self._pause_handle_click(event.pos):
                        self.audio.play(SFX_NAME_CLICK)   # 暂停按钮点击反馈
                elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                    if self._result_menu_button_rect().collidepoint(event.pos):
                        self.audio.play(SFX_NAME_CLICK)   # 返回按钮点击反馈
                        self.reset()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if self.state == GameState.MENU:
                    # 菜单内：↑↓移动焦点，Enter/Space 确认，ESC/Backspace 返回上一页
                    self.menu.handle_key(key)
                elif self.state == GameState.PLAYING:
                    # ESC：调出/收起暂停菜单（局间提示期按 PAUSE_ALLOWED_DURING_INTRO 门槛）
                    if key == pygame.K_ESCAPE and (self.round_over_pause <= 0
                                                   or PAUSE_ALLOWED_DURING_INTRO):
                        self._pause_open()
                    if key == pygame.K_j:
                        self._try_fire()
                    if key == pygame.K_SPACE:
                        self._try_fire_p2()
                elif self.state == GameState.PAUSED:
                    self._pause_handle_key(key)
                elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                    if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        self.audio.play(SFX_NAME_CLICK)   # 键盘返回同样给点击反馈
                        self.reset()

    def _try_fire(self) -> None:
        """P1 开火入口（PLAYING 帧内由 J 键触发；阵亡则忽略）。"""
        if self.player_tank is not None and self.player_tank not in self._dead_players:
            self._try_fire_for(self.player_tank, "p1")

    def _try_fire_p2(self) -> None:
        """P2 开火入口（PLAYING 帧内由空格键触发；P2 不在场/阵亡则忽略）。"""
        if (self.player2_tank is not None
                and self.player2_tank not in self._dead_players):
            self._try_fire_for(self.player2_tank, "p2")

    def _try_fire_p3(self) -> None:
        """P3 开火入口（三人混战帧内由鼠标左键触发；P3 不在场/阵亡则忽略）。"""
        if (self.player3_tank is not None
                and self.player3_tank not in self._dead_players):
            self._try_fire_for(self.player3_tank, "p3")

    def _try_fire_for(self, tank, owner: str) -> None:
        """按 tank 与 owner 开火：普通弹 owner 传入；霰弹弹丸实例补 owner。

        开火冷却按玩家各自独立（P1/P2 各打各的，互不拦截）。
        """
        if self._tank_cooldown(owner) > 0:
            return
        muzzle_x, muzzle_y = tank.get_muzzle_position()
        dx0, dy0 = tank.get_direction_vector()

        # 激光充能（一次性）：优先于普通弹与霰弹发射，不消耗弹药
        if ITEM_SYSTEM_ENABLED and getattr(tank, "laser_charged", False):
            self._fire_laser_for(tank, owner)
            return

        # 追踪导弹（独立计数）：不依赖普通弹药/重装，只依剩余发数
        if ITEM_SYSTEM_ENABLED and getattr(tank, "missile_active", False):
            self._fire_missile_for(tank, owner)
            return

        # 霰弹模式（独立弹夹）：不依赖普通弹药/重装，只依自己剩余次数
        if ITEM_SYSTEM_ENABLED and tank.shotgun_active:
            self._fire_shotgun_for(tank, owner)
            return

        # 普通开火
        if not tank.can_fire():
            return
        bullet = Bullet(muzzle_x, muzzle_y, dx0, dy0, self.game_map, owner=owner)
        bullet.emitter = tank          # 子弹归属实体
        self.bullets.append(bullet)
        self._set_tank_cooldown(owner, BULLET_FIRE_COOLDOWN)
        tank.consume_ammo()
        # 玩家开炮音效（受主控音量 / 静音体系约束，额外调小音量）
        self.audio.play(SFX_CANNON_FIRE, volume_scale=SFX_CANNON_FIRE_VOLUME)

    def _fire_shotgun_for(self, tank, owner: str) -> None:
        """霰弹开火：生成 16 颗弹丸并对实例补 owner（ShotgunPellet 构造不支持 owner 参数）。"""
        import math as _m
        muzzle_x, muzzle_y = tank.get_muzzle_position()
        dx0, dy0 = tank.get_direction_vector()
        base_angle = _m.atan2(dx0, -dy0)   # 还原朝向：dx=sin a, dy=-cos a -> a=atan2(dx, -dy)
        for _ in range(SHOTGUN_PELLETS):
            spread = random.uniform(-SHOTGUN_SPREAD_RADIANS, SHOTGUN_SPREAD_RADIANS)
            angle = base_angle + spread
            dx = _m.sin(angle)
            dy = -_m.cos(angle)
            pellet = ShotgunPellet(muzzle_x, muzzle_y, dx, dy, self.game_map)
            pellet.owner = owner          # 覆盖默认 "player"，供 PVP 命中判定
            pellet.emitter = tank         # 子弹归属实体
            self.bullets.append(pellet)
        tank.consume_shotgun_ammo()
        self._set_tank_cooldown(owner, BULLET_FIRE_COOLDOWN)
        # 霰弹同样属于玩家开炮，播放开炮音效（同样调小音量）
        self.audio.play(SFX_CANNON_FIRE, volume_scale=SFX_CANNON_FIRE_VOLUME)

    def _laser_targets(self):
        """激光可命中的目标：各方在场（未阵亡）玩家坦克（含自己，激光经反射
        也可打到自己，与子弹自伤规则一致；起点在炮管外，天然不会瞬发自中）。"""
        targets = []
        for tank in (self.player_tank, self.player2_tank, self.player3_tank):
            if tank is not None and tank not in self._dead_players:
                targets.append(tank)
        return targets

    def _missile_targets(self):
        """追踪导弹可锁定/可命中的目标：各方在场（未阵亡）玩家坦克，
        附带各自车身颜色（用于弹体/尾焰/烟迹染色：P1 红 / P2 蓝 / P3 绿）。"""
        targets = []
        for tank, color in ((self.player_tank, COLOR_PLAYER_TANK),
                            (self.player2_tank, COLOR_P2_TANK),
                            (self.player3_tank, COLOR_P3_TANK)):
            if tank is not None and tank not in self._dead_players:
                targets.append((tank, color))
        return targets

    def _fire_missile_for(self, tank, owner: str) -> None:
        """追踪导弹开火：从炮口 generate 一枚追踪导弹；发射音效由导弹自身管理
        （出膛飞行音 → 锁定音 → 即将命中音 → 死亡统一淡出）。"""
        muzzle_x, muzzle_y = tank.get_muzzle_position()
        dx0, dy0 = tank.get_direction_vector()
        missile = Missile(muzzle_x, muzzle_y, dx0, dy0, self.game_map,
                          owner=owner, audio=self.audio)
        missile.emitter = tank            # 导弹归属实体（自伤识别用）
        self.missiles.append(missile)
        tank.consume_missile_ammo()
        self._set_tank_cooldown(owner, BULLET_FIRE_COOLDOWN)

    def _settle_missile_hit(self, missile) -> None:
        """追踪导弹命中结算：与激光一致——护盾拦截则只播爆炸特效+音效零伤害；
        命中发射者自己按自毁结算；命中对方走 PVP 击杀计分。"""
        hit_tank = missile.hit_tank
        if hit_tank is None:
            return
        # 命中爆炸音效（护盾拦截也炸在护盾上）
        self.audio.play(SFX_MISSILE_EXPLODE,
                        volume_scale=SFX_MISSILE_EXPLODE_VOLUME)
        if ITEM_SYSTEM_ENABLED and hit_tank.handle_enemy_hit():
            # 护盾拦截：导弹炸开、零伤害（护盾时间不消耗）
            self.explosions.append(Explosion(missile.rect.center,
                                             time_scale=0.25))
            return
        if hit_tank is missile.emitter:
            # 误伤自己：与自弹自毁同规则（爆炸 + 震屏 + 隐藏坦克，不计击杀分）
            self.audio.play(SFX_PLAYER_DESTROYED,
                            volume_scale=SFX_PLAYER_DESTROYED_VOLUME)
            self._pvp_destroyed[hit_tank] = missile.owner
            self.explosions.append(Explosion(hit_tank.rect.center,
                                             time_scale=0.25))
            self.shake.add_trauma(Explosion.TRAUMA)
            self._dead_players.add(hit_tank)
            hit_tank.reload_remaining = 0.0   # 死亡即停换弹：防辉光/读条残留
        else:
            self._handle_player_bullet_hit_pvp(missile.owner, hit_tank)

    def _fire_laser_for(self, tank, owner: str) -> None:
        """激光充能开火：预计算最多 10 次反射的折线，激光沿折线高速推进；
        命中坦克（含反射后命中自己）或反射满即消失。开火后充能清空。"""
        muzzle_x, muzzle_y = tank.get_muzzle_position()
        dx0, dy0 = tank.get_direction_vector()
        vertices, _hit = trace_laser_path(
            muzzle_x, muzzle_y, dx0, dy0, self.game_map,
            targets=self._laser_targets(),
            max_bounces=LASER_MAX_BOUNCES,
        )
        laser = Laser(vertices, owner=owner)
        laser.emitter = tank                 # 激光归属实体（自伤识别用）
        laser.set_targets(self._laser_targets())
        self.lasers.append(laser)
        tank.laser_charged = False
        self._set_tank_cooldown(owner, BULLET_FIRE_COOLDOWN)
        # 激光发射音效（用户提供的“激光道具音效.wav”，对标开炮音效音量/播放方式）
        self.audio.play(SFX_LASER_FIRE, volume_scale=SFX_LASER_FIRE_VOLUME)

    def _tank_cooldown(self, owner: str) -> float:
        """按 owner 取开火冷却剩余（P1/P2/P3 各自独立）。"""
        if owner == "p2":
            return self.fire_cooldown_p2_remaining
        if owner == "p3":
            return self.fire_cooldown_p3_remaining
        return self.fire_cooldown_remaining

    def _set_tank_cooldown(self, owner: str, value: float) -> None:
        """按 owner 设开火冷却剩余。"""
        if owner == "p2":
            self.fire_cooldown_p2_remaining = value
        elif owner == "p3":
            self.fire_cooldown_p3_remaining = value
        else:
            self.fire_cooldown_remaining = value

    def _update_fx(self, dt: float) -> None:
        """推进世界空间纯特效：飘字 / 爆炸 / 震屏（纯表现，不碰战斗逻辑）。

        局间/开局暂停时也调用，保证被毁坦克的爆炸能在"胜利提示出现前"完整播完。
        """
        for fs in self.floating_scores:
            fs.update(dt)
        self.floating_scores = [fs for fs in self.floating_scores if fs.alive]
        for e in self.explosions:
            e.update(dt)
        self.explosions = [e for e in self.explosions if e.alive]
        self.shake.update(dt)

    def _tank_by_owner(self, owner: str):
        """owner -> 玩家坦克对象（不在场返回 None）。"""
        if owner == "p1":
            return self.player_tank
        if owner == "p2":
            return self.player2_tank
        if owner == "p3":
            return self.player3_tank
        return None

    def _owner_of_tank(self, tank):
        """坦克对象 -> owner 字符串（p1/p2/p3），非 PVP 坦克返回 None。"""
        if tank is self.player_tank:
            return "p1"
        if tank is self.player2_tank:
            return "p2"
        if tank is self.player3_tank:
            return "p3"
        return None

    def _opponents_of(self, owner: str):
        """某发射者的对手列表 [(owner, tank), ...]（不含自己；1v1 时恰为一项）。"""
        result = []
        for o in ("p1", "p2", "p3"):
            if o == owner:
                continue
            tank = self._tank_by_owner(o)
            if tank is not None:
                result.append((o, tank))
        return result

    def _solid_tanks_excluding(self, tank):
        """返回除 tank 本身之外、当前在场（未阵亡）的"实体坦克"列表，
        供 handle_input 的 others 参数使用，实现坦克互撞。
        包含 P1 / P2 / P3 / 敌方坦克（当前敌方列表恒为空，提前铺好兼容）。"""
        others = []
        candidates = []
        if self.player_tank is not None:
            candidates.append(self.player_tank)
        if self.player2_tank is not None:
            candidates.append(self.player2_tank)
        if self.player3_tank is not None:
            candidates.append(self.player3_tank)
        candidates.extend(self.enemy_tanks)
        for c in candidates:
            if c is tank:
                continue
            if c in self._dead_players:
                continue
            others.append(c)
        return others

    def update(self):
        # Phase 6.0：仅 PLAYING 状态执行战斗逻辑。
        # GAME_OVER / VICTORY（及未来的 PAUSED/MENU）一律停止战斗更新，
        # 不改变玩家/敌人/子弹/道具/碰撞等的任何内部实现。
        if self.state != GameState.PLAYING:
            return
        dt = self.clock.get_time() / 1000.0
        # 档位 C：命中闪光计时器衰减（三色各自独立衰减）。
        if UI_AREA_DYNAMIC:
            if self._ui_flash_p1 > 0:
                self._ui_flash_p1 = max(0.0, self._ui_flash_p1 - dt)
            if self._ui_flash_p2 > 0:
                self._ui_flash_p2 = max(0.0, self._ui_flash_p2 - dt)
            if self._ui_flash_p3 > 0:
                self._ui_flash_p3 = max(0.0, self._ui_flash_p3 - dt)
        self._pvp_destroyed = {}          # PVP 本帧被摧毁集合清零

        # 局间/开局提示倒计时推进：
        #   'intro'（开局提示）→ 冻结战斗，仅倒计时 + 特效（"准备开战"）；
        #   单局已结算（_round_locked）→ 非冻结倒计时：战斗照常运行（子弹飞、坦克动、
        #      爆炸播），仅叠一个不阻挡操作的胜利横幅；倒计时归零再进下一局 / 结算页。
        #   这样"击毁对方即判胜"后游戏不暂停，赢家随后即便被流弹击中自毁也不改胜负。
        if self.round_over_pause > 0:
            if self._round_overlay_hold > 0:
                self._round_overlay_hold -= dt
            if self._pause_after == "intro":
                # 开局提示：冻结战斗，仅推进特效与倒计时
                self.round_over_pause -= dt
                self._update_fx(dt)
                if self.round_over_pause <= 0:
                    self._pause_after = None
                return
            # 单局已结算：非冻结倒计时，战斗照常；倒计时归零再推进
            self.round_over_pause -= dt
            if self.round_over_pause <= 0:
                action = self._pause_after
                self._pause_after = None
                self._round_locked = False
                if action == "round":
                    self._start_round()
                elif action == "result":
                    if self.match_mode == "pvp3":
                        # 三人混战：按系列胜者定结果状态（P1 胜=胜利页，否则失败页）
                        self._pvp3_winner = self._last_round_winner
                        if self._last_round_winner == "p1":
                            self.set_victory()
                        else:
                            self.set_game_over()
                    elif self.round_manager.a_win:
                        self.set_victory()
                    else:
                        self.set_game_over()
                return
            # 倒计时未到：继续向下执行正常战斗（不 return），实现"击毁后不暂停"

        # 玩家移动 & 弹药（P1/P2 均在阵；阵亡玩家不操作）
        keys = pygame.key.get_pressed()
        if self.player_tank not in self._dead_players:
            self.player_tank.handle_input(keys, dt, self._solid_tanks_excluding(self.player_tank))
            self.player_tank.update_ammo(dt)
        if (self.player2_tank is not None
                and self.player2_tank not in self._dead_players):
            self.player2_tank.handle_input(keys, dt, self._solid_tanks_excluding(self.player2_tank))
            self.player2_tank.update_ammo(dt)
        # P3（三人混战）：鼠标控制——中心每帧移向鼠标、炮管朝向鼠标
        if (self.player3_tank is not None
                and self.player3_tank not in self._dead_players):
            mouse_pos = pygame.mouse.get_pos()
            self.player3_tank.handle_mouse_input(
                mouse_pos, dt, self._solid_tanks_excluding(self.player3_tank))
            self.player3_tank.update_ammo(dt)

        # 开火冷却（P1/P2/P3 各自独立递减）
        if self.fire_cooldown_remaining > 0:
            self.fire_cooldown_remaining -= dt
        if self.fire_cooldown_p2_remaining > 0:
            self.fire_cooldown_p2_remaining -= dt
        if self.fire_cooldown_p3_remaining > 0:
            self.fire_cooldown_p3_remaining -= dt

        # 子弹更新
        for bullet in self.bullets:
            bullet.update(dt)

        # 激光更新 + 命中结算（Laser 在 update 内按子步进判定，命中即置 hit_tank）
        for laser in self.lasers:
            laser.update(dt)
            if not laser.alive and laser.hit_tank is not None:
                self._settle_laser_hit(laser)

        # 追踪导弹更新 + 命中结算（Missile 自行管理追踪/转向/反弹/烟迹/音效）
        for missile in self.missiles:
            missile.update(dt, self._missile_targets())
        for missile in self.missiles:
            if not missile.alive and missile.hit_tank is not None:
                self._settle_missile_hit(missile)

        # --- 碰撞检测 ---
        # 1b) 玩家子弹 vs 玩家（PVP 互射计分；三人混战同理；护盾豁免前置）
        for bullet in self.bullets:
            if not bullet.alive or bullet.owner not in ("p1", "p2", "p3"):
                continue
            # 命中任一其他在场玩家即结算（一发只认一个目标，与 1v1 行为一致）
            for _opp_owner, _opp in self._opponents_of(bullet.owner):
                if (_opp is not None
                        and _opp not in self._dead_players
                        and bullet.rect.colliderect(_opp.rect)):
                    bullet.alive = False
                    self._handle_player_bullet_hit_pvp(bullet.owner, _opp)
                    break

        # 1c) 玩家自弹 vs 自己（SELF_HIT_ENABLED 总开关）：
        #     反弹过（bounce_count>=1）的子弹飞回命中自己 → 按被摧毁结算。
        #     开火瞬间 bounce=0 不判定（斜向贴脸时 muzzle 可能落在自身 rect 内），
        #     只有反弹后的子弹才可能伤到自己；owner 白名单仅 p1/p2/p3（实战无 "player" 实弹）。
        if SELF_HIT_ENABLED:
            for bullet in self.bullets:
                if not bullet.alive or bullet.bounce_count < 1:
                    continue
                if bullet.owner == "p1":
                    self_tank = self.player_tank
                elif bullet.owner == "p2":
                    self_tank = self.player2_tank
                elif bullet.owner == "p3":
                    self_tank = self.player3_tank
                else:
                    continue                       # 敌弹 / "player"：非自弹，跳过
                if (self_tank is None
                        or self_tank in self._dead_players
                        or not bullet.rect.colliderect(self_tank.rect)):
                    continue
                bullet.alive = False
                # 护盾免疫（对自弹同样生效，不消耗护盾时间）
                if ITEM_SYSTEM_ENABLED and self_tank.handle_enemy_hit():
                    continue
                # 记录自毁（不计击杀分/不弹飘字），由 _settle_pvp 依被毁者
                # 判对方胜局；同帧双毁仍走互毁作废。
                self.audio.play(SFX_PLAYER_DESTROYED,
                                volume_scale=SFX_PLAYER_DESTROYED_VOLUME)
                self._pvp_destroyed[self_tank] = bullet.owner
                # 自弹自毁：与子弹击杀一致，生成爆炸 + 震屏 + 隐藏坦克
                # 玩家被毁爆炸慢放（time_scale=0.25），更有打击感
                self.explosions.append(Explosion(self_tank.rect.center, time_scale=0.25))
                self.shake.add_trauma(Explosion.TRAUMA)
                self._dead_players.add(self_tank)
                self_tank.reload_remaining = 0.0  # 死亡即停换弹：防辉光/读条残留

        # PVP 本帧结算（收集后原子处理）
        self._settle_pvp()

        # 清理失效子弹 / 激光 / 导弹
        self.bullets = [b for b in self.bullets if b.alive]
        self.lasers = [l for l in self.lasers if l.alive]
        self.missiles = [m for m in self.missiles if m.alive]

        # Phase 7.1 世界空间纯特效：飘字 / 爆炸 / 震屏（暂停期外正常推进）
        self._update_fx(dt)

        # 道具系统（Phase 5.4.3 / T7）：PVP 全流程启用。
        # 刷新避让：P1 由 player_rect 传入，P2 并入 enemy_rects。
        # 拾取：P1 先判、P2 后判 = 竞争拾取（同帧命中概率极低，先判定 P1 先得）。
        if ITEM_SYSTEM_ENABLED:
            enemy_rects = [enemy.rect for enemy in self.enemy_tanks]
            if self.player2_tank is not None:
                enemy_rects = enemy_rects + [self.player2_tank.rect]
            if self.player3_tank is not None:
                enemy_rects = enemy_rects + [self.player3_tank.rect]
            self.item_spawn_manager.update(
                dt, self.player_tank.rect, enemy_rects)
            # 拾取与效果计时：阵亡玩家跳过（不能捡、不生效）
            if self.player_tank not in self._dead_players:
                collected = self.item_spawn_manager.try_pickup(self.player_tank)
                if collected:
                    self.audio.play(SFX_ITEM_PICKUP, volume_scale=SFX_ITEM_PICKUP_VOLUME)
            if (self.player2_tank is not None
                    and self.player2_tank not in self._dead_players):
                collected2 = self.item_spawn_manager.try_pickup(self.player2_tank)
                if collected2:
                    self.audio.play(SFX_ITEM_PICKUP, volume_scale=SFX_ITEM_PICKUP_VOLUME)
            if (self.player3_tank is not None
                    and self.player3_tank not in self._dead_players):
                collected3 = self.item_spawn_manager.try_pickup(self.player3_tank)
                if collected3:
                    self.audio.play(SFX_ITEM_PICKUP, volume_scale=SFX_ITEM_PICKUP_VOLUME)
            if self.player_tank not in self._dead_players:
                self.player_tank.update_effects(dt)
            if (self.player2_tank is not None
                    and self.player2_tank not in self._dead_players):
                self.player2_tank.update_effects(dt)
            if (self.player3_tank is not None
                    and self.player3_tank not in self._dead_players):
                self.player3_tank.update_effects(dt)

    # ------------------------------------------------------------------
    # Phase 6.1 统一结果入口
    # 状态切换只允许由 main.Game 通过 set_game_over()/set_victory() 发生；
    # 任何 entity / manager 一律调用 game.set_xxx()，禁止直接写 self.state，
    # 也禁止 player/enemy 控制游戏生命周期。二者幂等且互不覆盖。
    # ------------------------------------------------------------------
    def set_game_over(self) -> None:
        """统一进入 GAME_OVER 的唯一入口（幂等：结果状态间不互相覆盖）。"""
        if self.state in (GameState.GAME_OVER, GameState.VICTORY):
            return
        self.state = GameState.GAME_OVER
        self.game_over_flag = True
        self._result_hover = False     # 复位结果页按钮悬停态（防跨局残留高亮）
        self._silence_missiles()

    def set_victory(self) -> None:
        """统一进入 VICTORY 的唯一入口（幂等：结果状态间不互相覆盖）。"""
        if self.state in (GameState.GAME_OVER, GameState.VICTORY):
            return
        self.state = GameState.VICTORY
        self.game_over_flag = True
        self._result_hover = False     # 复位结果页按钮悬停态（与 set_game_over 一致）
        self._silence_missiles()

    def _silence_missiles(self) -> None:
        """离开战斗（GAME_OVER/VICTORY）时淡出所有在飞导弹的音效。

        主循环只在 PLAYING 态调 update()，结果画面下导弹被"冻住"不再致死，
        但音效是独立播放的，不主动淡出会一路播到自然结束（飞行音最长 12s+），
        造成"导弹都消失了音效还没结束"。这里统一 0.4s 淡出，只静音、
        保留冰冻中的视觉残影，与冻住子弹的行为一致。"""
        for missile in self.missiles:
            missile._fade_all_sounds()

    def _game_over(self) -> None:
        """游戏结束：转交 set_game_over() 切换状态（战斗随之冻结）。
        结果画面改由 render() 的状态叠加层绘制，保持结果状态而非立即退出。"""
        self.set_game_over()

    def _handle_player_bullet_hit_pvp(self, shooter_owner: str, hit_tank) -> None:
        """PVP 玩家子弹命中对方玩家：护盾免疫前置，否则记录到 _pvp_destroyed。"""
        if ITEM_SYSTEM_ENABLED and hit_tank.handle_enemy_hit():
            return
        self.audio.play(SFX_PLAYER_DESTROYED, volume_scale=SFX_PLAYER_DESTROYED_VOLUME)
        self._pvp_destroyed[hit_tank] = shooter_owner
        self.score_manager.add_score(PLAYER_KILL_SCORE)
        self.score_manager.add_kill()
        self.floating_scores.append(FloatingScore(PLAYER_KILL_SCORE, hit_tank.rect.center))
        # Phase 7.1 PVP 击杀：生成爆炸 + 屏幕震动（玩家被毁爆炸慢放 0.25）
        self.explosions.append(Explosion(hit_tank.rect.center, time_scale=0.25))
        self.shake.add_trauma(Explosion.TRAUMA)
        # 被毁坦克隐藏（不渲染/不交互/不挡路）；爆炸已在移出前于原位生成
        self._dead_players.add(hit_tank)
        hit_tank.reload_remaining = 0.0       # 死亡即停换弹：防辉光/读条残留

    def _settle_laser_hit(self, laser) -> None:
        """激光命中结算：与现有子弹完全一致——对方持护盾则免疫，
        否则一发摧毁；激光经反射命中发射者自己则按自毁结算（不计击杀分）。"""
        hit_tank = laser.hit_tank
        if hit_tank is None:
            return
        if ITEM_SYSTEM_ENABLED and hit_tank.handle_enemy_hit():
            return
        if hit_tank is laser.emitter:
            # 反射后命中自己：与自弹自毁同规则（爆炸 + 震屏 + 隐藏坦克）
            self.audio.play(SFX_PLAYER_DESTROYED,
                            volume_scale=SFX_PLAYER_DESTROYED_VOLUME)
            self._pvp_destroyed[hit_tank] = laser.owner
            self.explosions.append(Explosion(hit_tank.rect.center, time_scale=0.25))
            self.shake.add_trauma(Explosion.TRAUMA)
            self._dead_players.add(hit_tank)
            hit_tank.reload_remaining = 0.0   # 死亡即停换弹：防辉光/读条残留
        else:
            self._handle_player_bullet_hit_pvp(laser.owner, hit_tank)

    def _flash_side(self, owner: str) -> None:
        """状态栏命中闪光：点亮击杀者/被害者那一侧（档位 C，选 2 规格）。

        三色分区独立闪光：p1=红(左) / p2=蓝(右) / p3=绿(中)，等幅、等布局。
        红/蓝辉光条于 2026-10-24 被删、本次恢复重做，故 p1/p2 现与 p3 同等生效。

        调用方：
          - _settle_pvp 顶部"每击杀闪"循环：正常击杀闪击杀者、自毁/无击杀者闪
            被害者自己（选 2 规格）——三色均按各自 owner 闪。
          - _settle_pvp3_round：3P 最后存活者闪自己那侧（本回合定论提示）。
        衰减 UI_AREA_FLASH_DURATION，卡在 1.5s 慢动作爆炸窗口内可见。
        owner: "p1"(红) / "p2"(蓝) / "p3"(绿,中)。
        """
        if not UI_AREA_DYNAMIC:
            return
        if owner == "p1":
            self._ui_flash_p1 = UI_AREA_FLASH_DURATION
        elif owner == "p2":
            self._ui_flash_p2 = UI_AREA_FLASH_DURATION
        elif owner == "p3":
            self._ui_flash_p3 = UI_AREA_FLASH_DURATION

    def _settle_pvp3_round(self) -> None:
        """三人混战单局结算：仅最后存活者胜；同帧三人全毁则本局作废重开。

        一局内死亡陆续发生：按"累计阵亡"判断——在场存活者 >=2 时本局继续；
        只剩 1 人时该人胜；同帧三人全毁（互毁）才作废重开。
        胜局记入 _series_wins / RoundManager(side_c)，达胜点则系列结束。
        """
        destroyed_now = set(self._pvp_destroyed.keys())
        self._pvp_destroyed.clear()
        if len(destroyed_now) >= 3:
            # 三人同帧互毁：作废，先播完爆炸再重开本局（与 1v1 互毁同规则）
            self.round_over_pause = PVP_EXPLOSION_HOLD_SECONDS
            self._round_overlay_hold = PVP_EXPLOSION_HOLD_SECONDS
            self._pause_after = "round"
            self._round_locked = True
            return
        owners = ("p1", "p2", "p3")
        dead = set()
        for o in owners:
            t = self._tank_by_owner(o)
            if t is not None and t in self._dead_players:
                dead.add(o)
        dead |= destroyed_now
        alive = [o for o in owners
                 if self._tank_by_owner(o) is not None and o not in dead]
        if len(alive) >= 2:
            return                      # 还有人活着，本局继续
        if not alive:
            # 兜底：不该到达（存活 1 人时上一帧已结算）；按互毁作废处理
            self.round_over_pause = PVP_EXPLOSION_HOLD_SECONDS
            self._round_overlay_hold = PVP_EXPLOSION_HOLD_SECONDS
            self._pause_after = "round"
            self._round_locked = True
            return
        winner = alive[0]
        # 档位 C：命中闪光电亮【赢家】那侧（3P 同规则：最后存活者闪自己那侧）。
        # 三色均生效：winner 为 p1/p2/p3 时分别闪红/蓝/绿。
        self._flash_side(winner)
        self._series_wins[winner] = self._series_wins.get(winner, 0) + 1
        self._last_round_winner = winner
        self.round_manager.record_win(
            {"p1": "a", "p2": "b", "p3": "c"}[winner])
        self._round_locked = True
        self._after_round_settled(is_loss=(winner != "p1"))

    def _settle_pvp(self) -> None:
        """PVP 结算：若双方同帧被摧毁则作废重开；否则记录胜局并锁定本局。

        锁定（_round_locked）后，倒计时内战斗不冻结（子弹/坦克/爆炸照常），
        但任何后续击毁（含赢家被流弹击中自毁）一律忽略、不再改变已定胜负；
        赢家被击中仍会正常播放爆炸并隐藏（不"无敌"），只是不影响结果。
        """
        # 档位 C（选 2 规格）：【每次击杀】都按击杀者立刻闪一下，不等本回合结束。
        # 规则：正常击杀 → 闪击杀者；自毁/无击杀者（killer 缺失、==被害者自身、
        # 或非 p1p2p3）→ 闪被害者自己。放在最前（锁检查之前）保证所有击杀都触发，
        # 即便本局已锁定、被流弹击中也照样亮（只闪，不改胜负）。
        # 三色均生效：_flash_side 按 owner 闪红/蓝/绿；涉及 p1/p2/p3 的击杀都闪对应侧。
        if UI_AREA_DYNAMIC and self._pvp_destroyed:
            for victim, killer in self._pvp_destroyed.items():
                v_owner = self._owner_of_tank(victim)
                if killer not in ("p1", "p2", "p3") or killer == v_owner:
                    owner = v_owner          # 自毁 / 无击杀者 → 被害者自己那侧
                else:
                    owner = killer           # 正常击杀 → 击杀者那侧
                if owner is not None:
                    self._flash_side(owner)
        if not self._pvp_destroyed:
            return
        if self._round_locked:
            # 本局已锁定：后续击毁不再改变胜负（视觉摧毁已在碰撞阶段完成）
            self._pvp_destroyed.clear()
            return
        if self.match_mode == "pvp3":
            self._settle_pvp3_round()
            return
        if len(self._pvp_destroyed) >= 2:
            # 互毁作废：先播完双方爆炸（无提示文字），再重开本局。
            # 闪光已由顶部每击杀循环覆盖（互毁双方都闪），此处不重复闪。
            self._pvp_destroyed.clear()
            self.round_over_pause = PVP_EXPLOSION_HOLD_SECONDS
            self._round_overlay_hold = PVP_EXPLOSION_HOLD_SECONDS
            self._pause_after = "round"
            self._round_locked = True
            return
        tank = next(iter(self._pvp_destroyed))
        # 闪光已由顶部每击杀循环按击杀者触发（正常击杀=赢家侧；自毁=被害者自己那侧），
        # 此处只算胜负，不再闪。
        self._pvp_destroyed.clear()
        a_win = (tank is self.player2_tank)
        self.round_manager.record_round(side_a_win=a_win)
        self._last_round_a_win = a_win
        self._round_locked = True
        self._after_round_settled(is_loss=not a_win)

    def _pick_distinct_player_spawn(self, taken, min_dist_tiles: float = 3.0):
        """随机取一个与 taken 中各点至少 min_dist_tiles 格远的合法出生点。

        多人混战出生点互异用：避免 P1/P2/P3 出生重叠/贴脸。尽力而为，
        尝试次数用完后退回最后一次候选（保证一定返回合法点）。
        """
        best = None
        for _ in range(40):
            sx, sy = self._pick_random_player_spawn()
            if best is None:
                best = (sx, sy)
            ok = True
            for (tx, ty) in taken:
                if math.hypot(sx - tx, sy - ty) < min_dist_tiles * TILE_SIZE:
                    ok = False
                    break
            if ok:
                return sx, sy
        return best

    def _start_round(self) -> None:
        """开始新一局：重载当前关战场（地图/玩家复位）并复位局标记。"""
        self.round_manager.reset_for_round()
        # 死亡状态清零（本局全员复活）
        self._dead_players = set()
        # 解除上一局的结果锁定（新局重新进入可结算状态）
        self._round_locked = False
        self._load_stage(self.level_manager.current_stage)
        # P2 重定位到合法出生点（避免与 P1 出生点重叠）
        if self.player2_tank is not None:
            sx, sy = self._pick_distinct_player_spawn(
                [(self.player_tank.x, self.player_tank.y)])
            self._reset_player_for_stage(sx, sy, self.player2_tank)
        # P3 重定位（三人混战）：与 P1/P2 均保持距离
        if self.player3_tank is not None:
            taken = [(self.player_tank.x, self.player_tank.y)]
            if self.player2_tank is not None:
                taken.append((self.player2_tank.x, self.player2_tank.y))
            sx, sy = self._pick_distinct_player_spawn(taken)
            self._reset_player_for_stage(sx, sy, self.player3_tank)

    def _after_round_settled(self, is_loss: bool = False) -> None:
        """单局结算后：系列结束则进结算页；否则进入下一局。

        set_victory = side_a 系列胜（PVP P1 胜）；set_game_over = side_b 系列胜。
        系列未结束时按胜负区分停留时长：判负更久（看清失败反馈）。
        """
        if self.round_manager.match_over:
            # 最终局：同样先播完爆炸（hold），再进结算页（结果状态仍由 set_victory/set_game_over 进入）
            self.round_over_pause = PVP_EXPLOSION_HOLD_SECONDS
            self._round_overlay_hold = PVP_EXPLOSION_HOLD_SECONDS
            self._pause_after = "result"
            return
        # 系列未结束：先播爆炸（hold 期间隐藏提示），再弹胜利提示，停留后进入下一局
        self.round_over_pause = (ROUND_LOSS_PAUSE_SECONDS if is_loss
                                 else ROUND_PAUSE_SECONDS)
        self._round_overlay_hold = PVP_EXPLOSION_HOLD_SECONDS
        self._pause_after = "round"

    def _intermission_data(self) -> dict:
        """局间/开局信息面板数据（纯数据，供 render 绘制；不新增 GameState）。

        返回：局次/总数/系列格式/双方标签与胜局/本局结果/剩余与总暂停秒。
        三人混战（pvp3）：标签三方、比分行三列、结果文案按本局胜者。
        """
        rm = self.round_manager
        fmt = {3: "三局两胜", 4: "四局三胜", 5: "五局四胜"}.get(
            rm.win_needed, f"先胜{rm.win_needed}局")
        is_intro = (self._pause_after == "intro")
        if is_intro:
            result = "intro"
            total = ROUND_INTRO_SECONDS
        else:
            # 局间提示：总时长扣除"先播爆炸"的 hold 段，覆盖层从爆炸播完后开始倒数
            result = "win" if self._last_round_a_win else "loss"
            total = max(0.0, (ROUND_PAUSE_SECONDS if self._last_round_a_win
                              else ROUND_LOSS_PAUSE_SECONDS)
                        - PVP_EXPLOSION_HOLD_SECONDS)
        remaining = max(0.0, min(total, self.round_over_pause))

        if self.match_mode == "pvp3":
            labels = ("玩家一", "玩家二", "玩家三")
            wins = (rm.side_a_wins, rm.side_b_wins, rm.side_c_wins)
            winner = self._last_round_winner
            result_word = "" if is_intro else (
                f"{labels[('p1','p2','p3').index(winner)]}胜利"
                if winner in ("p1", "p2", "p3") else "")
            # 三人局间结果配色统一用金色/绿色提示（不再按 P1 视角分红绿）
            return {
                "round": rm.current_round,
                "total_rounds": rm.rounds_total,
                "format": fmt,
                "a_label": labels[0], "b_label": labels[1],
                "a_wins": wins[0], "b_wins": wins[1],
                "result": result,
                "result_word": result_word,
                "remaining": remaining,
                "total_pause": total,
                "p3": True,
                "c_label": labels[2], "c_wins": wins[2],
                "score_line": (f"{labels[0]} {wins[0]} : {wins[1]} "
                               f"{labels[1]} : {wins[2]} {labels[2]}"),
                "result_color": (255, 235, 160) if is_intro else (50, 255, 120),
            }

        a_label, b_label = "玩家一", "玩家二"
        # 胜方文案：PVP 按谁击败谁显示
        if is_intro:
            result_word = ""
        elif result == "win":
            result_word = "玩家一胜利"
        else:
            result_word = "玩家二胜利"
        return {
            "round": rm.current_round,
            "total_rounds": rm.rounds_total,
            "format": fmt,
            "a_label": a_label, "b_label": b_label,
            "a_wins": rm.side_a_wins, "b_wins": rm.side_b_wins,
            "result": result,
            "result_word": result_word,
            "remaining": remaining,
            "total_pause": total,
        }

    def _render_intermission(self) -> None:
        """局间/开局信息覆盖层：压暗 + 三行居中文案 + 底部倒计时读条（两端向中央收）。"""
        d = self._intermission_data()
        # 1) 压暗遮罩（约 40%）
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(100)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        result = d["result"]
        is_intro = (result == "intro")
        if is_intro:
            res_color = (255, 235, 160)          # 金色：开战
        elif result == "win":
            res_color = (50, 255, 120)           # 绿：胜方提示
        else:
            res_color = (255, 50, 50)            # 红：负方提示
        # 三人混战：结果色统一走数据里的配色（不按 P1 视角分红绿）
        if d.get("p3"):
            res_color = d.get("result_color", res_color)

        # 2) 主标题：第 X 局 · 系列格式
        title = f"第 {d['round']} 局 · {d['format']}"
        t_img = self._inter_font_title.render(title, True, COLOR_TEXT)
        self.screen.blit(t_img, t_img.get_rect(center=(cx, 300)))

        # 3) 比分行：A 胜局 : B 胜局（三人混战为三列）
        if d.get("p3"):
            score = d["score_line"]
        else:
            score = f"{d['a_label']} {d['a_wins']} : {d['b_wins']} {d['b_label']}"
        s_img = self._inter_font_score.render(score, True, COLOR_TEXT)
        self.screen.blit(s_img, s_img.get_rect(center=(cx, 358)))

        # 4) 结果 + 倒计时文字
        if is_intro:
            sub = f"{d['format']} · 开战！"
        else:
            word = d["result_word"]
            n = int(math.ceil(d["remaining"]))
            sub = f"{word} · {n} 秒后开战…"
        sub_img = self.font.render(sub, True, res_color)
        self.screen.blit(sub_img, sub_img.get_rect(center=(cx, 408)))

        # 5) 底部倒计时读条（居中、两端向中央收缩；白色，不随结果变色）
        if d["total_pause"] > 0:
            bar_w = int(SCREEN_WIDTH * 0.6)
            bar_h = 8
            bar_y = SCREEN_HEIGHT - 120
            ratio = d["remaining"] / d["total_pause"]
            half = int(bar_w / 2 * ratio)
            track = pygame.Rect(cx - bar_w // 2, bar_y, bar_w, bar_h)
            pygame.draw.rect(self.screen, (70, 70, 80), track, border_radius=bar_h // 2)
            fill = pygame.Rect(cx - half, bar_y, half * 2, bar_h)
            if fill.width > 0:
                pygame.draw.rect(self.screen, (255, 255, 255), fill, border_radius=bar_h // 2)
            # 6) 倒计时数字（秒.百分位，白色；读条下方居中，圆润加粗字体，右侧带 s 单位）
            num = f"{max(0.0, d['remaining']):.2f}s"
            num_img = self._inter_font_countdown.render(num, True, (255, 255, 255))
            self.screen.blit(num_img, num_img.get_rect(center=(cx, bar_y + bar_h + 24)))

    def _draw_result_card(self, rows) -> None:
        """结果档案卡：深底圆角矩形 + 行渲染。

        rows: 三元组 (kind, label, value) 列表
          - ("kv", label, value)  键值行：标签左对齐、数值右对齐（克制档案系）
          - ("score", None, text) 大比分行：加粗圆润数字居中
          - ("fmt",  None, text) 系列格式行：小字金色居中
        """
        cx = SCREEN_WIDTH // 2
        n = len(rows)
        h = RESULT_CARD_PAD_Y * 2 + n * RESULT_CARD_LINE_GAP
        card = pygame.Rect(cx - RESULT_CARD_W // 2, RESULT_CARD_TOP, RESULT_CARD_W, h)
        pygame.draw.rect(self.screen, RESULT_CARD_BG, card, border_radius=8)
        pygame.draw.rect(self.screen, RESULT_CARD_BORDER, card, 2, border_radius=8)
        for i, (kind, label, value) in enumerate(rows):
            cy = card.top + RESULT_CARD_PAD_Y + i * RESULT_CARD_LINE_GAP \
                + RESULT_CARD_LINE_GAP // 2
            if kind == "kv":
                l_img = self.font.render(label, True, RESULT_LABEL_COLOR)
                v_img = self.font.render(value, True, RESULT_VALUE_COLOR)
                self.screen.blit(l_img,
                                 l_img.get_rect(midleft=(card.left + RESULT_CARD_PAD_X, cy)))
                self.screen.blit(v_img,
                                 v_img.get_rect(midright=(card.right - RESULT_CARD_PAD_X, cy)))
            elif kind == "score":
                img = self._inter_font_countdown.render(value, True, RESULT_VALUE_COLOR)
                self.screen.blit(img, img.get_rect(center=(cx, cy)))
            else:  # "fmt" 系列格式小字（金色）
                img = self._inter_font_score.render(value, True, PAUSE_HOVER_BORDER)
                self.screen.blit(img, img.get_rect(center=(cx, cy)))

    def _render_result_panel(self) -> None:
        """PVP 结果结算页：遮罩 + 顶部系列比分小字 + 大比分档案卡 + 返回按钮。

        档案卡 = 大比分 玩家一 x : y 玩家二 + 系列格式（如 先胜3局）。
        全部只读现有数据源，不新增任何游戏逻辑 / 状态。
        """
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        rm = self.round_manager
        cx = SCREEN_WIDTH // 2
        fmt = {3: "三局两胜", 4: "四局三胜", 5: "五局四胜"}.get(
            rm.win_needed, f"先胜{rm.win_needed}局")

        if self.match_mode == "pvp3":
            # 三人混战结算页：三方胜局 + 系列胜者标题
            labels = ("玩家一", "玩家二", "玩家三")
            wins = (rm.side_a_wins, rm.side_b_wins, rm.side_c_wins)
            series = f"{labels[0]} {wins[0]} : {wins[1]} {labels[1]} : {wins[2]} {labels[2]}"
            winner = self._pvp3_winner
            win_idx = ("p1", "p2", "p3").index(winner) if winner in ("p1", "p2", "p3") else None
            title = f"{labels[win_idx]}胜利" if win_idx is not None else "系列赛结束"
            title_color = RESULT_WIN_COLOR if win_idx == 0 else (
                (50, 255, 120) if win_idx is not None else RESULT_LOSE_COLOR)
            rows = [
                ("score", None, series),
                ("fmt", None, fmt),
            ]
        else:
            a_win = rm.a_win      # property：side_a 是否已达胜点（与 _after_round_settled 一致）
            a_label, b_label = "玩家一", "玩家二"
            title_color = RESULT_WIN_COLOR if a_win else RESULT_LOSE_COLOR
            # 1) 顶部系列比分小字：玩家 3 : 1 玩家2
            series = f"{a_label} {rm.side_a_wins} : {rm.side_b_wins} {b_label}"
            # 2) 结果大字标题（系列赛最终胜方；措辞与局间提示一致）
            title = "玩家一胜利" if a_win else "玩家二胜利"
            # 3) 档案卡行（大比分 + 系列格式）
            rows = [
                ("score", None, f"{a_label}  {rm.side_a_wins} : {rm.side_b_wins}  {b_label}"),
                ("fmt", None, fmt),
            ]

        # 1) 顶部系列比分小字
        s_img = self._inter_font_score.render(series, True, PAUSE_HOVER_BORDER)
        self.screen.blit(s_img, s_img.get_rect(center=(cx, RESULT_SERIES_TOP)))

        # 2) 结果大字标题
        t_img = self.big_font.render(title, True, title_color)
        self.screen.blit(t_img, t_img.get_rect(center=(cx, RESULT_TITLE_Y)))

        # 3) 档案卡行
        self._draw_result_card(rows)

        # 4) 返回按钮（支持悬停高亮）
        self._draw_button(self._result_menu_button_rect(), "返回菜单",
                          hover=self._result_hover)

    # ------------------------------------------------------------------
    # Phase UI Step 1-B：战斗暂停菜单（PLAYING 按 ESC 调出；PAUSED 下 update 已冻结战斗）
    # 四层页面：main → settings → help / audio_master / audio_sfx；ESC 逐级返回。
    # 复用 PAUSE_* 常量、主菜单悬停/点击音效；全部为表现层，不触碰游戏逻辑。
    # ------------------------------------------------------------------
    def _pause_open(self) -> None:
        """PLAYING → PAUSED：打开暂停主菜单（焦点回到首页第 0 项）。"""
        self._pause_section = "main"
        self._pause_focus = 0
        self._pause_hover = None
        self.state = GameState.PAUSED

    def _pause_close(self) -> None:
        """PAUSED → PLAYING：恢复战斗（暂停期间战斗被冻结，数据无损）。"""
        self.audio.play(SFX_NAME_CLICK)
        self._pause_hover = None
        self.state = GameState.PLAYING

    def _pause_section_title(self) -> str:
        """当前暂停子页标题。"""
        return {
            "main": PAUSE_TITLE,
            "settings": PAUSE_SETTINGS_TITLE,
            "help": PAUSE_HELP_TITLE,
            "audio_master": PAUSE_AUDIO_TITLE + "（主音量）",
            "audio_sfx": PAUSE_AUDIO_TITLE + "（音效）",
        }.get(self._pause_section, PAUSE_TITLE)

    def _pause_items(self):
        """当前页按钮列表：[(标签, 动作标识), ...]，动作由 _pause_action 分发。"""
        s = self._pause_section
        if s == "main":
            return list(zip(PAUSE_BTN_LABELS, ("resume", "restart", "settings", "menu")))
        if s == "settings":
            return list(zip(PAUSE_SETTINGS_LABELS, ("back", "help", "audio_master", "audio_sfx")))
        if s in ("audio_master", "audio_sfx"):
            return list(zip(PAUSE_AUDIO_LABELS, ("vol_up", "vol_down", "mute", "back")))
        return list(zip(PAUSE_HELP_LABELS, ("back",)))   # help 页

    def _pause_rects(self):
        """当前页按钮矩形：主列自 PAUSE_BTN_TOP 向下排列；help 页单按钮置底居中。"""
        n = len(self._pause_items())
        if self._pause_section == "help":
            return [pygame.Rect(SCREEN_WIDTH // 2 - PAUSE_BTN_W // 2,
                                SCREEN_HEIGHT - 140, PAUSE_BTN_W, PAUSE_BTN_H)]
        return [
            pygame.Rect(SCREEN_WIDTH // 2 - PAUSE_BTN_W // 2,
                        PAUSE_BTN_TOP + i * (PAUSE_BTN_H + PAUSE_BTN_GAP),
                        PAUSE_BTN_W, PAUSE_BTN_H)
            for i in range(n)
        ]

    def _pause_audio_kind(self) -> str:
        """当前音量页对应的音频通道（master / sfx）。"""
        return "master" if self._pause_section == "audio_master" else "sfx"

    def _pause_back(self) -> None:
        """返回上级页：help/audio → settings → main（main 页的返回由 ESC 关闭暂停）。"""
        self._pause_section = "settings" if self._pause_section != "settings" else "main"
        self._pause_focus = 0

    def _pause_action(self, action: str) -> None:
        """暂停页按钮动作分发（纯 UI 编排；战斗"重新本局"复用 _start_round）。"""
        if action == "resume":
            self._pause_close()
        elif action == "restart":
            self._start_round()                # 重载当前关战场 + 复位局标记
            self.round_over_pause = ROUND_INTRO_SECONDS
            self._pause_after = "intro"
            self._round_overlay_hold = 0.0   # 开局提示无"先播爆炸"阶段
            self._pause_close()
        elif action == "menu":
            self.reset()
        elif action == "settings":
            self._pause_section = "settings"
            self._pause_focus = 0
        elif action == "help":
            self._pause_section = "help"
            self._pause_focus = 0
        elif action in ("audio_master", "audio_sfx"):
            self._pause_section = action
            self._pause_focus = 0
        elif action == "back":
            self._pause_back()
        elif action == "vol_up":
            self._adjust_volume(self._pause_audio_kind(), MENU_VOLUME_STEP)
        elif action == "vol_down":
            self._adjust_volume(self._pause_audio_kind(), -MENU_VOLUME_STEP)
        elif action == "mute":
            self.audio.toggle_mute()

    def _pause_handle_mouse(self, pos) -> None:
        """鼠标悬停：命中按钮即聚焦（键鼠统一到 _pause_focus），移入边沿播悬停音。"""
        idx = None
        for i, rect in enumerate(self._pause_rects()):
            if rect.collidepoint(pos):
                idx = i
                break
        if idx is not None and idx != self._pause_hover:
            self.audio.play(SFX_NAME_HOVER, volume_scale=SFX_BUTTON_HOVER_VOLUME)
        self._pause_hover = idx
        if idx is not None:
            self._pause_focus = idx

    def _pause_handle_click(self, pos) -> bool:
        """鼠标左键：命中按钮则执行动作，返回是否消费（供上层播点击音）。"""
        items = self._pause_items()
        for i, rect in enumerate(self._pause_rects()):
            if rect.collidepoint(pos) and i < len(items):
                self._pause_focus = i
                self._pause_action(items[i][1])
                return True
        return False

    def _pause_handle_key(self, key) -> None:
        """暂停菜单键盘：ESC 逐级返回 / ↑↓(W·S) 移动焦点 / Enter·空格·J 确认。"""
        if key == pygame.K_ESCAPE:
            if self._pause_section == "main":
                self._pause_close()
            else:
                self._pause_back()
            return
        if key in (pygame.K_UP, pygame.K_w):
            n = len(self._pause_items())
            self._pause_focus = (self._pause_focus - 1) % n
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            n = len(self._pause_items())
            self._pause_focus = (self._pause_focus + 1) % n
            return
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j):
            items = self._pause_items()
            if items:
                self.audio.play(SFX_NAME_CLICK)
                self._pause_action(items[self._pause_focus % len(items)][1])

    def _render_pause(self) -> None:
        """暂停菜单渲染：全窗遮罩(含 UI 区) + 标题 + 系列进度行 + 按钮列；子页附文本/音量。"""
        overlay = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(PAUSE_OVERLAY_ALPHA)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        # 1) 标题（与局间标题同款字号，观感统一）
        t_img = self._inter_font_title.render(self._pause_section_title(), True, COLOR_TEXT)
        self.screen.blit(t_img, t_img.get_rect(center=(cx, PAUSE_TITLE_Y)))

        # 2) 主菜单页系列进度行（局制模式；战斗进行中 round_over_pause<=0 时显示）
        if self._pause_section == "main" and self.round_over_pause <= 0:
            rm = self.round_manager
            fmt = {3: "三局两胜", 4: "四局三胜", 5: "五局四胜"}.get(
                rm.win_needed, f"先胜{rm.win_needed}局")
            a_l, b_l = "玩家一", "玩家二"
            i1 = self.font.render(f"第 {rm.current_round} 局 · {fmt}",
                                  True, PAUSE_HOVER_BORDER)
            i2 = self.font.render(f"{a_l} {rm.side_a_wins} : {rm.side_b_wins} {b_l}",
                                  True, COLOR_TEXT)
            self.screen.blit(i1, i1.get_rect(center=(cx, PAUSE_INFO_TOP - 14)))
            self.screen.blit(i2, i2.get_rect(center=(cx, PAUSE_INFO_TOP + 10)))

        # 3) 帮助页文本（标题下方逐行居中；按钮置底由 _pause_rects 提供）
        if self._pause_section == "help":
            y = PAUSE_TITLE_Y + 70
            for line in HELP_TEXT:
                img = self.font.render(line, True, COLOR_TEXT)
                self.screen.blit(img, img.get_rect(center=(cx, y)))
                y += 24

        # 4) 音量/音效页数值（只读 audio，不保存状态）
        if self._pause_section in ("audio_master", "audio_sfx"):
            kind = self._pause_audio_kind()
            cur = self.audio.master if kind == "master" else self.audio.sfx
            name = "主音量" if kind == "master" else "音效"
            state = "已静音" if self.audio.muted else f"{int(round(cur * 100))}%"
            st_img = self.font.render(f"{name}：{state}", True, PAUSE_HOVER_BORDER)
            self.screen.blit(st_img, st_img.get_rect(center=(cx, PAUSE_TITLE_Y + 70)))

        # 5) 按钮列（焦点/悬停金边描边 + 左右指示三角）
        items = self._pause_items()
        for i, (label, _action) in enumerate(items):
            rect = self._pause_rects()[i]
            hovered = (i == self._pause_focus) or (i == self._pause_hover)
            pygame.draw.rect(self.screen, (80, 80, 90), rect, border_radius=6)
            pygame.draw.rect(self.screen,
                             PAUSE_HOVER_BORDER if hovered else COLOR_TEXT,
                             rect, 2, border_radius=6)
            b_img = self.font.render(label, True, COLOR_TEXT)
            self.screen.blit(b_img, b_img.get_rect(center=rect.center))
            if hovered:
                self._draw_select_triangles(self.screen, rect, PAUSE_HOVER_BORDER)

    def render(self):
        if self.state == GameState.MENU:
            self.menu.render(self.screen)
        elif self.state == GameState.GAME_OVER:
            self._render_battle()
            self._render_result_panel()
        elif self.state == GameState.VICTORY:
            self._render_battle()
            self._render_result_panel()
        elif self.state == GameState.PLAYING:
            self._render_battle()
            # Phase 7.0-B Player Status Panel：PLAYING 玩家状态面板（P1/P2 得分/胜局/弹药）
            # 三人混战（pvp3）同用这条底部状态栏：左红 P1 / 中绿 P3 / 右蓝 P2，
            # 由面板内按 match_mode 分派三栏渲染（VS 圆标在 pvp3 下不画，见 _render_ui_area）
            self.player_status_panel.render(self.screen, self)
            # 局间/开局信息覆盖层：暂停期内压暗 + 三行文案 + 底部读条（不新增 GameState）
            # hold 剩余 > 0 时先让爆炸完整播完（战场无遮挡），播完才弹胜利提示
            if self.round_over_pause > 0 and self._round_overlay_hold <= 0:
                self._render_intermission()
        else:  # PAUSED：冻结战场 + 暂停菜单覆盖层（不叠加战斗 HUD）
            self._render_battle()
            self._render_pause()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Phase 7.0 游戏区 / UI 区分离
    # 布局：游戏区 = 地图区（固定 GAME_AREA_HEIGHT=SCREEN_HEIGHT=800），
    # UI 状态区位于游戏区下方（WINDOW_HEIGHT = 游戏区 + STATUS_PANEL_HEIGHT）。
    # SCREEN_HEIGHT 语义不变（仍为实体下边界），UI 区只扩展建窗高度，不侵入游戏区。
    # ------------------------------------------------------------------
    def _ui_area_rect(self) -> pygame.Rect:
        """游戏区下方 UI 状态区矩形。"""
        return pygame.Rect(0, UI_AREA_Y, SCREEN_WIDTH, STATUS_PANEL_HEIGHT)

    def _bg_top_edge_color(self, surface) -> tuple:
        """背景图上边缘平均色：采样顶端 3 行的像素均值，作为下移时
        顶部"渐变软填充"的贴图侧颜色（贴近图片一侧观感自然）。"""
        rows = min(3, surface.get_height())
        rs = gs = bs = n = 0
        for r in range(rows):
            for x in range(0, surface.get_width(), 4):
                px = surface.get_at((x, r))
                rs += px[0]
                gs += px[1]
                bs += px[2]
                n += 1
        if n == 0:
            return COLOR_BG
        return (rs // n, gs // n, bs // n)

    def _build_level_bg(self, bg_name: str):
        """按文件名构建一张关卡专属背景（整窗 800×950 预合成，含下移渐变软填充）。
        图片缺失/加载失败 或 LEVEL_BG_ENABLED=False 时返回 None（调用方回退纯色底）。"""
        if not LEVEL_BG_ENABLED or not bg_name:
            return None
        path = os.path.join(_PROJECT_ROOT, bg_name)
        try:
            raw = pygame.image.load(path)
        except (pygame.error, OSError, ValueError):
            return None
        try:
            scaled = pygame.transform.smoothscale(raw, (SCREEN_WIDTH, WINDOW_HEIGHT))
            if LEVEL_BG_OFFSET_Y > 0:
                off = min(LEVEL_BG_OFFSET_Y, WINDOW_HEIGHT - 1)
                result = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))
                result.blit(scaled, (0, off))
                top_color = self._bg_top_edge_color(scaled)
                for row in range(off):
                    t = row / max(1, off - 1)  # 0=最顶(纯色底) → 1=贴近图片上缘
                    c = tuple(
                        int(c_base + (c_top - c_base) * t)
                        for c_base, c_top in zip(COLOR_BG, top_color))
                    pygame.draw.line(result, c, (0, row), (SCREEN_WIDTH - 1, row))
                scaled = result
            return scaled.convert()
        except (pygame.error, OSError, ValueError):
            return None

    def _load_level_bg_for_stage(self, stage_config) -> None:
        """切关时按 stage_config["bg"] 加载本关专属背景（对应关系：关卡 N ↔ 关卡背景_N.png，
        由各 stage 配置里的 bg 字段保证，绝不串台）。失败/缺失自动回退纯色底（self.level_bg=None）。"""
        self.level_bg = self._build_level_bg(stage_config.get("bg", ""))

    def _render_ui_area(self) -> None:
        """绘制 UI 状态区底带（Phase 7.5-B 深色驾驶舱）。

        取代原纯白底带：程序化深色金属渐变 + 左右阵营氛围光 + 中央 VS 金属圆 +
        顶/底沿接缝高光 + 底部金属拉丝，使状态栏与战场同处一个"世界"。

        分层（自上而下）：
          1) 逐行竖向渐变底色（顶 UI_AREA_BG_TOP → 底 UI_AREA_BG_BOTTOM）
          2) 左右暗角压暗（UI_AREA_VIGNETTE，靠 alpha 从边缘线性衰减，不依赖 radial）
          3) P1 左区红光 / P2 右区蓝光（UI_AREA_GLOW_*，中等亮度，不抢文字）
          4) 底部金属拉丝（极淡水平细线）
          5) 中央 VS 金属圆（双描边做立体高光；VS 文字常驻，局间覆盖层不压暗它）
          6) 顶沿高光细线 + 底沿收边细线（金属接缝）

        图片模式（self.level_bg 存在）：叠加半透明白面纱（LEVEL_BG_UI_ALPHA）让
        关卡背景透出（保留原行为）；无图时纯深色驾驶舱（不再回退纯白）。
        """
        rect = self._ui_area_rect()
        x0, y0, w, h = rect.x, rect.y, rect.width, rect.height
        cx = x0 + w // 2

        # 1) 竖向渐变底色（逐行）
        top_c = UI_AREA_BG_TOP
        bot_c = UI_AREA_BG_BOTTOM
        for row in range(h):
            t = row / max(1, h - 1)
            c = tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * t) for i in range(3))
            pygame.draw.line(self.screen, c, (x0, y0 + row), (x0 + w - 1, y0 + row))

        # 2) 左右暗角：从边缘向中线 alpha 线性衰减（左半 / 右半分别）
        #    注：子 Surface 尺寸为 (w,h)，必须用本地坐标 (0..w-1, 0..h-1) 绘制，
        #    再整体 blit 到 (x0,y0)；用绝对坐标会画到子表面外被裁剪（此前 bug）。
        vig = pygame.Surface((w, h), pygame.SRCALPHA)
        vig.fill((0, 0, 0, 0))
        vig_col = UI_AREA_VIGNETTE
        half = w // 2
        for xx in range(half):
            # 距最近侧边的归一化距离 0(边)->1(中线)
            a = int(150 * (1.0 - xx / max(1, half - 1)))
            pygame.draw.line(vig, (vig_col[0], vig_col[1], vig_col[2], max(0, a)),
                             (xx, 0), (xx, h - 1))
            pygame.draw.line(vig, (vig_col[0], vig_col[1], vig_col[2], max(0, a)),
                             (w - 1 - xx, 0), (w - 1 - xx, h - 1))
        self.screen.blit(vig, (x0, y0))

        # 3) 阵营氛围光（三色柔光晕）：每方独立「呼吸 + 换弹提亮 + 命中闪光」，与纯绿版
        #    同款逻辑——各自是「一个光源、从锚点自然化开、远处淡到零」的柔和光晕，而非实色带。
        #    2026-10-24 历程：先删红蓝仅留中绿；后重做时误把三色画在同张画布、后画整列覆盖
        #    先画（无混色），交界处硬切成像素方块。本次改为【逐列 over 混色】彻底修复：
        #    每一列把红/绿/蓝在该列的贡献用 over 算子合成一种颜色再落笔，交界处是平滑渐变
        #    （左缘纯红 → 红绿过渡 → 中心纯绿 → 绿蓝过渡 → 右缘纯蓝），不再是硬边色块。
        #    布局：pvp3=左红/中绿/右蓝；pvp=左红/右蓝（中心柔和相接，不留黑缝/黑边）。
        #    守卫：对应坦克不存在（如菜单态）则该侧不画，避免误亮。
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        glow.fill((0, 0, 0, 0))
        if UI_AREA_DYNAMIC:
            tt = pygame.time.get_ticks() / 1000.0
            breath = UI_AREA_GLOW_BREATH_AMP * math.sin(
                2 * math.pi * tt / UI_AREA_GLOW_BREATH_PERIOD)
            def _reload_on(tank):
                # 换弹提亮：死人不提亮（死亡路径不推进 update_ammo，reload_remaining 会冻结；
                # 现死亡登记处清零 + 此处守卫双保险）。
                return (bool(getattr(tank, "is_reloading", False))
                        and tank not in self._dead_players) if tank is not None else False
            def _ga(base, flash_t, reload_on, breath_scale=1.0):
                return max(0, min(255, int(base + breath * breath_scale
                                 + (UI_AREA_RELOAD_BOOST if reload_on else 0)
                                 + UI_AREA_FLASH_BOOST * (flash_t / UI_AREA_FLASH_DURATION))))
            # 红/绿/蓝均乘各自稳态系数（红绿=80/30 齐平、蓝=3.8 最亮）；呼吸各带系数。
            ga_p1 = _ga(UI_AREA_GLOW_ALPHA * UI_AREA_GLOW_RED_SCALE,
                        self._ui_flash_p1, _reload_on(self.player_tank),
                        UI_AREA_GLOW_RED_BREATH_SCALE)
            ga_p2 = _ga(UI_AREA_GLOW_ALPHA * UI_AREA_GLOW_BLUE_SCALE,
                        self._ui_flash_p2, _reload_on(self.player2_tank))
            # 绿：基线 80（ALPHA×GREEN_SCALE，与红齐平），呼吸满幅。
            ga_p3 = _ga(UI_AREA_GLOW_ALPHA * UI_AREA_GLOW_GREEN_SCALE,
                        self._ui_flash_p3, _reload_on(self.player3_tank),
                        UI_AREA_GLOW_GREEN_BREATH_SCALE)
        else:
            ga_p1 = ga_p2 = ga_p3 = UI_AREA_GLOW_ALPHA
        # 各色光晕：anchor=锚点，W=半宽（在 anchor±W 处淡到 0）。余弦隆起 p=0.5*(1+cos(pi*d))。
        # pvp3：绿居中（中心满亮、两侧归零，与原始纯绿版完全一致）；红锚左缘、蓝锚右缘，
        #       各自向中心化开——左缘纯红、右缘纯蓝、中心纯绿，过渡区平滑混色。
        # pvp ：红锚左缘、蓝锚右缘，半宽=整条宽度使二者在中点柔和相接（不留黑缝/黑边）。
        if self.match_mode == "pvp3":
            bumps = []
            if self.player_tank is not None:
                bumps.append((0.0, w / 2.0, ga_p1, UI_AREA_GLOW_RED))
            if self.player3_tank is not None:
                bumps.append((w / 2.0, w / 2.0, ga_p3, UI_AREA_GLOW_GREEN))
            if self.player2_tank is not None:
                bumps.append((w, w / 2.0, ga_p2, UI_AREA_GLOW_BLUE))
        elif self.match_mode == "pvp":
            bumps = []
            if self.player_tank is not None:
                bumps.append((0.0, w / 2.0, ga_p1, UI_AREA_GLOW_RED))
            if self.player2_tank is not None:
                bumps.append((w, w / 2.0, ga_p2, UI_AREA_GLOW_BLUE))
        else:
            bumps = []
        # 逐列 over 混色：先在该列把多个光晕合成一个像素，再画一行——杜绝后画覆盖先画的硬边方块。
        for xx in range(w):
            cr = cg = cb = 0.0   # 累积颜色（非预乘，0~255）
            ca = 0.0             # 累积 alpha（0~1）
            for (anchor, W, ga, col) in bumps:
                d = (xx - anchor) / W
                if d <= -1.0 or d >= 1.0:
                    continue
                sa = (ga / 255.0) * (0.5 * (1.0 + math.cos(math.pi * d)))  # 该列该色有效透明度
                if sa <= 0.003:
                    continue
                inv = (1.0 - sa) * ca
                na = sa + inv
                if na <= 0.0:
                    continue
                # over 算子：C_out = (A_s·C_s + A_d·(1-A_s)·C_d) / A_out
                cr = (sa * col[0] + inv * cr) / na
                cg = (sa * col[1] + inv * cg) / na
                cb = (sa * col[2] + inv * cb) / na
                ca = na
            if ca > 0.003:
                pygame.draw.line(glow, (int(round(cr)), int(round(cg)), int(round(cb)),
                                        int(round(ca * 255))),
                                 (xx, 0), (xx, h - 1))
        self.screen.blit(glow, (x0, y0))

        # 4) 底部金属拉丝（极淡水平细线）
        brush = pygame.Surface((w, h), pygame.SRCALPHA)
        brush.fill((0, 0, 0, 0))
        bc = UI_AREA_BRUSH
        ba = UI_AREA_BRUSH_ALPHA
        for i in range(1, 6):
            yy = h - i * 2
            pygame.draw.line(brush, (bc[0], bc[1], bc[2], ba),
                             (0, yy), (w - 1, yy))
        self.screen.blit(brush, (x0, y0))

        # 5) 中央 VS 金属圆（双描边立体 + 文字常驻）
        #    整场对决结束的结算页（GAME_OVER / VICTORY）不再绘制 VS：胜负已分，
        #    再挂"VS"会显得没结束；局间覆盖层（仍在 PLAYING 态）仍常驻，沿用 option A。
        #    三人混战（pvp3）同样不画 VS：中栏要让给绿方 P3 状态栏（左红/中绿/右蓝）。
        if self.state not in (GameState.GAME_OVER, GameState.VICTORY) \
                and self.match_mode != "pvp3":
            vr = UI_AREA_VS_RADIUS
            vcy = y0 + h // 2
            pygame.draw.circle(self.screen, UI_AREA_VS_BG, (cx, vcy), vr)
            pygame.draw.circle(self.screen, UI_AREA_VS_RING, (cx, vcy), vr, width=2)
            pygame.draw.circle(self.screen, UI_AREA_VS_INNER, (cx, vcy), vr - 4, width=1)
            vs_img = self._ui_area_vs_font.render("VS", True, UI_AREA_VS_TEXT)
            self.screen.blit(vs_img, vs_img.get_rect(center=(cx, vcy)))

        # 6) 顶沿高光 + 底沿收边（金属接缝）
        pygame.draw.line(self.screen, UI_AREA_SEAM_TOP,
                         (x0, y0), (x0 + w - 1, y0), 1)
        pygame.draw.line(self.screen, UI_AREA_SEAM_BOTTOM,
                         (x0, y0 + h - 1), (x0 + w - 1, y0 + h - 1), 1)

        # 说明：深色驾驶舱为不透底设计（红蓝氛围光即"融入战场"的载体），
        # 不再叠加旧白面纱（LEVEL_BG_UI_ALPHA）。原白面纱会把驾驶舱洗成灰白、
        # 并遮盖动态辉光，与 B/C 档目标冲突；关卡背景仍作整窗战斗底（见 _render_battle）。

    def _render_battle(self):
        """绘制战场（背景 + 地图 + 玩家 + 敌人 + 子弹 + 道具）。PLAYING 与结果状态共用。
        游戏世界统一绘制到 world_surface，再以 shake.offset() 贴回 self.screen 实现屏幕震动；
        UI 状态区底带（_render_ui_area）不抖，直接画在 self.screen。"""
        surf = self.world_surface
        surf.fill(COLOR_BG)
        # 关卡背景图：整窗铺底（含状态栏）。图片缺失时保持旧行为（纯色深灰底）。
        if self.level_bg is not None:
            surf.blit(self.level_bg, (0, 0))
        self.map_renderer.render(surf)
        if self.player_tank not in self._dead_players:
            self.player_tank.render(surf)
        if (self.player2_tank is not None
                and self.player2_tank not in self._dead_players):
            self.player2_tank.render(surf)
        if (self.player3_tank is not None
                and self.player3_tank not in self._dead_players):
            self.player3_tank.render(surf)
        for enemy in self.enemy_tanks:
            enemy.render(surf)
        for bullet in self.bullets:
            bullet.render(surf)
        # 激光预测虚线：拾取后坦克前方实时预览（固定 4 次反射，随朝向实时更新）；
        # 颜色按发射方阵营走（红方红 / 蓝方蓝）
        if ITEM_SYSTEM_ENABLED:
            for tank, owner in ((self.player_tank, "p1"),
                                (self.player2_tank, "p2"),
                                (self.player3_tank, "p3")):
                if (tank is None or tank in self._dead_players
                        or not getattr(tank, "laser_charged", False)):
                    continue
                self._draw_laser_preview(surf, tank, owner)
        for laser in self.lasers:
            laser.render(surf)
        # 追踪导弹：目标色弹体 + 同色渐隐烟迹（激光之后、道具之前）
        for missile in self.missiles:
            missile.render(surf)
        # 道具系统（Phase 5.4.3 / T7.1）：绘制道具（仅当回退开关开启时）。
        # 最后 10 秒的"呼吸灯"提醒由 item.render 内部按 ITEM_FLASH_START /
        # ITEM_BREATH_PERIOD 实现（透明度正弦呼吸），此处不再做二值忽闪。
        if ITEM_SYSTEM_ENABLED:
            for item in self.item_spawn_manager.items:
                item.render(surf)
        # Phase 7.1 Floating Score：世界空间战斗反馈（+1/+2/+3）
        for fs in self.floating_scores:
            fs.render(surf)
        # Phase 7.1 爆炸/碎裂特效：世界空间表现层
        for e in self.explosions:
            e.render(surf)
        # 屏幕震动：整张游戏世界以 shake.offset() 为左上角偏移贴回 self.screen
        # （先铺背景色，避免抖动时边缘露出上一帧残影）
        self.screen.fill(COLOR_BG)
        self.screen.blit(self.world_surface, self.shake.offset())
        # Phase 7.0 游戏区/UI 区分离：游戏区下方绘制 UI 状态区底带（不抖）
        self._render_ui_area()

    def _draw_laser_preview(self, surf, tank, owner: str = "p1") -> None:
        """激光预测虚线：拾取后坦克炮口前方实时预览实际弹道（固定 4 次反射）。
        与实射共用 trace_laser_path，保证预览 == 实际前 4 段反射；只在战场上画。
        虚线颜色按发射方阵营走（owner="p1" 红 / "p2" 蓝）。
        虚线走马灯式沿路径向落点方向流动（相位 = 时间×速度，弧长连续）。"""
        muzzle_x, muzzle_y = tank.get_muzzle_position()
        dx0, dy0 = tank.get_direction_vector()
        vertices, _hit = trace_laser_path(
            muzzle_x, muzzle_y, dx0, dy0, self.game_map,
            targets=self._laser_targets(),
            max_bounces=LASER_PREVIEW_BOUNCES,
        )
        color = COLOR_LASER_BY_OWNER.get(owner, COLOR_LASER_FALLBACK)
        # 走马灯相位：每帧按真实时间递增，与帧率无关（暂停/掉帧不跳变）
        phase = (pygame.time.get_ticks() / 1000.0) * LASER_PREVIEW_FLOW_SPEED
        _draw_dashed_polyline(surf, vertices, color, phase=phase)

    # ------------------------------------------------------------------
    # Phase UI 第一步：多级菜单构建（主菜单/模式/关卡/难度/说明/音频页）
    # 页面与按钮几何见 ui.menu + settings 的布局常量。
    # ------------------------------------------------------------------
    def _result_menu_button_rect(self):
        """结果页“返回菜单”按钮区域（档案卡下方，RESULT_BTN_TOP）。"""
        return pygame.Rect(SCREEN_WIDTH // 2 - RESULT_BTN_W // 2,
                           RESULT_BTN_TOP, RESULT_BTN_W, RESULT_BTN_H)

    def _draw_button(self, rect: pygame.Rect, label: str, hover: bool = False):
        """结果页简单按钮绘制（矩形 + 描边 + 文字）；hover 时金色描边高亮。"""
        pygame.draw.rect(self.screen, (80, 80, 90), rect, border_radius=6)
        pygame.draw.rect(self.screen,
                         PAUSE_HOVER_BORDER if hover else COLOR_TEXT,
                         rect, 2, border_radius=6)
        text = self.font.render(label, True, COLOR_TEXT)
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)
        if hover:
            self._draw_select_triangles(self.screen, rect, PAUSE_HOVER_BORDER)

    def _draw_select_triangles(self, surface, rect, color) -> None:
        """高亮指示三角：左右各一、尖端都指向按钮（镜像同步摆动，与 menu.py 同风格）。

        左三角尖端右移（靠近按钮）时，右三角尖端同步左移：
        左右共用同一相位 dx = A·sin(t·ω)，左三角平移 +dx、右三角平移 -dx。
        幅度 ≤ TRIANGLE_GAP → 尖端始终不进入按钮区域、不重叠字体。
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

    def _build_menu(self) -> None:
        """构建 MenuSystem 并推入根页（主菜单）；根页附带首页背景图与标题 Logo。"""
        self.menu = MenuSystem(self.audio, preview_loader=self._preview_card)
        self.menu.set_fonts(self.font, self.big_font)
        self._menu_bg = self._load_menu_background()
        self._menu_title = self._load_menu_title()
        self.menu.push(self._main_screen())

    def _preview_card(self, stage_index: int):
        """懒渲染并缓存某关的地图预览卡（纯结构迷你图 + 卡片框 + 关卡名标签）。

        首次悬停某关时才构建并缓存；之后命中缓存零开销。
        构建失败（数据异常）返回 None → 菜单不弹预览，静默回退。
        """
        if stage_index in self._preview_cards:
            return self._preview_cards[stage_index]
        if self._preview_font is None:
            self._preview_font = _create_font(PREVIEW_LABEL_SIZE, has_cjk=True)
        card = None
        try:
            st = self.level_manager.stages[stage_index]
            name = st.get("meta", {}).get("name", f"关卡 {stage_index + 1}")
            cell = PREVIEW_CELL_SIZE
            mini = pygame.Surface((GRID_SIZE * cell, GRID_SIZE * cell))
            if st.get("shape_fn"):
                # 连续几何关卡（Stage 5「戈壁环岛」）：按真实形状渲染后缩放，
                # 与战场同一套数据（MapRenderer + shape_fn）—— 圆弧沙洲 /
                # 真圆钢球 / LJR 水印，预览即实战，不用方块近似。
                grid, deco = st["map_data"]()
                gm = GameMap.from_map_data(grid, deco)
                visual_fn = st.get("visual_fn")
                gm.visual_colors = visual_fn() if visual_fn else None
                deco_fn = st.get("deco_fn")
                gm.decorations = deco_fn() if deco_fn else None
                gm.shapes = st["shape_fn"]()
                geometry_fn = st.get("geometry_fn")
                gm.geometry = geometry_fn() if geometry_fn else None
                full = pygame.Surface((GRID_SIZE * TILE_SIZE,
                                       GRID_SIZE * TILE_SIZE))
                MapRenderer(gm).render(full)
                mini = pygame.transform.smoothscale(
                    full, (GRID_SIZE * cell, GRID_SIZE * cell))
            else:
                # 老关卡（纯方块地图）：栅格迷你图，原样保留
                grid, _is_deco = st["map_data"]()
                for r in range(GRID_SIZE):
                    for c in range(GRID_SIZE):
                        v = grid[r][c]
                        if v == TileType.STEEL:
                            color = PREVIEW_STEEL
                        elif v == TileType.BRICK:
                            color = PREVIEW_BRICK
                        else:
                            color = PREVIEW_GROUND
                        pygame.draw.rect(mini, color,
                                         (c * cell, r * cell, cell, cell))
            label = self._preview_font.render(
                f"第{stage_index + 1}关 · {name}", True, PREVIEW_LABEL_COLOR)
            pad = PREVIEW_CARD_PAD
            mw = mini.get_width()
            mh = mini.get_height()
            card_w = max(label.get_width(), mw) + 2 * pad
            card_h = pad + PREVIEW_LABEL_H + PREVIEW_LABEL_GAP + mh + pad
            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(card, PREVIEW_CARD_BG, (0, 0, card_w, card_h),
                             border_radius=PREVIEW_CARD_RADIUS)
            pygame.draw.rect(card, PREVIEW_CARD_BORDER, (0, 0, card_w, card_h),
                             2, border_radius=PREVIEW_CARD_RADIUS)
            card.blit(label, label.get_rect(midtop=(card_w // 2, pad)))
            card.blit(mini, ((card_w - mw) // 2,
                             pad + PREVIEW_LABEL_H + PREVIEW_LABEL_GAP))
        except Exception:
            card = None
        self._preview_cards[stage_index] = card
        return card

    def _load_menu_background(self):
        """加载并缩放到全窗大小的主菜单背景图；缺失/损坏时返回 None（回退纯色底）。
        加载时自动裁掉底部连续黑色横带，让主题画面覆盖全窗，避免底部露出黑区。"""
        try:
            img = pygame.image.load(MENU_BG_PATH).convert()
            w, h = img.get_size()
            max_crop = int(h * MENU_BG_CROP_MAX_RATIO)
            crop = 0
            # 自底向上逐行算平均亮度，低于阈值视为黑色带；遇非黑行即停止（不误裁画面内容）
            for y in range(h - 1, -1, -1):
                lum = 0
                n = 0
                for x in range(0, w, 4):
                    px = img.get_at((x, y))
                    lum += (px[0] + px[1] + px[2]) // 3
                    n += 1
                if lum / n >= MENU_BG_BLACK_THRESH:
                    break
                crop += 1
                if crop >= max_crop:      # 上限保护，防误裁大片暗区
                    break
            if 0 < crop < h:
                img = img.subsurface((0, 0, w, h - crop))
            return pygame.transform.smoothscale(img, (SCREEN_WIDTH, WINDOW_HEIGHT))
        except Exception:
            return None

    def _load_menu_title(self):
        """加载并按 MENU_TITLE_W 缩放主菜单标题 Logo；缺失/损坏时返回 None（回退文字标题）。"""
        try:
            img = pygame.image.load(MENU_TITLE_PATH).convert_alpha()
            w = MENU_TITLE_W
            h = int(round(img.get_height() * w / max(1, img.get_width())))
            return pygame.transform.smoothscale(img, (w, h))
        except Exception:
            return None

    # -- 主菜单 --
    def _main_screen(self) -> MenuScreen:
        # 标题改用文字渲染（title_image=None），不再使用模糊的 AI 标题图；
        # 用专用大字粗体字体，呈现带描边+投影的游戏风金色标题。
        # 两档平齐：坦/战同高度(平齐)，克/大同高度(平齐)
        # （偏移正值=下沉，负值=上抬；战降到与坦平齐(-38→6)，大调到与克平齐(6→-38)）
        title_offsets = [6, -38, -38, 6]
        scr = MenuScreen("main", "坦克大战",
                         background=self._menu_bg, title_image=None,
                         title_font=self.title_font, title_offsets=title_offsets)
        scr.add(
            UiButton(column_button_rect(0, 5), "开始游戏",
                     lambda: self.menu.push(self._dual_screen())),
            UiButton(column_button_rect(1, 5), "游戏说明",
                     lambda: self.menu.push(self._help_screen())),
            UiButton(column_button_rect(2, 5), "音量",
                     lambda: self.menu.push(self._audio_screen("master", "音量"))),
            UiButton(column_button_rect(3, 5), "音效",
                     lambda: self.menu.push(self._audio_screen("sfx", "音效"))),
            UiButton(column_button_rect(4, 5), "退出游戏", self._quit),
        )
        return scr

    def _quit(self) -> None:
        self.running = False

    def _dual_screen(self) -> MenuScreen:
        """双人/三人模式页：PVP 纯 1v1 双人对战 或 三人混战（P3 鼠标）。"""
        scr = MenuScreen("dual", "多人模式", background=self._menu_bg)
        scr.add(
            UiButton(column_button_rect(0, 3), "双人对战（PVP）",
                     lambda: self._enter_mode_map("pvp")),
            UiButton(column_button_rect(1, 3), "三人混战（鼠标）",
                     lambda: self._enter_mode_map("pvp3")),
            UiButton(column_button_rect(2, 3), "返回", lambda: self.menu.pop()),
        )
        scr.on_draw = _draw_bottom_note(
            "双人 1v1 ｜ 三人混战：先胜 ⌈N/2⌉ 局者胜")
        return scr

    def _enter_mode_map(self, mode: str) -> None:
        """记录菜单入口模式并推入地图选择页（对局数页据此决定 start_pvp/start_pvp3）。"""
        self._menu_mode = mode
        self.menu.push(self._pvp_map_screen())

    def _pvp_map_screen(self) -> MenuScreen:
        """PVP 地图选择页：复用单人 1~4 关地图，按钮仅显示地图名 + 悬停预览卡。"""
        stages = self.level_manager.stages
        title = "双人对战 · 选择地图" if self._menu_mode != "pvp3" else "三人混战 · 选择地图"
        scr = MenuScreen("pvp_map", title, background=self._menu_bg)
        for i, st in enumerate(stages):
            name = st.get("meta", {}).get("name", f"地图 {i + 1}")
            scr.add(UiButton(
                column_button_rect(i, len(stages) + 2),
                name,
                lambda i=i: self._pick_pvp_map(i),
                preview_stage=i))
        scr.add(UiButton(
            column_button_rect(len(stages), len(stages) + 2),
            "随机地图",
            lambda: self._enter_pvp_random()))
        scr.add(UiButton(column_button_rect(len(stages) + 1, len(stages) + 2),
                        "返回", lambda: self.menu.pop()))
        if self._menu_mode == "pvp3":
            scr.on_draw = _draw_bottom_note(
                "玩家一: WASD+J ｜ 玩家二: 方向键+空格 ｜ 玩家三: 鼠标移动+左键开火")
        else:
            scr.on_draw = _draw_bottom_note("玩家一: WASD+J ｜ 玩家二: 方向键+空格")
        return scr

    def _pick_pvp_map(self, index: int) -> None:
        """选中地图 → 进入 PVP 对局数选择页。"""
        self.selected_stage = index
        self.menu.push(self._pvp_setup_screen())

    # ------------------------------------------------------------------
    # PVP 随机地图转盘（CSGO 开箱式开图动画）
    # ------------------------------------------------------------------
    def _enter_pvp_random(self) -> None:
        """推入随机开图页（PVP 版）并启动第一轮抽取。滚动期间无任何按钮。"""
        self._roulette_pick = self._pick_pvp_map
        scr = MenuScreen("pvp_random", "双人对战 · 随机地图", background=self._menu_bg)
        scr.buttons = []
        scr.on_draw = lambda s, f, m: self._draw_roulette(s, f, m)
        self.menu.push(scr)
        self._start_roulette()

    def _start_roulette(self) -> None:
        """开启/重摇一轮：抽目标图 + 随机时长，计算滚动终位，清空落定按钮。

        时长每次随机于 [PVP_ROULETTE_DURATION_MIN, PVP_ROULETTE_DURATION_MAX]，
        上限恒为 5 秒；落点由 _force_pvp_random 注入（测试用）或随机抽取。
        落点 = 整数卡位（保证中央槽指向 win）+ 卡内随机像素位置（保证指针
        稳稳落在选中卡内部、距边缘 ≥ PVP_ROULETTE_FINAL_INSET，绝不落缝）。
        float 小数残差直接计入 offset_end，由缓出曲线全程平滑滑入，无跳变。
        """
        win = self._force_pvp_random if self._force_pvp_random is not None \
            else random.randrange(len(self.level_manager.stages))
        duration = random.uniform(PVP_ROULETTE_DURATION_MIN, PVP_ROULETTE_DURATION_MAX)
        center = PVP_ROULETTE_SLOTS // 2          # 中央槽（选中位）
        n = len(self.level_manager.stages)
        end = PVP_ROULETTE_SPIN_CARDS
        # 收尾对齐：滚动到终点时中央槽 (center + end) % n == win
        end += (win - (center + end)) % n
        # 卡内随机落点：卡位整数对齐 + 卡内像素残差（扣除左右留白）
        cards = self._roulette_cards()
        card_w = cards[0].get_size()[0]
        step = card_w + PVP_ROULETTE_CARD_GAP
        inset_px = PVP_ROULETTE_FINAL_INSET
        residual_px = random.randint(inset_px, card_w - inset_px)
        offset_end = end + residual_px / step
        self._roulette_state = {
            "win": win,
            "duration": duration,
            "start_ticks": pygame.time.get_ticks(),
            "offset_start": 0,
            "offset_end": offset_end,
            "phase": "spin",
        }
        scr = self.menu.current
        if scr is not None and scr.id == "pvp_random":
            scr.buttons = []
            self._reset_menu_focus()

    def _roulette_cards(self) -> list:
        """构建并缓存 4 张统一尺寸的转盘卡（迷你图 + 地图名），懒构建一次。"""
        if self._roulette_cards_cache is not None:
            return self._roulette_cards_cache
        cell = PVP_ROULETTE_CELL
        mini_px = GRID_SIZE * cell
        if self._roulette_font is None:
            self._roulette_font = _create_font(PVP_ROULETTE_LABEL_SIZE, has_cjk=True)
        minis, labels = [], []
        for st in self.level_manager.stages:
            mini = pygame.Surface((mini_px, mini_px))
            if st.get("shape_fn"):
                # 连续几何关卡（Stage 5「戈壁环岛」）：按真实形状渲染后缩放，
                # 与战场同一套数据（MapRenderer + shape_fn）—— 圆弧沙洲 /
                # 真圆钢球 / LJR 水印，转盘卡即实战，不用方块近似。
                grid, deco = st["map_data"]()
                gm = GameMap.from_map_data(grid, deco)
                visual_fn = st.get("visual_fn")
                gm.visual_colors = visual_fn() if visual_fn else None
                deco_fn = st.get("deco_fn")
                gm.decorations = deco_fn() if deco_fn else None
                gm.shapes = st["shape_fn"]()
                geometry_fn = st.get("geometry_fn")
                gm.geometry = geometry_fn() if geometry_fn else None
                full = pygame.Surface((GRID_SIZE * TILE_SIZE,
                                       GRID_SIZE * TILE_SIZE))
                MapRenderer(gm).render(full)
                mini = pygame.transform.smoothscale(full, (mini_px, mini_px))
            else:
                # 老关卡（纯方块地图）：栅格迷你图，原样保留
                grid, _is_deco = st["map_data"]()
                for r in range(GRID_SIZE):
                    for c in range(GRID_SIZE):
                        v = grid[r][c]
                        color = PREVIEW_STEEL if v == TileType.STEEL else (
                            PREVIEW_BRICK if v == TileType.BRICK else PREVIEW_GROUND)
                        pygame.draw.rect(mini, color, (c * cell, r * cell, cell, cell))
            minis.append(mini)
            labels.append(self._roulette_font.render(
                st.get("meta", {}).get("name", ""), True, PREVIEW_LABEL_COLOR))
        # 统一卡宽：迷你图与最宽标签取大，避免 4 张卡宽度不一而成带时抖动
        pad = PREVIEW_CARD_PAD
        label_h = labels[0].get_height()
        w = max(mini_px, max(lt.get_width() for lt in labels)) + 2 * pad
        h = pad + mini_px + PREVIEW_LABEL_GAP + label_h + pad
        cards = []
        for mini, label in zip(minis, labels):
            card = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(card, PREVIEW_CARD_BG, (0, 0, w, h),
                             border_radius=PREVIEW_CARD_RADIUS)
            pygame.draw.rect(card, PREVIEW_CARD_BORDER, (0, 0, w, h), 2,
                             border_radius=PREVIEW_CARD_RADIUS)
            card.blit(mini, ((w - mini_px) // 2, pad))
            card.blit(label, label.get_rect(midtop=(w // 2, pad + mini_px + PREVIEW_LABEL_GAP)))
            cards.append(card)
        self._roulette_cards_cache = cards
        return cards

    def _draw_roulette(self, surface, font, menu) -> None:
        """开图页每帧绘制：卡带滚动（缓出减速）→ 落定弹结果按钮。"""
        st = self._roulette_state
        if st is None:
            return
        cards = self._roulette_cards()
        n = len(cards)
        card_w, card_h = cards[0].get_size()
        gap = PVP_ROULETTE_CARD_GAP
        step = card_w + gap
        center_x = SCREEN_WIDTH // 2
        c = PVP_ROULETTE_SLOTS // 2

        now = pygame.time.get_ticks()
        duration_ms = max(1.0, st["duration"] * 1000.0)
        p = max(0.0, min(1.0, (now - st["start_ticks"]) / duration_ms))
        e = _ease_out_cubic(p)
        offset = st["offset_start"] + (st["offset_end"] - st["offset_start"]) * e
        base = int(offset)
        frac = offset - base

        # 卡带行：位于标题（MENU_TITLE_Y=180）之下；中央槽 x 对准屏幕正中（箭头/判定线正上方）
        strip_y = PVP_ROULETTE_STRIP_Y
        for k in range(PVP_ROULETTE_SLOTS):
            idx = (base + k) % n
            x = center_x + (k - c) * step - int(frac * step)
            surface.blit(cards[idx], (x, strip_y))

        # 落定：仅弹结果按钮（一次）；不再画落定金框，判定以箭头/判定线为准
        if st["phase"] == "spin" and p >= 1.0:
            st["phase"] = "done"
            scr = menu.current
            if scr is not None and scr.id == "pvp_random":
                self._show_roulette_result_buttons(scr, st["win"])

        # 中央向上的三角形箭头（地图在箭头上方，尖端指向选中卡）
        ax, ay = center_x, strip_y + card_h + 16
        # CSGO 式判定线：灰色竖线从箭头尖端向上贯穿整条卡带（视觉指示；判定仍以中央槽数学为准）
        pygame.draw.line(surface, PVP_ROULETTE_LINE,
                         (ax, ay), (ax, strip_y - 8), 3)
        pygame.draw.polygon(surface, PVP_ROULETTE_ARROW,
                            [(ax, ay), (ax - 12, ay + 18), (ax + 12, ay + 18)])

        caption = "随机抽取中…" if st["phase"] == "spin" else \
            f"已选中 · {self.level_manager.stages[st['win']].get('meta', {}).get('name', '')}"
        if self._roulette_caption_font is None:
            self._roulette_caption_font = _create_font(
                PVP_ROULETTE_CAPTION_SIZE, has_cjk=True)
            self._roulette_caption_font.set_bold(True)   # 圆润加粗（微软雅黑粗体，效果同倒计时字）
        t = self._roulette_caption_font.render(caption, True, PREVIEW_LABEL_COLOR)
        # 文字上沿置于箭头底（ay+18）下方 8px，随字体高度自适应
        surface.blit(t, t.get_rect(center=(center_x, ay + 26 + t.get_height() // 2)))
        _draw_bottom_note("玩家一: WASD+J ｜ 玩家二: 方向键+空格")(surface, font, menu)

    def _show_roulette_result_buttons(self, scr, win: int) -> None:
        """落定后浮现结果按钮（底部横排）：就用这张图开局 / 重新随机 / 返回。

        「就用这张图开局」经 self._roulette_pick 分流：PVP → _pick_pvp_map（进局数页）。
        """
        labels = ["就用这张图开局", "重新随机", "返回"]
        actions = [
            lambda: self._roulette_pick(win),
            lambda: self._start_roulette(),
            lambda: self.menu.pop(),
        ]
        rects = self._row_button_rects(labels, PVP_ROULETTE_RESULT_Y)
        scr.buttons = [UiButton(r, lb, cb)
                       for r, lb, cb in zip(rects, labels, actions)]
        self._reset_menu_focus()

    def _row_button_rects(self, labels, y) -> list:
        """按文字宽自适应生成一行水平居中按钮矩形（开图页结果按钮专用）。"""
        pad, gap = 28, 20
        widths = [self.font.size(t)[0] + 2 * pad for t in labels]
        total = sum(widths) + gap * (len(labels) - 1)
        x = (SCREEN_WIDTH - total) // 2
        rects = []
        for w in widths:
            rects.append(pygame.Rect(x, y, w, MENU_BTN_H))
            x += w + gap
        return rects

    def _reset_menu_focus(self) -> None:
        """换按钮列后重置菜单焦点/悬停，避免旧索引越界。"""
        self.menu._focus = 0
        self.menu._hover = None
        self.menu._reset_preview()

    def _pvp_setup_screen(self) -> MenuScreen:
        """PVP 对局数选择页：5/7/9/11/13 局对应三局两胜至七局六胜。
        三人混战入口（_menu_mode=pvp3）时开局走 start_pvp3。"""
        name = self.level_manager.stages[self.selected_stage].get("meta", {}).get(
            "name", f"关卡 {self.selected_stage + 1}")
        mode_name = "三人混战" if self._menu_mode == "pvp3" else "双人对战"
        scr = MenuScreen("pvp_setup", f"{mode_name} · {name} · 选择对局数",
                         background=self._menu_bg)
        n = len(PVP_ROUNDS_CHOICES)
        labels = {5: "三局两胜", 7: "四局三胜", 9: "五局四胜",
                  11: "六局五胜", 13: "七局六胜"}

        def _start(r):
            if self._menu_mode == "pvp3":
                self.start_pvp3(r)
            else:
                self.start_pvp(r)

        for i, r in enumerate(PVP_ROUNDS_CHOICES):
            scr.add(UiButton(column_button_rect(i, n + 1),
                             f"打 {r} 局（{labels.get(r, '')}）",
                             lambda r=r: _start(r)))
        scr.add(UiButton(column_button_rect(n, n + 1), "返回", lambda: self.menu.pop()))
        if self._menu_mode == "pvp3":
            scr.on_draw = _draw_bottom_note(
                "玩家一: WASD+J ｜ 玩家二: 方向键+空格 ｜ 玩家三: 鼠标移动+左键开火")
        else:
            scr.on_draw = _draw_bottom_note("玩家一: WASD+J ｜ 玩家二: 方向键+空格")
        return scr

    # -- 游戏说明 --
    def _help_screen(self) -> MenuScreen:
        scr = MenuScreen("howto", "游戏说明", background=self._menu_bg)
        scr.add(UiButton(bottom_button_rect(), "返回", lambda: self.menu.pop()))
        scr.on_draw = _draw_help
        return scr

    # -- 音量 / 音效 --
    def _audio_screen(self, kind: str, title: str) -> MenuScreen:
        """kind: 'master'=主音量 / 'sfx'=音效音量。"""
        scr = MenuScreen(f"audio_{kind}", title, background=self._menu_bg)
        scr.add(
            UiButton(column_button_rect(0, 4), "＋ 增大",
                     lambda: self._adjust_volume(kind, MENU_VOLUME_STEP)),
            UiButton(column_button_rect(1, 4), "－ 减小",
                     lambda: self._adjust_volume(kind, -MENU_VOLUME_STEP)),
            UiButton(column_button_rect(2, 4), "静音开关",
                     lambda: self.audio.toggle_mute()),
            UiButton(column_button_rect(3, 4), "返回", lambda: self.menu.pop()),
        )
        scr.on_draw = _volume_value(self, kind)
        return scr

    def _adjust_volume(self, kind: str, delta: float) -> None:
        cur = self.audio.master if kind == "master" else self.audio.sfx
        newval = max(0.0, min(1.0, cur + delta))
        if kind == "master":
            self.audio.set_master(newval)
        else:
            self.audio.set_sfx(newval)

    def run(self):
        prev_state = None
        while self.running:
            self.handle_events()
            if self.state == GameState.PLAYING:
                self.update()
            # BGM 状态机（通过前后帧状态比较驱动，子页切换仍属 MENU 态不中断）：
            #  - 菜单乐仅在 MENU 态播放；离开菜单即停。
            #  - 战斗乐按关映射（STAGE_BGM_MAP）：单人/PvPvE 进对应关战斗时开播；
            #    离开战场（结算/回菜单）经 BGM_STOP_FADE 柔和淡出；从战斗直回菜单时
            #    淡出后无缝衔接菜单乐。
            if self.state != prev_state:
                if self.state == GameState.MENU:
                    # 从战斗直接回菜单（暂停页"主菜单"）：先让战斗乐淡出，再自动接播菜单乐
                    if prev_state in (GameState.PLAYING, GameState.PAUSED):
                        self.audio.stop_bgm(BGM_STOP_FADE, pending=SFX_BGM_MENU)
                    else:
                        self.audio.play_bgm(SFX_BGM_MENU)
                elif prev_state == GameState.MENU:
                    self.audio.stop_bgm()
                    # 命中关卡映射才开播（PVP 按所选地图播放对应战斗乐；
                    # 未配置战斗乐的关卡映射取不到键名自然不播）
                    bgm_key = STAGE_BGM_MAP.get(self.selected_stage)
                    if self.state == GameState.PLAYING and bgm_key is not None:
                        self.audio.play_bgm(bgm_key)
                elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                    # 战斗结束进入结算：柔和淡出（未在播战斗乐时安全无操作）
                    if prev_state in (GameState.PLAYING, GameState.PAUSED):
                        self.audio.stop_bgm(BGM_STOP_FADE)
                prev_state = self.state
            self.audio.update_bgm()
            self.render()
            self.clock.tick(FPS)
        # 退出前确保 BGM 停止
        self.audio.stop_bgm()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()