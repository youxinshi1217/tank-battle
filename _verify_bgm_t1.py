# -*- coding: utf-8 -*-
"""第一关 BGM Task1 headless 验证：
1. 每曲参数（fadein/fadeout/target）随 register_bgm 生效
2. stop_bgm(fadeout) 淡出停止：音量渐降 -> 周期结束后真正停止
3. pending 机制：淡出结束后自动开播待播 BGM
4. 直接 stop_bgm(pending)（未在播）立即开播 pending
5. 回归：未传参数时回落菜单 BGM 默认值
"""
import os
import sys
import time

os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

from core.audio_manager import AudioManager
from core.settings import (
    SFX_BGM_MENU, SFX_BGM_MENU_PATH,
    SFX_BGM_STAGE1, SFX_BGM_STAGE1_PATH,
    BGM_MENU_FADEIN, BGM_MENU_TARGET_VOLUME,
    BGM_STAGE1_FADEIN, BGM_STAGE1_FADEOUT,
    BGM_STAGE1_TARGET_VOLUME,
)

SAVE = os.path.join(os.getcwd(), "_verify_audio_tmp.json")
FAIL = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAIL.append(name)


def main():
    am = AudioManager(save_path=SAVE)
    am.set_muted(False, persist=False)
    check("设备可用（dummy 驱动）", am._available)

    # 1. 每曲参数生效
    ok1 = am.register_bgm(SFX_BGM_MENU, SFX_BGM_MENU_PATH)
    ok2 = am.register_bgm(SFX_BGM_STAGE1, SFX_BGM_STAGE1_PATH,
                          fadein=BGM_STAGE1_FADEIN,
                          fadeout=BGM_STAGE1_FADEOUT,
                          target=BGM_STAGE1_TARGET_VOLUME)
    check("菜单/战斗 BGM 均注册成功", ok1 and ok2)
    check("meta 记录每曲参数",
          am._bgm_meta[SFX_BGM_STAGE1] == {"fadein": BGM_STAGE1_FADEIN,
                                           "fadeout": BGM_STAGE1_FADEOUT,
                                           "target": BGM_STAGE1_TARGET_VOLUME})

    # 2. 播放战斗乐 -> 参数接管
    am.play_bgm(SFX_BGM_STAGE1)
    check("战斗乐开播", am._bgm_playing and am._bgm_name == SFX_BGM_STAGE1)
    check("战斗乐参数接管 fadein/target",
          abs(am._bgm_fadein - BGM_STAGE1_FADEIN) < 1e-9
          and abs(am._bgm_target - BGM_STAGE1_TARGET_VOLUME) < 1e-9)
    am.update_bgm()
    time.sleep(0.05)
    am.update_bgm()
    check("播放中 channel busy", am._bgm_channel is not None
          and am._bgm_channel.get_busy())

    # 3. 淡出停止 + pending
    am.stop_bgm(fadeout=0.3, pending=SFX_BGM_MENU)
    check("淡出停止状态开启", am._bgm_stopping and am._bgm_pending == SFX_BGM_MENU)
    v_mid = None
    am.update_bgm()
    v_mid = am._bgm_channel.get_volume()
    check("淡出中音量 < 目标音量(>0)", 0.0 < v_mid < BGM_STAGE1_TARGET_VOLUME)
    # 模拟淡出周期结束
    am._bgm_stop_start -= 10.0
    am.update_bgm()
    check("淡出结束后战斗乐已切换（转播菜单乐）", not am._bgm_stopping
          and am._bgm_name == SFX_BGM_MENU and am._bgm_playing)
    check("pending 自动接播菜单乐", am._bgm_playing
          and am._bgm_name == SFX_BGM_MENU)
    check("淡出后接播未残留 stopping/pending",
          not am._bgm_stopping and am._bgm_pending is None)

    # 4. 未在播时直接 stop_bgm(pending)：立即开播 pending
    am.stop_bgm()  # 先彻底停掉
    am.stop_bgm(fadeout=3.0, pending=SFX_BGM_STAGE1)
    check("未在播时直接停止并立即开播 pending",
          am._bgm_playing and am._bgm_name == SFX_BGM_STAGE1
          and not am._bgm_stopping)

    # 5. 回归：菜单 BGM 未传参数时为默认值
    am.stop_bgm()
    am.play_bgm(SFX_BGM_MENU)
    check("菜单 BGM 回落默认 fadein/target",
          abs(am._bgm_fadein - BGM_MENU_FADEIN) < 1e-9
          and abs(am._bgm_target - BGM_MENU_TARGET_VOLUME) < 1e-9)

    am.stop_bgm()
    print("\n" + ("ALL PASS" if not FAIL else f"FAILED: {FAIL}"))
    sys.exit(0 if not FAIL else 1)


if __name__ == "__main__":
    main()