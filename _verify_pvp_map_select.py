# -*- coding: utf-8 -*-
"""PVP 地图选择页验证（headless，不改任何游戏逻辑）。

覆盖：
  1) PVP 入口改为先进地图页：_pvp_map_screen 构建 4 个地图按钮 + 返回
  2) 按钮仅显示地图名，且全部绑定 preview_stage（悬停预览卡）
  3) _pick_pvp_map 记忆 selected_stage 并推入局数页；局数页标题带地图名
  4) start_pvp 使用选中的地图（含非首关），系列赛期间不再跳图
  5) 回归：不选图时 selected_stage 默认 0，start_pvp 行为与改造前一致
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M
from ui.menu import MenuSystem, MenuScreen

game = M.Game()
STAGE_NAMES = [st.get("meta", {}).get("name") for st in game.level_manager.stages]
assert len(STAGE_NAMES) == 5, f"应有 5 关，实际 {len(STAGE_NAMES)}"


def check(name, cond):
    assert cond, f"[FAIL] {name}"
    print(f"[PASS] {name}")


# 1) 地图页构建：4 地图按钮 + 1 返回，按钮文本仅地图名
scr = game._pvp_map_screen()
check("地图页标题为「双人对战 · 选择地图」",
      scr.title == "双人对战 · 选择地图")
btns = scr.buttons
check("5 个地图按钮 + 随机 + 返回 = 7 按钮", len(btns) == 7)
for i, st_name in enumerate(STAGE_NAMES):
    check(f"按钮{i}文本=地图名「{st_name}」（不带第N关）", btns[i].label == st_name)
    check(f"按钮{i}绑定 preview_stage={i}", btns[i].preview_stage == i)
check("第 6 个按钮为「随机地图」", btns[5].label == "随机地图")
check("末位按钮为「返回」", btns[-1].label == "返回")
check("地图页带双人操作提示 on_draw", scr.on_draw is not None)

# 2) 预览卡懒渲染可用（悬停第 3 关按钮）
card = game._preview_card(2)
check("第 3 关预览卡可渲染", card is not None)
check("预览卡缓存命中", game._preview_card(2) is card)

# 3) 选图 → 局数页：selected_stage 记忆 + 标题带地图名
via_menu = MenuSystem(game.audio, preview_loader=game._preview_card)
via_menu.push(game._pvp_map_screen())
via_menu.push(game._pvp_setup_screen())
check("直接进局数页时 selected_stage 未设置→走默认第 1 关",
      "钢铁废墟" in via_menu.current.title)
game._pick_pvp_map(2)   # 选中第 3 关「军事攻坚」
check("_pick_pvp_map 记忆 selected_stage=2", game.selected_stage == 2)
scr2 = game._pvp_setup_screen()
check("局数页标题含地图名「军事攻坚」", "军事攻坚" in scr2.title)

# 4) start_pvp 用选中地图：current_stage 即第 3 关，系列赛内不跳图
game.start_pvp(rounds=7)
check("start_pvp 载入第 3 关地图", game.selected_stage == 2)
check("level_manager 当前关为第 3 关",
      game.level_manager.stages.index(game.level_manager.current_stage) == 2)
check("局制 7/4 生效",
      game.round_manager.rounds_total == 7 and game.round_manager.win_needed == 4)
game._start_round()
check("第二局仍为第 3 关（系列赛不跳图）",
      game.level_manager.stages.index(game.level_manager.current_stage) == 2)
check("P2 恒在场", game.player2_tank is not None)
check("无波次敌人（PVP 硬门控）",
      game.match_mode == "pvp" and len(game.enemy_tanks) == 0)

# 5) 回归：默认 selected_stage=0 走首关，与改造前行为一致
g2 = M.Game()
g2.start_pvp(rounds=5)
check("默认 selected_stage=0 载入首关",
      g2.selected_stage == 0
      and g2.level_manager.stages.index(g2.level_manager.current_stage) == 0
      and g2.round_manager.rounds_total == 5
      and g2.player2_tank is not None)

print("\nALL PVP 地图选择验证通过")