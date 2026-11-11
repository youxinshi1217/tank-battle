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

ok = True
W = 800; N = 9; step = (W / 2.0) / N
# 红闪（2P）：向右发散，取中右一条光柱（左缘爆亮、中右光柱清晰可见）
rx = int(round(0 + 7 * step))
g = Game(); g.start_pvp()
g._ui_flash_p1 = S.UI_AREA_FLASH_DURATION
g._render_ui_area()
r0 = sample(g, 5); r1 = sample(g, rx)
print("[红闪] 左缘=%s 中右光柱(x%d)=%s" % (r0, rx, r1))
ok = ok and (r0[0] > 150 and r1[0] > 80)

# 蓝闪（2P）：向左发散，src=799 取中左一条光柱
bx = int(round(799 - 7 * step))
g2 = Game(); g2.start_pvp()
g2._ui_flash_p2 = S.UI_AREA_FLASH_DURATION
g2._render_ui_area()
b0 = sample(g2, 795); b1 = sample(g2, bx)
print("[蓝闪] 右缘=%s 中左光柱(x%d)=%s" % (b0, bx, b1))
ok = ok and (b0[2] > 150 and b1[2] > 80)

# 绿闪（3P）：双向发散，取左右各一条光柱（k=5 → 距中线 222px）
gx = int(round(400 - 5 * step)); gy = 800 - gx
g3 = Game(); g3.start_pvp3()
g3._ui_flash_p3 = S.UI_AREA_FLASH_DURATION
g3._render_ui_area()
gl = sample(g3, gx); gr = sample(g3, gy)
print("[绿闪] 左光柱(x%d)=%s 右光柱(x%d)=%s" % (gx, gl, gy, gr))
ok = ok and (gl[1] > 80 and gr[1] > 80)

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
