"""验证三人混战击杀闪光映射：红(左)/蓝(右)/绿(中)各为击杀者那侧闪；
自毁/无击杀者闪被害者自己那侧。真实 Game 实例 + dummy SDL。"""
import pygame

pygame.init()
pygame.display.set_mode((800, 950))  # 占位，真实尺寸由 Game 内部接管
from main import Game  # noqa: E402

g = Game()
g.start_pvp3(3)  # match_mode=pvp3, state=PLAYING, player3_tank 已建
assert g.player3_tank is not None
assert g.match_mode == "pvp3"

rect = g._ui_area_rect()
x0, y0, w, h = rect.x, rect.y, rect.width, rect.height
cx = x0 + w // 2
mid_y0, mid_y1 = y0 + h // 2 - 6, y0 + h // 2 + 6
LEFT_X = x0 + 2
RIGHT_X = x0 + w - 3
CENTER_X = cx


def sample(col_x):
    r = g_max = b = 0
    for yy in range(mid_y0, mid_y1):
        c = g.screen.get_at((col_x, yy))
        r = max(r, c[0]); g_max = max(g_max, c[1]); b = max(b, c[2])
    return r, g_max, b


def render_with(victim, killer):
    g._ui_flash_p1 = g._ui_flash_p2 = g._ui_flash_p3 = 0.0
    if victim is None:
        g._pvp_destroyed = {}
    else:
        g._pvp_destroyed = {victim: killer}
    if victim is not None:
        g._trigger_kill_flashes(g._pvp_destroyed)
    g._render_ui_area()


# 基线（无任何闪光）
render_with(None, None)
base_L = sample(LEFT_X)
base_R = sample(RIGHT_X)
base_C = sample(CENTER_X)
print("基线 左(红,蓝,绿)=%s 右=%s 中=%s" % (base_L, base_R, base_C))

ok = True
cases = [
    ("红被蓝杀 -> 右蓝", g.player_tank, "p2", "R"),
    ("蓝被红杀 -> 左红", g.player2_tank, "p1", "L"),
    ("绿被蓝杀 -> 右蓝", g.player3_tank, "p2", "R"),
    ("绿被红杀 -> 左红", g.player3_tank, "p1", "L"),  # 你的第4条修正：左红
    ("红被绿杀 -> 中绿", g.player_tank, "p3", "C"),
    ("蓝被绿杀 -> 中绿", g.player2_tank, "p3", "C"),
    ("红自毁 -> 左红", g.player_tank, "p1", "L"),
    ("蓝自毁 -> 右蓝", g.player2_tank, "p2", "R"),
    ("绿自毁 -> 中绿", g.player3_tank, "p3", "C"),
    ("环境击杀(无killer)红 -> 左红", g.player_tank, None, "L"),
]
for name, victim, killer, expect in cases:
    render_with(victim, killer)
    L = sample(LEFT_X)
    R = sample(RIGHT_X)
    C = sample(CENTER_X)
    # 期望侧对应通道应明显高于基线同侧
    if expect == "L":
        good = L[0] > base_L[0] + 80
        detail = "左红=%d(基%d)" % (L[0], base_L[0])
    elif expect == "R":
        good = R[2] > base_R[2] + 80
        detail = "右蓝=%d(基%d)" % (R[2], base_R[2])
    else:
        good = C[1] > base_C[1] + 80
        detail = "中绿=%d(基%d)" % (C[1], base_C[1])
    # 反侧不应明显亮（防止误闪到错误一侧）
    if expect == "L":
        wrong = R[2] > base_R[2] + 40 or C[1] > base_C[1] + 40
    elif expect == "R":
        wrong = L[0] > base_L[0] + 40 or C[1] > base_C[1] + 40
    else:
        wrong = L[0] > base_L[0] + 40 or R[2] > base_R[2] + 40
    status = "OK " if (good and not wrong) else "FAIL"
    if not (good and not wrong):
        ok = False
    print("[%s] %-26s %s%s" % (status, name, detail,
          " (反侧误闪!)" if wrong else ""))

# 集成校验：直接走 _settle_pvp（pvp3 路径）也应触发闪光
g._round_locked = False
g._ui_flash_p1 = g._ui_flash_p2 = g._ui_flash_p3 = 0.0
g._pvp_destroyed = {g.player_tank: "p3"}   # 红被绿杀
g._settle_pvp()
g._render_ui_area()  # 直接渲染，不重置闪光（验证 _settle_pvp 已点亮计时器）
C2 = sample(CENTER_X)
print("集成(_settle_pvp 红被绿杀) 中绿=%d(基%d) -> %s" %
      (C2[1], base_C[1], "OK" if C2[1] > base_C[1] + 80 else "FAIL"))
if C2[1] <= base_C[1] + 80:
    ok = False

print("\n全部通过" if ok else "\n存在失败项")
