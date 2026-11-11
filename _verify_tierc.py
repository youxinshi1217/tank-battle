import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import core.settings as S
from main import Game, GameState

def sample(g, x):
    r = g._ui_area_rect()
    y = r.y + r.height // 2
    return g.screen.get_at((x, y))[:3]

class FakeClock:
    def get_time(self): return 16.0
    def tick(self, fps=60): return 16

ok = True

# 1) 常量确认（DURATION 跟随实际值，不强等于 0.32）
print("[常量] DURATION=%.2f BOOST=%d RELOAD_BOOST=%d" %
      (S.UI_AREA_FLASH_DURATION, S.UI_AREA_FLASH_BOOST, S.UI_AREA_RELOAD_BOOST))
ok = ok and S.UI_AREA_FLASH_DURATION > 0.3 and S.UI_AREA_FLASH_BOOST == 150 \
        and S.UI_AREA_RELOAD_BOOST == 38

# 2) 发散光线已删干净（_owner_of_tank 仍保留、被 _settle_pvp 使用，不应删）
ok = ok and not hasattr(Game, "_draw_diverge_rays") \
        and hasattr(Game, "_owner_of_tank") and not hasattr(Game, "_trigger_kill_flashes")
print("[清理] _draw_diverge_rays/_trigger_kill_flashes 已移除、_owner_of_tank 保留：%s"
      % (not hasattr(Game, "_draw_diverge_rays") and hasattr(Game, "_owner_of_tank")))
ok = ok and hasattr(Game, "_flash_side")
print("[新增] _flash_side 存在：%s" % hasattr(Game, "_flash_side"))

# 3) 红方被害 -> 蓝(右)侧闪（赢家蓝应显著提亮；输家红保持稳态不被提亮）
g = Game(); g.start_pvp()
g._round_locked = False
g._ui_flash_p1 = g._ui_flash_p2 = 0.0
g._render_ui_area()
base_rl = sample(g, 200); base_rr = sample(g, 600)   # 结算前基线（稳态）
g._pvp_destroyed = {g.player_tank: "p2"}
g._settle_pvp()
g._render_ui_area()
rr = sample(g, 600); rl = sample(g, 200)
print("[红被害->蓝胜] 左红=%s(基线%s) 右蓝=%s(基线%s)" % (rl, base_rl, rr, base_rr))
ok = ok and (g._ui_flash_p2 > 0 and g._ui_flash_p1 == 0
             and rr[2] > base_rr[2] * 1.12        # 赢家(蓝)侧显著提亮
             and abs(rl[0] - base_rl[0]) < 30)     # 输家(红)侧保持稳态、未提亮

# 4) 蓝方被害 -> 红(左)侧闪（赢家红应显著提亮；输家蓝保持稳态不被提亮）
g2 = Game(); g2.start_pvp()
g2._round_locked = False
g2._ui_flash_p1 = g2._ui_flash_p2 = 0.0
g2._render_ui_area()
base_2l = sample(g2, 200); base_2r = sample(g2, 600)
g2._pvp_destroyed = {g2.player2_tank: "p1"}
g2._settle_pvp()
g2._render_ui_area()
l2 = sample(g2, 200); r2 = sample(g2, 600)
print("[蓝被害->红胜] 左红=%s(基线%s) 右蓝=%s(基线%s)" % (l2, base_2l, r2, base_2r))
ok = ok and (g2._ui_flash_p1 > 0 and g2._ui_flash_p2 == 0
             and l2[0] > base_2l[0] * 1.12        # 赢家(红)侧显著提亮
             and abs(r2[2] - base_2r[2]) < 30)     # 输家(蓝)侧保持稳态、未提亮

# 5) 互毁 -> 双方都闪
g3 = Game(); g3.start_pvp()
g3._round_locked = False
g3._ui_flash_p1 = g3._ui_flash_p2 = 0.0
g3._pvp_destroyed = {g3.player_tank: "p2", g3.player2_tank: "p1"}
g3._settle_pvp()
print("[互毁] p1=%s p2=%s" % (g3._ui_flash_p1, g3._ui_flash_p2))
ok = ok and (g3._ui_flash_p1 > 0 and g3._ui_flash_p2 > 0)

# 6) 3P：最后存活者(绿)胜 -> 中绿闪（需把死者登记进 _dead_players，与实战一致）
g4 = Game(); g4.start_pvp3()
g4._round_locked = False
g4._ui_flash_p1 = g4._ui_flash_p2 = g4._ui_flash_p3 = 0.0
g4._dead_players.update([g4.player_tank, g4.player2_tank])
g4._pvp_destroyed = {g4.player_tank: "p3", g4.player2_tank: "p3"}
g4._settle_pvp()
g4._render_ui_area()
gc = sample(g4, 400); gs = sample(g4, 200)
print("[3P 绿胜] p3=%s p1=%s p2=%s 中绿=%s 左(x200,蓝应低)=%s" %
      (g4._ui_flash_p3, g4._ui_flash_p1, g4._ui_flash_p2, gc, gs))
ok = ok and (g4._ui_flash_p3 > 0 and g4._ui_flash_p1 == 0 and g4._ui_flash_p2 == 0
             and gc[1] > 60 and gs[2] < 60)

# 7) 衰减归零（时长跟随 UI_AREA_FLASH_DURATION）
g.clock = FakeClock()
frames = 0
while g._ui_flash_p2 > 0 and frames < 200:
    g.update(); frames += 1
elapsed = frames * 16.0 / 1000.0
print("[衰减] flash_p2 归零用 %.3f 秒 (%d 帧)" % (elapsed, frames))
ok = ok and abs(elapsed - S.UI_AREA_FLASH_DURATION) < 0.05

# 8) 渲染不崩（含 pvp / pvp3 / 结算态）
g2.state = GameState.GAME_OVER; g2._render_ui_area()
g4.state = GameState.VICTORY; g4._render_ui_area()
print("[渲染] GAME_OVER / VICTORY 状态栏渲染无异常")

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
