import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
import core.settings as S
from main import Game

def sample(g, x, y=None):
    r = g._ui_area_rect()
    yy = r.y + (r.height // 2 if y is None else y)
    return g.screen.get_at((x, yy))[:3]

ok = True
g = Game(); g.start_pvp(); g._ui_flash_p1 = S.UI_AREA_FLASH_DURATION; g._render_ui_area()
r0 = sample(g, 2); rmid = sample(g, 200)
print("[红闪] 左缘=%s 中右(x200)=%s" % (r0, rmid))
ok = ok and (r0[0] > 150 and rmid[0] > 60)

g2 = Game(); g2.start_pvp(); g2._ui_flash_p2 = S.UI_AREA_FLASH_DURATION; g2._render_ui_area()
b0 = sample(g2, 798); bmid = sample(g2, 600)
print("[蓝闪] 右缘=%s 中左(x600)=%s" % (b0, bmid))
ok = ok and (b0[2] > 150 and bmid[2] > 60)

g3 = Game(); g3.start_pvp3(); g3._ui_flash_p3 = S.UI_AREA_FLASH_DURATION; g3._render_ui_area()
gl = sample(g3, 250); gr = sample(g3, 550)
print("[绿闪] 左(x250)=%s 右(x550)=%s" % (gl, gr))
ok = ok and (gl[1] > 60 and gr[1] > 60)

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
