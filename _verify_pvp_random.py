# -*- coding: utf-8 -*-
"""PVP 随机地图转盘验证（headless，不改游戏逻辑）。

覆盖：
  1) 地图页含「随机地图」入口（4 图 + 随机 + 返回 = 6 按钮）
  2) 开图页：滚动中无按钮；状态含 win/duration/终位；时长 ∈ [MIN, MAX] 且 MAX=5
  3) 卡带：4 张统一尺寸卡可构建，卡带数学 (center+offset_end)%4 == win
  4) 落定：phase→done、浮现 3 结果按钮；【就用这张图开局】进局数页且标题带名
  5) 重摇：重新随机 → 回到滚动态、按钮清空、新落点生效
  6) 返回：pop 回地图页
  7) 无注入时随机性：win ∈ 0..3、时长恒 ≤ 5 秒
"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()

import main as M

game = M.Game()
STAGE_NAMES = [st.get("meta", {}).get("name") for st in game.level_manager.stages]
N = len(STAGE_NAMES)
SURF = pygame.Surface((M.SCREEN_WIDTH, M.SCREEN_HEIGHT))


def check(name, cond):
    assert cond, f"[FAIL] {name}"
    print(f"[PASS] {name}")


def finish_roulette():
    """把动画时间快进到超时并走完一帧绘制（等价播完）。"""
    st = game._roulette_state
    st["start_ticks"] = pygame.time.get_ticks() - int(st["duration"] * 1000) - 10
    game._draw_roulette(SURF, game.font, game.menu)


# 1) 地图页入口
scr = game._pvp_map_screen()
btns = scr.buttons
check("地图页 7 按钮（5 图 + 随机 + 返回）", len(btns) == 7)
check("第 6 个按钮为「随机地图」", btns[5].label == "随机地图")

# 2) 进入开图页：滚动中无按钮、状态就绪
game._force_pvp_random = 2
game._enter_pvp_random()
check("当前页为 pvp_random", game.menu.current.id == "pvp_random")
check("滚动期间无按钮", game.menu.current.buttons == [])
st = game._roulette_state
check("状态 phase=spin", st is not None and st["phase"] == "spin")
check("注入落点生效 win=2", st["win"] == 2)
check("时长 ∈ [MIN,MAX] 且 MAX 恒 5",
      M.PVP_ROULETTE_DURATION_MIN <= st["duration"] <= M.PVP_ROULETTE_DURATION_MAX == 5.0)
center = M.PVP_ROULETTE_SLOTS // 2
check("终位数学 (center+int(offset_end))%4 == win",
      (center + int(st["offset_end"])) % N == st["win"])
check("offset_end 为含卡内残差的 float（小数∈[0,1)）",
      isinstance(st["offset_end"], float)
      and 0.0 <= st["offset_end"] - int(st["offset_end"]) < 1.0)

# 3) 卡带构建：统一尺寸
cards = game._roulette_cards()
check("4 张转盘卡", len(cards) == N)
sizes = {c.get_size() for c in cards}
check("卡带尺寸统一", len(sizes) == 1)

# 4) 落定 → 结果按钮 → 就用这张图开局
finish_roulette()
scr = game.menu.current
check("落定后 phase=done", game._roulette_state["phase"] == "done")
check("浮现 3 个结果按钮", len(scr.buttons) == 3
      and scr.buttons[0].label == "就用这张图开局"
      and scr.buttons[1].label == "重新随机"
      and scr.buttons[2].label == "返回")
# 滚动中点击无按钮上报 → 需真达到落定才有按钮；此处验证按钮回调
scr.buttons[0].on_click()
check("开局 → 进局数页且记忆 selected_stage=2",
      game.menu.current.id == "pvp_setup" and game.selected_stage == 2)
check("局数页标题含地图名「军事攻坚」", "军事攻坚" in game.menu.current.title)

# 5) 重摇：回开图页 → 重新随机 → 滚动态 + 新落点
game._enter_pvp_random()
finish_roulette()
scr = game.menu.current
game._force_pvp_random = 0   # 换注入：第二次落点为 0
scr.buttons[1].on_click()    # 重新随机
st = game._roulette_state
check("重摇 → phase=spin 且按钮清空",
      st["phase"] == "spin" and game.menu.current.buttons == [])
check("重摇落点更新 win=0", st["win"] == 0)
finish_roulette()
check("重摇后再次落定", game._roulette_state["phase"] == "done")
scr = game.menu.current
scr.buttons[0].on_click()
check("重摇落点生效 selected_stage=0", game.selected_stage == 0)

# 6) 返回路径（真实链路）：地图页 → 开图页 → 落定 → 返回 → 回地图页
game.menu.reset_to_main()
game.menu.push(game._pvp_map_screen())   # [main, pvp_map]
game._enter_pvp_random()                  # [main, pvp_map, pvp_random]
finish_roulette()
game.menu.current.buttons[2].on_click()   # pop → pvp_map
check("返回 → 回 pvp_map 页", game.menu.current.id == "pvp_map")

# 7) 无注入随机性：次数抽样，win 越界即失败；时长恒上限 5 秒
game._force_pvp_random = None
for _ in range(50):
    st = game._roulette_state
    game._start_roulette()
    assert 0 <= st["win"] < N
    assert M.PVP_ROULETTE_DURATION_MIN <= st["duration"] <= M.PVP_ROULETTE_DURATION_MAX == 5.0

# 8) 布局核查：卡带下移不遮标题；各组件不与按钮/页脚/底部提示碰撞
game.menu.reset_to_main()
game.menu.push(game._pvp_map_screen())
game._enter_pvp_random()
finish_roulette()
result_btns = game.menu.current.buttons
strip_top = M.PVP_ROULETTE_STRIP_Y
strip_bottom = strip_top + cards[0].get_size()[1]
arrow_tip = strip_bottom + 16
caption_top = arrow_tip + 26   # 状态文字上沿（箭头底 ay+18 下方 8px）
btn_top, btn_bottom = M.PVP_ROULETTE_RESULT_Y, M.PVP_ROULETTE_RESULT_Y + M.MENU_BTN_H
check(f"卡带顶({strip_top}) ≥ 230（标题底≈215，不遮挡）", strip_top >= 230)
check(f"卡带底({strip_bottom}) < 结果按钮顶({btn_top})", strip_bottom < btn_top)
check(f"状态文字上沿({caption_top}) < 结果按钮顶({btn_top})", caption_top < btn_top)
check(f"按钮底({btn_bottom}) < 底部提示(688) 且 < 页脚(728)",
      btn_bottom < 688)
check("结果三按钮横排居中且等高",
      len({b.rect.top for b in result_btns}) == 1
      and result_btns[0].rect.left > 0
      and result_btns[-1].rect.right <= M.SCREEN_WIDTH)

# 9) UI 细节：判定线改灰、状态文字改黑粗圆体
check("判定线为中灰（R==G==B）且深于/区别于箭头深灰",
      M.PVP_ROULETTE_LINE[0] == M.PVP_ROULETTE_LINE[1] == M.PVP_ROULETTE_LINE[2]
      and M.PVP_ROULETTE_ARROW[0] == M.PVP_ROULETTE_ARROW[1] == M.PVP_ROULETTE_ARROW[2]
      and M.PVP_ROULETTE_LINE != M.PVP_ROULETTE_ARROW)
cfont = game._roulette_caption_font
check("状态文字字体已懒创建且加粗（雅黑粗体圆润效果）",
      cfont is not None and cfont.bold)
check("状态文字颜色为近黑（黑色系）",
      all(v <= 40 for v in M.PREVIEW_LABEL_COLOR))

# 10) 落缝检验：指针（判定线 center_x）必须稳定落在选中卡内部
#     （距卡片左右边缘均 ≥ PVP_ROULETTE_FINAL_INSET，绝不落缝/贴缝）
game.menu.reset_to_main()
game.menu.push(game._pvp_map_screen())
game._force_pvp_random = None  # 关闭注入，使用真随机
card_w = cards[0].get_size()[0]
step_px = card_w + M.PVP_ROULETTE_CARD_GAP
inset = M.PVP_ROULETTE_FINAL_INSET
residuals = set()
for i in range(20):
    game._start_roulette()
    st = game._roulette_state
    frac_final = st["offset_end"] - int(st["offset_end"])
    r_px = int(round(frac_final * step_px))  # 指针距选中卡左边缘的像素
    residuals.add(r_px)
    check(f"第{i+1}次指针距卡左缘 {r_px}px ∈ [{inset},{card_w-inset}]（不落缝）",
          inset <= r_px <= card_w - inset)
check("卡内落点随机且至少出现 2 种位置（不固定）", len(residuals) >= 2)

print("\nALL 随机地图转盘验证通过")