# -*- coding: utf-8 -*-
"""
Phase UI 第一步 - AudioManager（音频管理：音量 / 音效 / 静音 + 持久化）

职责：
  - 持有全局「主音量 master」与「音效音量 sfx」两条音量轨，及静音开关。
  - 播放命名音效（键名 -> Sound）。音量 = master * sfx，静音时静默。
  - 音量 / 静音状态持久化到 save/audio.json，重启后恢复。

音效来源（两级回退）：
  1. 从 SFX_DIR 加载 <name>.wav；存在则用真实文件。
  2. 文件缺失时，为 click 生成一段程序化「点击音」，保证音量反馈立即可用。

不负责：
  - BGM 音乐播放由本模块 BGM 子系统负责（受控循环 + 首尾淡入淡出，自然衔接）。
  - 任何游戏逻辑 / 战斗音效触发。

兼容性：
  - 无音频设备 / mixer 初始化失败时进入 no-op 安全模式，不抛异常。
"""

import array
import json
import math
import os
import time

import pygame

from core.settings import (
    AUDIO_FILE,
    SFX_DIR,
    SFX_NAME_CLICK,
    VOLUME_MAX,
    VOLUME_MIN,
    SFX_BGM_MENU,
    BGM_MENU_FADEIN,
    BGM_MENU_FADEOUT,
    BGM_MENU_TARGET_VOLUME,
)


def _generate_click_sound():
    """程序化生成一段柔和的短促「点击音」（正弦 + 线性衰减，双声道 16bit）。

    无真实 wav 时作为音量反馈，权重很小、不吵。频率 880Hz、时长 40ms。
    """
    sr = 22050
    freq = 880.0
    ms = 40
    n = int(sr * ms / 1000.0)
    amp = 6000  # 小音量防护
    buf = array.array("h")
    for i in range(n):
        t = i / sr
        decay = 1.0 - (i / n)          # 线性淡出，避免爆音
        val = int(amp * math.sin(2 * math.pi * freq * t) * decay)
        buf.append(val)                # 左声道
        buf.append(val)                # 右声道
    return pygame.mixer.Sound(buffer=buf.tobytes())


