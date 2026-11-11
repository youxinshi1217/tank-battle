import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
sys.path.insert(0, r"C:/Users/32857/Desktop/新建文件夹/坦克大战/tank_game")
from main import Game, GameState

pygame.init()
g = Game()
g.start_pvp(5)

r = g._ui_area_rect()
cx, vcy = r.x + r.width // 2, r.y + r.height // 2
sx, sy = cx + 20, vcy  # 圆内、偏离中心（避开 VS 文字笔画），应命中 VS_BG 圆面

def center_pixel(state):
    g.state = state
    g._render_battle()
    return g.screen.get_at((sx, sy))[:3]

p_playing = center_pixel(GameState.PLAYING)
p_over = center_pixel(GameState.GAME_OVER)
p_vict = center_pixel(GameState.VICTORY)

print("采样点 (x=%d,y=%d) 中央像素 RGB：" % (sx, sy))
print("  PLAYING     :", p_playing, "（应是 VS_BG 圆面 ≈ (52,52,60)）")
print("  GAME_OVER   :", p_over, "（应=渐变底色 ≈ (35,35,41)，无 VS 圆）")
print("  VICTORY     :", p_vict, "（应=渐变底色 ≈ (35,35,41)，无 VS 圆）")

# 判定：PLAYING 时该点应明显更亮（VS_BG 52 > 渐变 35）；结束态应回落到渐变
assert p_playing[0] > 45, "FAIL: PLAYING 下应在中央画出 VS 圆"
assert p_over[0] < 45 and p_vict[0] < 45, "FAIL: 结束态下中央不应有 VS 圆"
print("\nALL PASS：对决结束（结算页）VS 已隐藏，局间（PLAYING）VS 仍常驻。")
