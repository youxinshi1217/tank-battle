import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame, math
sys.path.insert(0, r"C:/Users/32857/Desktop/新建文件夹/坦克大战/tank_game")
from main import Game
import core.settings as S

pygame.init()
g = Game()
g.start_pvp(5)

def scan_edges():
    """返回 (红区峰值RGB, 蓝区峰值RGB)，取状态栏中行采样。

    档位 C：红锚左缘(峰值在左边缘)、蓝锚右缘(峰值在右边缘)，各自向中心化开、半宽 w/2。
    故采样点取近边缘处（红 x≈w/20、蓝 x≈19w/20）才能采到各色最亮峰值，断言最稳。
    """
    g._render_ui_area()
    r = g._ui_area_rect()
    x_red, x_blue = r.x + r.width // 20, r.x + 19 * r.width // 20
    y = r.y + r.height // 2
    return g.screen.get_at((x_red, y))[:3], g.screen.get_at((x_blue, y))[:3]

# 基线：无闪光（两计时器清零）
g._ui_flash_p1 = 0.0
g._ui_flash_p2 = 0.0
base_l, base_r = scan_edges()

# ---- 测试1：受害者=P1(红) -> 赢家=P2(蓝) -> 应闪右(蓝)侧 ----
g._ui_flash_p1 = 0.0
g._ui_flash_p2 = 0.0
g._pvp_destroyed = {g.player_tank: "p2"}
g._settle_pvp()
f1, f2 = g._ui_flash_p1, g._ui_flash_p2
L, R = scan_edges()
print("[测试1] 受害=P1红(蓝方胜)  计时器 flash_p1=%.3f flash_p2=%.3f" % (f1, f2))
print("        红区中心RGB=%s 蓝区中心RGB=%s" % (str(L), str(R)))
print("        基线右蓝=%d 现在右蓝=%d  基线左红=%d 现在左红=%d" % (base_r[2], R[2], base_l[0], L[0]))
assert f2 > 0 and f1 == 0, "FAIL 计时器: 赢家侧应为 p2"
assert R[2] > base_r[2] * 1.12, "FAIL 渲染: 右(蓝/赢家)蓝色通道应被显著提亮"
print("        => 通过：蓝方胜时右蓝侧闪亮\n")

# ---- 测试2：受害者=P2(蓝) -> 赢家=P1(红) -> 应闪左(红)侧 ----
# 复位上一次结算的局锁定（否则 _settle_pvp 走"已锁定"分支直接 return）
g._round_locked = False
g._ui_flash_p1 = 0.0
g._ui_flash_p2 = 0.0
g._pvp_destroyed = {g.player2_tank: "p1"}
g._settle_pvp()
f1, f2 = g._ui_flash_p1, g._ui_flash_p2
L, R = scan_edges()
print("[测试2] 受害=P2蓝(红方胜)  计时器 flash_p1=%.3f flash_p2=%.3f" % (f1, f2))
print("        红区中心RGB=%s 蓝区中心RGB=%s" % (str(L), str(R)))
print("        基线左红=%d 现在左红=%d  基线右蓝=%d 现在右蓝=%d" % (base_l[0], L[0], base_r[2], R[2]))
assert f1 > 0 and f2 == 0, "FAIL 计时器: 赢家侧应为 p1"
assert L[0] > base_l[0] * 1.12, "FAIL 渲染: 左(红/赢家)红色通道应被显著提亮"
print("        => 通过：红方胜时左红侧闪亮\n")

# ---- 测试3：衰减确认（闪一下后 update 应逐步归零；时长由 UI_AREA_FLASH_DURATION 控制）----
# update() 内部 dt 取自 self.clock.get_time()；测试里没调 clock.tick() 故 dt 恒 0。
# 用虚拟时钟固定每帧 16ms（=real 60fps 一帧）推进，确认衰减到 0 的帧数≈DURATION/0.016。
import types
class FakeClock:
    def get_time(self): return 16.0
    def tick(self, *a): return 16.0
g.clock = FakeClock()
g._round_locked = False
g._ui_flash_p2 = 0.0
g._ui_flash_p1 = S.UI_AREA_FLASH_DURATION
start = g._ui_flash_p1
frames = 0
while g._ui_flash_p1 > 0 and frames < 200:
    g.update()
    frames += 1
elapsed = frames * 0.016
print("[测试3] flash_p1=%.3f -> 归零，共 %d 帧 ≈ %.2f 秒" % (start, frames, elapsed))
exp_frames = int(round(S.UI_AREA_FLASH_DURATION / 0.016))
assert g._ui_flash_p1 == 0 and abs(frames - exp_frames) <= 3, \
    "FAIL 闪光应约 %s s(%d 帧) 衰减到 0，实际 %d 帧" % (S.UI_AREA_FLASH_DURATION, exp_frames, frames)
print("        => 通过：闪光峰值 %s s 后逐步衰减归零，落在慢动作爆炸窗口内\n" % S.UI_AREA_FLASH_DURATION)

print("ALL PASS：命中闪光已改为【赢家侧】，且亮度/时长达标。")