class AudioManager:
    """音量 / 音效 / 静音管理。单例由 main.Game 持有。"""

    def __init__(self, save_path: str = None):
        save_path = save_path or AUDIO_FILE
        self._save_path = save_path
        self._master = 1.0
        self._sfx = 1.0
        self._muted = False
        self._sounds = {}       # 音效键名 -> pygame.mixer.Sound
        self._available = False  # 音频设备是否可用

        # ---- BGM 子系统状态 ----
        self._bgm = {}           # BGM 键名 -> pygame.mixer.Sound
        self._bgm_meta = {}      # BGM 键名 -> {fadein, fadeout, target}（每曲参数）
        self._bgm_channel = None     # 专用 channel（None 表示未分配）
        self._bgm_name = None        # 当前播放的 BGM 键名
        self._bgm_playing = False    # 是否在播放（受控循环进行中）
        self._bgm_start = 0.0        # 本段开始播放的时钟（time.time，秒）
        self._bgm_length = 0.0       # 当前 BGM 时长（秒）
        self._bgm_state = "idle"     # idle / fadein / sustain / fadeout
        self._bgm_fadein = BGM_MENU_FADEIN
        self._bgm_fadeout = BGM_MENU_FADEOUT
        self._bgm_target = BGM_MENU_TARGET_VOLUME
        # 淡出停止（stop_bgm(fadeout>0)）：音量从当前逐渐归零后再真正停止，
        # 期间保持播放、跳过循环逻辑；结束后若有待播 BGM（pending）则自动开播。
        self._bgm_stopping = False   # 是否处于淡出停止中
        self._bgm_stop_start = 0.0   # 淡出停止开始的时钟
        self._bgm_stop_fade = 0.0    # 淡出停止总时长（秒）
        self._bgm_pending = None     # 淡出结束后待开播的 BGM 键名

        self._init_mixer()
        self._load_named_sounds(SFX_DIR)
        self.load()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def _init_mixer(self) -> None:
        """初始化 mixer。失败（无设备）则进入 no-op 安全模式。"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            # 若已初始化且参数不同，按需重置，保证与程序化音格式一致
            if pygame.mixer.get_init() != (22050, -16, 2):
                pygame.mixer.quit()
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._available = pygame.mixer.get_init() is not None
        except pygame.error:
            self._available = False

    def _load_named_sounds(self, sfx_dir: str) -> None:
        """加载 SFX_DIR 下的 <name>.wav；click 缺失时回退到程序化点击音。"""
        click_path = os.path.join(sfx_dir, f"{SFX_NAME_CLICK}.wav")
        if os.path.exists(click_path):
            self._sounds[SFX_NAME_CLICK] = pygame.mixer.Sound(click_path)
        elif self._available:
            try:
                self._sounds[SFX_NAME_CLICK] = _generate_click_sound()
            except pygame.error:
                pass

    def register_sound(self, name: str, path: str) -> bool:
        """加载指定文件作为命名音效（支持 wav/ogg/mp3 等 pygame 兼容格式）。

        成功返回 True；无音频设备 / 文件缺失 / 解码失败时返回 False 且不抛异常。
        用于接入用户提供的外部音效资源（如开炮声）。
        """
        if not self._available:
            return False
        if not os.path.exists(path):
            return False
        try:
            self._sounds[name] = pygame.mixer.Sound(path)
            return True
        except pygame.error:
            return False

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def load(self) -> None:
        """从 save/audio.json 恢复音量与静音。文件缺失 / 损坏则用默认。"""
        try:
            with open(self._save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._master = self._clamp(data.get("master", 1.0))
            self._sfx = self._clamp(data.get("sfx", 1.0))
            self._muted = bool(data.get("muted", False))
        except (OSError, ValueError, TypeError):
            pass

    def save(self) -> None:
        """持久化当前音量 / 静音设置。"""
        try:
            os.makedirs(os.path.dirname(self._save_path) or ".", exist_ok=True)
            with open(self._save_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "master": round(self._master, 3),
                        "sfx": round(self._sfx, 3),
                        "muted": self._muted,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError:
            pass

    # ------------------------------------------------------------------
    # 音量读写
    # ------------------------------------------------------------------
    @staticmethod
    def _clamp(v):
        return max(VOLUME_MIN, min(VOLUME_MAX, float(v)))

    @property
    def master(self) -> float:
        """主音量（0~1）。"""
        return self._master

    @property
    def sfx(self) -> float:
        """音效音量（0~1）。"""
        return self._sfx

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def effective(self) -> float:
        """实际生效音量（主音量 × 音效音量 × 静音开关）。"""
        return self._master * self._sfx * (0.0 if self._muted else 1.0)

    def set_master(self, volume: float, persist: bool = True) -> None:
        """设置主音量，持久化。"""
        self._master = self._clamp(volume)
        if persist:
            self.save()

    def set_sfx(self, volume: float, persist: bool = True) -> None:
        """设置音效音量，持久化。"""
        self._sfx = self._clamp(volume)
        if persist:
            self.save()

    def toggle_mute(self, persist: bool = True) -> bool:
        """切换静音状态，返回切换后的静音标志。"""
        self._muted = not self._muted
        if persist:
            self.save()
        return self._muted

    def set_muted(self, muted: bool, persist: bool = True) -> None:
        self._muted = bool(muted)
        if persist:
            self.save()

    # ------------------------------------------------------------------
    # 播放
    # ------------------------------------------------------------------
    def play(self, name: str, volume_scale: float = 1.0):
        """播放命名音效。无设备 / 静音 / 未加载时安全跳过。

        Args:
            name:          音效键名（register_sound / 预置命名音效）。
            volume_scale:  额外音量缩放（0~1，默认 1.0）。用于把某些音效压低，
                           例如拾取音效保持"能听见即可"的小音量。最终音量
                           = effective × volume_scale，并钳制在 [0, 1]。

        Returns:
            正在播放该音效的 pygame.mixer.Channel（调用方可据此 fadeout/stop）；
            静音 / 无设备 / 未加载时返回 None。
        """
        if not self._available or self._muted:
            return None
        sound = self._sounds.get(name)
        if sound is None:
            return None
        vol = max(0.0, min(1.0, self.effective * float(volume_scale)))
        sound.set_volume(vol)
        return sound.play()

    def ensure_channels(self, channels: int) -> None:
        """扩容 mixer 播放通道数（多发导弹音效并发时防抢通道）。
        无音频设备时安全跳过；已初始化才生效。"""
        if not self._available:
            return
        try:
            current = pygame.mixer.get_num_channels()
            if current < channels:
                pygame.mixer.set_num_channels(channels)
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # BGM 子系统（大厅主菜单背景音乐：受控循环 + 首尾淡入淡出）
    # ------------------------------------------------------------------
    def register_bgm(self, name: str, path: str, fadein: float = None,
                     fadeout: float = None, target: float = None) -> bool:
        """加载指定文件作为 BGM（支持 ogg/mp3/wav）。成功返回 True；失败安全返回 False。

        可选 fadein/fadeout/target 为每曲专属参数（淡入/循环尾淡出/目标音量），
        不传时回落菜单 BGM 默认值，不影响现有主菜单音乐注册。
        """
        if not self._available:
            return False
        if not os.path.exists(path):
            return False
        try:
            sound = pygame.mixer.Sound(path)
            self._bgm[name] = sound
            self._bgm_meta[name] = {
                "fadein": fadein, "fadeout": fadeout, "target": target,
            }
            return True
        except pygame.error:
            return False

    def _bgm_effective_volume(self) -> float:
        """BGM 实际音量 = 主音量 × 目标音量 × 静音开关，钳制 [0, 1]。"""
        if self._muted:
            return 0.0
        return max(0.0, min(1.0, self._master * self._bgm_target))

    def play_bgm(self, name: str) -> None:
        """开始播放 BGM（受控循环）。无设备 / 未加载 / 静音时安全跳过。

        采用受控循环：每段 = 头 fadein 秒淡入 → 中段稳音量 → 尾 fadeout 秒淡出，
        淡出结束后从开头重新播放，循环时首尾音量都为 0，过渡自然。
        播放前先应用该曲专属参数（register_bgm 传入）；若已有淡出停止进行中则取消。
        """
        if not self._available or self._muted:
            return
        sound = self._bgm.get(name)
        if sound is None:
            return
        # 新 BGM 直接接管：取消进行中的淡出停止与待播队列
        self._bgm_stopping = False
        self._bgm_pending = None
        # 已在播放同一 BGM 则不重复触发
        if self._bgm_playing and self._bgm_name == name:
            return
        # 应用该曲专属参数：未提供项的回落默认值（菜单 BGM 传 None 即复位默认音量）
        meta = self._bgm_meta.get(name)
        if meta is not None:
            self._bgm_fadein = meta["fadein"] if meta["fadein"] is not None else BGM_MENU_FADEIN
            self._bgm_fadeout = meta["fadeout"] if meta["fadeout"] is not None else BGM_MENU_FADEOUT
            self._bgm_target = meta["target"] if meta["target"] is not None else BGM_MENU_TARGET_VOLUME
        # 分配专用 channel（避免与音效抢占）
        if self._bgm_channel is None or not self._bgm_channel.get_busy():
            self._bgm_channel = pygame.mixer.Channel(0)
        self._bgm_name = name
        self._bgm_length = sound.get_length()
        # 起始即从头淡入（音量 0 → target）
        self._bgm_channel.play(sound)
        self._bgm_channel.set_volume(0.0)
        self._bgm_start = time.time()
        self._bgm_playing = True
        self._bgm_state = "fadein"

    def stop_bgm(self, fadeout: float = 0.0, pending: str = None) -> None:
        """停止 BGM。安全可重复调用。

        Args:
            fadeout:  >0 时先柔和淡出（保持播放、音量渐降归零）再真正停止；
                      0 则立即停止（原行为）。
            pending:  淡出结束后自动开播的 BGM 键名（用于"战斗乐淡出后无
                      缝衔接菜单乐"）。立即停止时若有 pending 直接开播。
        """
        if fadeout > 0.0 and self._bgm_playing:
            self._bgm_stopping = True
            self._bgm_stop_start = time.time()
            self._bgm_stop_fade = fadeout
            self._bgm_pending = pending
            return
        # 立即停止：清除状态（含未完成的淡出与待播队列）
        self._bgm_playing = False
        self._bgm_state = "idle"
        self._bgm_name = None
        self._bgm_stopping = False
        self._bgm_pending = None
        if self._bgm_channel is not None:
            try:
                self._bgm_channel.stop()
            except pygame.error:
                pass
        if pending is not None and self._available:
            self.play_bgm(pending)

    def update_bgm(self) -> None:
        """每帧驱动 BGM 状态机：淡入 / 稳音 / 淡出 / 自然重播。

        由主循环每帧调用（菜单态与战斗态都要调用，保证淡出/重播轮询持续）。
        无设备 / 未播放时直接返回。
        """
        if not self._available or not self._bgm_playing or self._bgm_channel is None:
            return
        # 静音切换时实时静默
        if self._muted:
            self._bgm_channel.set_volume(0.0)
            return
        # ---- 淡出停止：音量渐降，结束后真正停止并接播 pending ----
        if self._bgm_stopping:
            elapsed = time.time() - self._bgm_stop_start
            fade = max(0.01, self._bgm_stop_fade)
            if elapsed >= fade:
                self._bgm_channel.set_volume(0.0)
                if self._bgm_channel.get_busy():
                    self._bgm_channel.stop()
                self._bgm_playing = False
                self._bgm_state = "idle"
                self._bgm_name = None
                self._bgm_stopping = False
                pending, self._bgm_pending = self._bgm_pending, None
                if pending is not None:
                    self.play_bgm(pending)
            else:
                vol = self._bgm_effective_volume() * (1.0 - elapsed / fade)
                self._bgm_channel.set_volume(max(0.0, min(1.0, vol)))
            return
        # 若 channel 已空闲（播放意外结束），立即重新触发循环段
        if not self._bgm_channel.get_busy():
            self._restart_bgm_segment()
            return

        elapsed = time.time() - self._bgm_start
        target = self._bgm_effective_volume()
        fadein = max(0.01, self._bgm_fadein)
        fadeout = max(0.01, self._bgm_fadeout)
        length = max(fadein + fadeout, self._bgm_length)

        if elapsed < fadein:
            # 头：0 → target 线性淡入
            vol = target * (elapsed / fadein)
            self._bgm_state = "fadein"
        elif elapsed > length - fadeout:
            # 尾：target → 0 线性淡出（最后 fadeout 秒）
            remain = length - elapsed
            vol = target * max(0.0, remain / fadeout)
            self._bgm_state = "fadeout"
            # 淡出窗口结束 -> 自然重播下一段（首尾都为 0，无缝）
            if remain <= 0.0:
                self._restart_bgm_segment()
                return
        else:
            # 中段：稳音量
            vol = target
            self._bgm_state = "sustain"
        self._bgm_channel.set_volume(max(0.0, min(1.0, vol)))

    def _restart_bgm_segment(self) -> None:
        """从开头重新播放当前 BGM 段（用于淡出结束后的自然循环）。"""
        sound = self._bgm.get(self._bgm_name)
        if sound is None:
            self._bgm_playing = False
            return
        if self._bgm_channel is None:
            self._bgm_channel = pygame.mixer.Channel(0)
        self._bgm_channel.play(sound)
        self._bgm_channel.set_volume(0.0)
        self._bgm_start = time.time()
        self._bgm_state = "fadein"