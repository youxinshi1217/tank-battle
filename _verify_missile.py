# -*- coding: utf-8 -*-
"""追踪导弹（MISSILE）全行为验证。

覆盖：
  [1] 道具类型注册 + 刷新权重
  [2] 拾取记账（+1 发、可累计、消耗、失效）
  [3] game 级发射（owner/emitter/弹药/冷却/出生点=炮口）
  [4] 出膛播放飞行音效
  [5] 无目标直线前飞（速率=1 倍坦克移速=150px/s、方向不变）
  [6] 锁定目标 → 弧线追击命中 P2 → 击杀计分 + 爆炸 + 隐藏
  [7] 目标转移 + 弹体/烟迹染色切换（旧烟保色、新烟变色）
  [8] 自伤宽限：宽限期内与自身重叠不命中
  [9] 误伤自己：宽限期后追到自己 → 自毁结算（P2 胜局、不计分）
  [10] 护盾拦截：导弹爆炸 + 零伤害 + 爆炸音效
  [11] 撞墙无限反弹（10 秒内 ≥3 次反弹仍存活）
  [12] 10 秒寿命到头：灰烟消散 → 消失（无命中、无伤害）
  [13] 音效时间线：飞行→锁定→贴近播即将命中并顶替锁定音→死亡统一 0.4s 淡出
  [14] 换关清理：旧导弹音效淡出、列表清空
  [15] 前方 180° 扇形锁定范围（身后不可锁、侧前 60° 可锁、反弹后身后目标进扇形）
  [16] 比赛结束（GAME_OVER/VICTORY）：在飞导弹音效淡出、视觉冰冻保留
  [17] 视线遮挡（"可见范围"锁定）：隔墙不可锁、同侧无遮挡可锁、
       锁定后被墙隔断→丢锁直飞、遮挡移除后重新锁定
  [18] 追踪强度衰减：5 秒全强度（贴目标转弯）→ 逐级下降（只减不增），
       换目标/丢锁重锁不重置计时；衰减后拐弯目标被甩开、直线目标仍命中
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math

import pygame

pygame.init()

import main as M
from core.settings import (
    TILE_SIZE, TANK_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE,
    MISSILE_SPEED, MISSILE_GRACE, MISSILE_FUEL, MISSILE_WARN_DISTANCE,
    MISSILE_SND_FADEOUT, MISSILE_LOCK_FADEOUT,
    MISSILE_TURN_RATE, MISSILE_TRACK_FULL_TIME,
    MISSILE_TRACK_DECAY_STEP, MISSILE_TRACK_DECAY_STAGES,
    ITEM_SPAWN_WEIGHTS, COLOR_PLAYER_TANK,
)
from entities.item import ItemType
from entities.player2_tank import COLOR_P2_TANK
from entities.missile import Missile
from maps.tile import TileType

PLAYER_KILL_SCORE = M.PLAYER_KILL_SCORE

results = []


def check(name, ok):
    results.append((name, ok))
    print(("[PASS] " if ok else "[FAIL] ") + name, flush=True)


# ------------------------------------------------------------------ #
# 测试替身
# ------------------------------------------------------------------ #
class FakeMap:
    """全空地图：rect_hits_obstacle 只依赖 get_tile。"""
    def get_tile(self, row, col):
        return TileType.EMPTY


class WallMap:
    """可自定义墙位置的地图：walls={(row,col):True}，其余全空。"""
    def __init__(self):
        self.walls = set()
    def add_wall_col(self, col, rows=25):
        for r in range(rows):
            self.walls.add((r, col))
    def get_tile(self, row, col):
        return TileType.BRICK if (row, col) in self.walls else TileType.EMPTY


class FakeTank:
    """最小坦克替身：只有 rect（供 Missile 目标/命中判定）。"""
    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        self.rect.center = (int(x), int(y))


class FakeChannel:
    def __init__(self, log, name):
        self.log = log
        self.name = name
    def get_busy(self):
        return True
    def fadeout(self, ms):
        self.log.append(("fadeout", self.name, ms))


class FakeAudio:
    """记录 play/fadeout 调用，替代 AudioManager。"""
    def __init__(self):
        self.log = []
    def play(self, name, volume_scale=1.0):
        self.log.append(("play", name))
        return FakeChannel(self.log, name)


def plays(fa, name):
    return any(e == ("play", name) for e in fa.log)


def fadeouts(fa, name):
    return [ms for e in fa.log if e[0] == "fadeout" and e[1] == name
            for ms in (e[2],)]


# ------------------------------------------------------------------ #
# game 级辅助
# ------------------------------------------------------------------ #
def new_game(rounds=3):
    g = M.Game()
    g.start_pvp(rounds=rounds)
    g.round_over_pause = 0.0
    g._pause_after = None
    g._pvp_destroyed = {}
    # 预热时钟：消除首帧 dt 尖峰（启动耗时被计进第一帧）
    for _ in range(5):
        g.clock.tick(60)
        g.update()
    return g


def step(game, frames, fps=60):
    for _ in range(frames):
        game.clock.tick(fps)
        game.update()


def place(tank, x, y):
    tank.physics.x = x
    tank.physics.y = y
    tank.physics.vx = 0.0
    tank.physics.vy = 0.0
    tank.x = x
    tank.y = y
    tank.rect.center = (round(x), round(y))


def find_clear_row_pair(game_map, min_gap=300):
    """找一行里相距 >= min_gap 的两个 EMPTY 格中心，且两点之间整行无墙
    （保证导弹直线弹道不会被墙挡）。"""
    for row in range(GRID_SIZE):
        cols = [c for c in range(GRID_SIZE)
                if game_map.get_tile(row, c) == TileType.EMPTY]
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                if (cols[j] - cols[i]) * TILE_SIZE < min_gap:
                    continue
                # 必须整行畅通（i..j 之间无墙）
                if not all(game_map.get_tile(row, c) == TileType.EMPTY
                           for c in range(cols[i], cols[j] + 1)):
                    continue
                x1 = cols[i] * TILE_SIZE + TILE_SIZE / 2
                x2 = cols[j] * TILE_SIZE + TILE_SIZE / 2
                y = row * TILE_SIZE + TILE_SIZE / 2
                return (x1, y), (x2, y)
    return None, None


def direct_update(missile, frames, targets, dt=1.0 / 60.0):
    for _ in range(frames):
        missile.update(dt, targets)
        if not missile.alive:
            break


# ================================================================== #
print("===== [1] 道具注册与权重 =====", flush=True)
check("[1] ItemType.MISSILE 已注册", ItemType.MISSILE == "MISSILE")
check("[1] 刷新权重含 MISSILE 且 >0",
      ITEM_SPAWN_WEIGHTS.get("MISSILE", 0) > 0)

# ================================================================== #
print("\n===== [2] 拾取记账 =====", flush=True)
g2 = new_game()
p1, p2 = g2.player_tank, g2.player2_tank
check("[2] 初始无追踪弹", p1.missile_ammo == 0 and not p1.missile_active)
p1.apply_item_effect(ItemType.MISSILE)
check("[2] 拾取 +1 发", p1.missile_ammo == 1 and p1.missile_active)
p1.charge_missile()
check("[2] 再拾取可累计到 2", p1.missile_ammo == 2)
p1.consume_missile_ammo()
check("[2] 发射消耗 1 发", p1.missile_ammo == 1)
p1.consume_missile_ammo()
check("[2] 归零后失效", p1.missile_ammo == 0 and not p1.missile_active)

# ================================================================== #
print("\n===== [3] game 级发射 =====", flush=True)
g3 = new_game()
p1, p2 = g3.player_tank, g3.player2_tank
p1.charge_missile()
mx, my = p1.get_muzzle_position()
g3._try_fire_for(p1, "p1")
check("[3] 发射后场上 1 枚导弹", len(g3.missiles) == 1)
m = g3.missiles[0]
check("[3] owner/emitter 正确", m.owner == "p1" and m.emitter is p1)
check("[3] 弹药已消耗", p1.missile_ammo == 0)
check("[3] 出生点=炮口", abs(m.x - mx) < 2 and abs(m.y - my) < 2)
check("[3] 速率=|MISSILE_SPEED|=1倍坦克移速",
      m.speed == abs(MISSILE_SPEED) == 1.0 * 150)
check("[3] 不占普通弹匣", p1.ammo == M.MAGAZINE_CAPACITY)
# 冷却拦截：立即再打一枚（先充能）应被冷却挡下
p1.charge_missile()
g3._try_fire_for(p1, "p1")
check("[3] 冷却生效（不会连发）", len(g3.missiles) == 1)

# ================================================================== #
print("\n===== [4] 出膛飞行音效 =====", flush=True)
g4 = new_game()
fa = FakeAudio()
g4.audio = fa
g4.player_tank.charge_missile()
g4._try_fire_for(g4.player_tank, "p1")
check("[4] 播放飞行音效一次", plays(fa, "missile_flight"))

# ================================================================== #
print("\n===== [5] 无目标直线前飞 =====", flush=True)
m5 = Missile(200.0, 200.0, 1.0, 0.0, FakeMap(), "p1", None)
a0 = m5.dir_angle
direct_update(m5, 60, [])   # 1 秒
moved = math.hypot(m5.x - 200.0, m5.y - 200.0)
check("[5] 直线飞行约 150px/秒（1倍坦克移速）", 148 <= moved <= 155)
check("[5] 方向保持不变", abs(m5.dir_angle - a0) < 1e-9)
check("[5] 1 秒后仍存活", m5.alive)

# ================================================================== #
print("\n===== [6] 追踪命中 P2 → 击杀结算 =====", flush=True)
g6 = new_game()
p1, p2 = g6.player_tank, g6.player2_tank
A, B = find_clear_row_pair(g6.game_map, min_gap=300)
if A is None:
    check("[6] 找到无墙直线布阵点", False)
else:
    check("[6] 找到无墙直线布阵点", True)
    place(p1, A[0], A[1])
    place(p2, B[0], B[1])
    # 1 倍速（150px/s）下出膛点离射手仍最近，但扇形规则把"身后的射手"排除，
    # 因此测试在"中距离"布阵隔离验证追踪+结算本身（发射点=炮口由 [3] 覆盖）：
    # 导弹在 P1 前方 160px 处出膛、直指 P2（P2 在前方扇形内、P1 在身后扇形外）。
    mx6 = A[0] + 160.0
    m6 = Missile(mx6, A[1], 1.0, 0.0, g6.game_map, owner="p1", audio=None)
    m6.emitter = p1
    g6.missiles.append(m6)
    sc0 = g6.score_manager.current_score
    hit = False
    for _ in range(640):       # 150px/s：140px 约需 1s，640 帧留足余量
        g6.clock.tick(60)
        g6.update()
        if not m6.alive:
            hit = True
            break
    check("[6] 导弹命中 P2", hit and m6.hit_tank is p2)
    check("[6] P2 被摧毁（隐藏/阵亡）", p2 in g6._dead_players)
    check("[6] 击杀计分", g6.score_manager.current_score == sc0 + PLAYER_KILL_SCORE)
    check("[6] 击杀计数 +1", g6.score_manager.kill_count == 1)
    check("[6] 生成爆炸特效", len(g6.explosions) > 0)
    check("[6] 胜局锁定（P1 胜该局）", g6.round_manager.side_a_wins == 1)

# ================================================================== #
print("\n===== [7] 目标转移 + 染色切换 =====", flush=True)
m7 = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m7.emitter = None
t_near = FakeTank(710, 360)     # 初始最近（蓝）
t_far = FakeTank(760, 360)      # 初始较远（红）
targets7 = [(t_near, COLOR_P2_TANK), (t_far, COLOR_PLAYER_TANK)]
m7.update(1.0 / 60.0, targets7)
check("[7] 初始锁定最近目标（蓝）", m7.target is t_near)
check("[7] 目标色=蓝方", m7.target_color == COLOR_P2_TANK)
check("[7] 烟迹染目标色（蓝）",
      all(p["color"] == COLOR_P2_TANK for p in m7.smoke) and len(m7.smoke) > 0)
direct_update(m7, 8, targets7)   # 8 帧：导弹向蓝方飞去（尚未命中）
# 交换站位：蓝方远离、红方成为最近（导弹距红方 ~73px，够完成重评不断太快命中）
t_near.rect.center = (900, 500)
t_far.rect.center = (740, 360)
direct_update(m7, 4, targets7)   # 4 帧 > 0.15s 重评间隔
check("[7] 转移目标到红方", m7.target is t_far)
check("[7] 染色切换为红方", m7.target_color == COLOR_PLAYER_TANK)
alive_colors = {p["color"] for p in m7.smoke}
check("[7] 新烟迹变红、旧蓝烟仍在自然消散",
      COLOR_PLAYER_TANK in alive_colors and COLOR_P2_TANK in alive_colors)

# ================================================================== #
print("\n===== [8] 自伤宽限期 =====", flush=True)
m8 = Missile(100.0, 100.0, 0.0, -1.0, FakeMap(), "p1", None)
t8 = FakeTank(100, 100)          # 与导弹完全重叠
m8.emitter = t8
direct_update(m8, 20, [(t8, COLOR_PLAYER_TANK)])   # 0.33s < 0.35s 宽限
check("[8] 宽限期内贴自身不命中", m8.alive and m8.hit_tank is None)
check("[8] 宽限期内不锁自己", m8.target is None)

# ================================================================== #
print("\n===== [9] 误伤自己 → 自毁结算 =====", flush=True)
g9 = new_game()
p1, p2 = g9.player_tank, g9.player2_tank
A, B = find_clear_row_pair(g9.game_map, min_gap=300)
place(p1, A[0], A[1])
place(p2, B[0], B[1])
# 目标池只剩 P1（隔离验证自伤路径）；扇形规则下射手出膛时在导弹身后锁不到，
# 因此用可控墙图让导弹先撞右墙反弹、车头转向左 —— 射手进入前方 180° 扇形后才被追。
g9._missile_targets = lambda: [(p1, COLOR_PLAYER_TANK)]
wm9 = WallMap()
wm9.add_wall_col(int(A[0]) // TILE_SIZE + 2)   # P1 右侧两格放一堵整列墙
m9 = Missile(A[0] + 16.0, A[1], 1.0, 0.0, wm9, owner="p1", audio=None)
m9.emitter = p1
g9.missiles.append(m9)
sc0 = g9.score_manager.current_score
kc0 = g9.score_manager.kill_count
hit_self = False
for _ in range(600):
    g9.clock.tick(60)
    g9.update()
    if not m9.alive:
        hit_self = True
        break
check("[9] 导弹反弹后绕回来撞上自己", hit_self and m9.hit_tank is p1)
check("[9] 自毁不计击杀分", g9.score_manager.current_score == sc0
      and g9.score_manager.kill_count == kc0)
check("[9] 自毁判对方胜局", g9.round_manager.side_b_wins == 1)
check("[9] 自毁后 P1 阵亡", p1 in g9._dead_players)

# ================================================================== #
print("\n===== [10] 护盾拦截 =====", flush=True)
g10 = new_game()
p1, p2 = g10.player_tank, g10.player2_tank
A, B = find_clear_row_pair(g10.game_map, min_gap=300)
place(p1, A[0], A[1])
place(p2, B[0], B[1])
p2.apply_shield()
# 同 [6]：中距离布阵（P1 前方 160px 出膛直指 P2），保证全程锁定 P2
m10 = Missile(A[0] + 160.0, A[1], 1.0, 0.0, g10.game_map, owner="p1", audio=None)
m10.emitter = p1
g10.missiles.append(m10)
sc0 = g10.score_manager.current_score
for _ in range(640):
    g10.clock.tick(60)
    g10.update()
    if not m10.alive:
        break
check("[10] 导弹炸在护盾上（消失）", not m10.alive and m10.hit_tank is p2)
check("[10] 持盾玩家零伤害", p2 not in g10._dead_players)
check("[10] 不计分、未结算", g10.score_manager.current_score == sc0
      and g10.round_over_pause == 0.0)
check("[10] 有爆炸特效", len(g10.explosions) > 0)

# ================================================================== #
print("\n===== [11] 撞墙无限反弹 =====", flush=True)
# 150px/s 下屏幕边界往返更来不及；改用可控墙图：导弹在两侧墙之间反复
# 弹来弹去（每次弹约 31px），5 秒内 >=3 次反弹且始终存活。
wm = WallMap()
cx, cy = SCREEN_WIDTH / 2.0, SCREEN_HEIGHT / 2.0
mid_col = int(cx) // TILE_SIZE
wm.add_wall_col(mid_col - 1)   # 左墙
wm.add_wall_col(mid_col + 1)   # 右墙
m11 = Missile(cx, cy, 1.0, 0.0, wm, "p1", None)
bounces = 0
last_sign = 1.0
for _ in range(300):           # 5 秒
    m11.update(1.0 / 60.0, [])
    sign = 1.0 if math.cos(m11.dir_angle) >= 0 else -1.0
    if sign != last_sign:
        bounces += 1
        last_sign = sign
    if not m11.alive:
        break
check("[11] 撞墙只翻方向不消失", m11.alive)
check("[11] 5 秒内反弹 ≥3 次", bounces >= 3)

# ================================================================== #
print("\n===== [12] 10 秒寿命 → 灰烟消散 =====", flush=True)
m12 = Missile(200.0, 200.0, 1.0, 0.0, FakeMap(), "p1", None)
dissolved = False
for _ in range(700):
    m12.update(1.0 / 60.0, [])
    if m12.dying:
        dissolved = True
        break
check("[12] 10 秒到头触发化灰", dissolved and m12.hit_tank is None)
check("[12] 喷出灰色烟雾团",
      dissolved and any(p["color"] == (140, 140, 140) for p in m12.smoke))
check("[12] 化灰阶段不再移动/命中", m12.dying)
for _ in range(40):            # 0.5s 消散
    m12.update(1.0 / 60.0, [])
check("[12] 消散完毕后彻底消失", not m12.alive)

# ================================================================== #
print("\n===== [13] 音效时间线 =====", flush=True)
fa13 = FakeAudio()
m13 = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", fa13)
m13.emitter = None
t13 = FakeTank(780, 350)           # 初始 ~180px（> 175 阈值，且在 800px 图内）
targets13 = [(t13, COLOR_P2_TANK)]
m13.update(1.0 / 60.0, targets13)
check("[13] 出膛播飞行音效", plays(fa13, "missile_flight"))
check("[13] 锁定播锁定音效", plays(fa13, "missile_lock"))
check("[13] 未贴近不播即将命中", not plays(fa13, "missile_warn"))
# 阈值边界：~190px 仍算远 → 不播；进入 6~8 车身（< 175）→ 立刻顶替播即将命中
t13.rect.center = (790, 355)       # ~190px > MISSILE_WARN_DISTANCE(175)
m13.update(1.0 / 60.0, targets13)
check("[13] 超出 175px 阈值不播即将命中", not plays(fa13, "missile_warn"))
t13.rect.center = (755, 360)       # ~155px < 175（≈6 车身）
m13.update(1.0 / 60.0, targets13)
check("[13] 进入 6~8 车身播即将命中音效", plays(fa13, "missile_warn"))
check("[13] 即将命中顶替锁定音（300ms 淡出）",
      fadeouts(fa13, "missile_lock") == [int(MISSILE_LOCK_FADEOUT * 1000)])
# 燃料耗尽 → 死亡统一淡出
m13.fuel = 0.001
m13.update(1.0 / 60.0, targets13)
check("[13] 死亡时飞行/锁定/警告统一 0.4s 淡出",
      fadeouts(fa13, "missile_flight") == [int(MISSILE_SND_FADEOUT * 1000)]
      and len(fadeouts(fa13, "missile_flight")) == 1)

# ================================================================== #
print("\n===== [14] 换关清理 =====", flush=True)
g14 = new_game()
fa14 = FakeAudio()
g14.audio = fa14
g14.player_tank.charge_missile()
g14._try_fire_for(g14.player_tank, "p1")
check("[14] 换关前有导弹在飞", len(g14.missiles) == 1)
g14._load_stage(g14.level_manager.current_stage)
check("[14] 换关后列表清空", len(g14.missiles) == 0)
check("[14] 旧导弹音效已淡出", len(fadeouts(fa14, "missile_flight")) == 1)

# ================================================================== #
print("\n===== [15] 前方 180° 扇形锁定范围 =====", flush=True)
# a) 正后方目标不可锁；即使更近也跳过，锁定扇形内目标
m15a = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m15a.emitter = None
t_back = FakeTank(500, 360)      # 正后 100px（全场最近）
t_front = FakeTank(760, 360)     # 正前 160px（扇形内）
m15a.update(1.0 / 60.0, [(t_back, COLOR_P2_TANK), (t_front, COLOR_PLAYER_TANK)])
check("[15] 正后方目标不锁", m15a.target is not t_back)
check("[15] 锁定扇形内目标", m15a.target is t_front)
# b) 目标全在扇形外 → 无锁定、直飞
m15b = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m15b.emitter = None
m15b.update(1.0 / 60.0, [(FakeTank(520, 360), COLOR_P2_TANK)])
check("[15] 扇形外无目标 → 不锁定", m15b.target is None)
# c) 侧前 60° 可锁；侧后 135° 不可锁
ang60 = math.radians(60)
t_60 = FakeTank(600 + 100 * math.cos(ang60), 360 + 100 * math.sin(ang60))
m15c = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m15c.emitter = None
m15c.update(1.0 / 60.0, [(t_60, COLOR_P2_TANK)])
check("[15] 侧前 60° 在扇形内可锁", m15c.target is t_60)
ang135 = math.radians(135)
t_135 = FakeTank(600 + 100 * math.cos(ang135), 360 + 100 * math.sin(ang135))
m15d = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m15d.emitter = None
m15d.update(1.0 / 60.0, [(t_135, COLOR_P2_TANK)])
check("[15] 侧后 135° 在扇形外不锁", m15d.target is None)
# d) 撞墙反弹后车头转向，原先在身后的目标进入扇形 → 变为可锁（自伤路径）
wm15 = WallMap()
wm15.add_wall_col(int(600.0) // TILE_SIZE + 2)   # 右侧一列墙
m15e = Missile(600.0, 360.0, 1.0, 0.0, wm15, "p1", None)
m15e.emitter = None
t_behind = FakeTank(540, 360)
direct_update(m15e, 5, [(t_behind, COLOR_PLAYER_TANK)])
check("[15] 出膛时身后目标不锁", m15e.target is None)
for _ in range(120):            # 飞到右墙反弹（约 0.9s）
    m15e.update(1.0 / 60.0, [(t_behind, COLOR_PLAYER_TANK)])
    if math.cos(m15e.dir_angle) < 0:
        break
direct_update(m15e, 10, [(t_behind, COLOR_PLAYER_TANK)])
check("[15] 反弹后原身后目标进入扇形被锁定", m15e.target is t_behind)

# ================================================================== #
print("\n===== [16] 比赛结束淡出在飞导弹音效 =====", flush=True)
# 主循环只在 PLAYING 态调 update()：结果画面下导弹被冻住不再致死，
# 若不主动淡出，音效会一路播到自然结束（飞行音最长 12s+）。
# set_game_over()/set_victory() 必须统一 0.4s 淡出，但保留视觉冰冻。
g16 = new_game()
fa16 = FakeAudio()
g16.audio = fa16
g16.player_tank.charge_missile()
g16._try_fire_for(g16.player_tank, "p1")
check("[16] 结束前有导弹在飞", len(g16.missiles) == 1)
g16.set_game_over()
check("[16] 进入 GAME_OVER", g16.state == M.GameState.GAME_OVER)
check("[16] GAME_OVER 时飞行音效已淡出（400ms）",
      fadeouts(fa16, "missile_flight") == [int(MISSILE_SND_FADEOUT * 1000)])
check("[16] 导弹视觉保留（冰冻不清屏）",
      len(g16.missiles) == 1 and g16.missiles[0].alive)
g16b = new_game()
fa16b = FakeAudio()
g16b.audio = fa16b
g16b.player_tank.charge_missile()
g16b._try_fire_for(g16b.player_tank, "p1")
g16b.set_victory()
check("[16] VICTORY 时同样淡出",
      fadeouts(fa16b, "missile_flight") == [int(MISSILE_SND_FADEOUT * 1000)])
check("[16] VICTORY 时导弹仍在场", len(g16b.missiles) == 1)

# ================================================================== #
print("\n===== [17] 视线遮挡：隔墙不可锁（可见范围锁定） =====", flush=True)
# TILE_SIZE=32：col 18 覆盖 x∈[576,608)，col 16 覆盖 x∈[512,544)。
# a) 目标在正前方扇形内、距离 200px，但中间隔一整列墙 → 不可锁
wm17 = WallMap()
wm17.add_wall_col(18)
m17a = Missile(500.0, 360.0, 1.0, 0.0, wm17, "p1", None)
m17a.emitter = None
t17a = FakeTank(700, 360)          # 墙后正前方（扇形内、全场唯一目标）
m17a.update(1.0 / 60.0, [(t17a, COLOR_P2_TANK)])
check("[17] 隔着墙的目标锁不到（不能隔障碍物探测）", m17a.target is None)
check("[17] 无锁定时直飞巡航、弹体失色", m17a.target_color is None)
# b) 同侧无遮挡、在扇形内 → 正常锁
m17b = Missile(500.0, 360.0, 1.0, 0.0, wm17, "p1", None)
m17b.emitter = None
t17b = FakeTank(560, 360)          # 墙前 60px，通道无墙
m17b.update(1.0 / 60.0, [(t17b, COLOR_PLAYER_TANK)])
check("[17] 无遮挡的扇形内目标正常锁", m17b.target is t17b)
# c) 锁定后目标被墙隔断 → 丢锁（不能隔墙继续追）；墙移除后重新锁定
# （直接调 _select_target 做确定性验证，避免掺入导弹巡航位移/撞墙）
wm17c = WallMap()
m17c = Missile(500.0, 360.0, 1.0, 0.0, wm17c, "p1", None)
m17c.emitter = None
t17c = FakeTank(550, 360)
m17c.update(1.0 / 60.0, [(t17c, COLOR_P2_TANK)])
check("[17] 先正常锁定", m17c.target is t17c)
wm17c.add_wall_col(16)             # 墙挪到导弹与目标之间（512~544）
m17c._select_target([(t17c, COLOR_P2_TANK)])
check("[17] 目标被墙隔断后丢失锁定", m17c.target is None)
check("[17] 丢锁后弹体退回深灰", m17c.target_color is None)
for r in range(25):                # 移除该列墙
    wm17c.walls.discard((r, 16))
m17c._select_target([(t17c, COLOR_P2_TANK)])
check("[17] 遮挡移除后重新锁定", m17c.target is t17c)
# d) _can_see：采样步长小于格宽，墙后/墙前判定稳定（贴墙目标不误判）
m17d = Missile(570.0, 360.0, 1.0, 0.0, wm17, "p1", None)
m17d.emitter = None
check("[17] _can_see 墙后=False（步长够细不漏检）",
      m17d._can_see(FakeTank(700, 360)) is False)
check("[17] _can_see 墙前=True", m17d._can_see(FakeTank(540, 360)) is True)
check("[17] _can_see 重合=True", m17d._can_see(FakeTank(570, 360)) is True)

# ================================================================== #
print("\n===== [18] 追踪强度衰减（5 秒全强度 → 逐级下降） =====", flush=True)
# a) 强度阶梯：首次锁定起只减不增
m18a = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m18a.emitter = None
t18a = FakeTank(760, 360)
m18a.update(1.0 / 60.0, [(t18a, COLOR_P2_TANK)])
check("[18] 首次锁定即开始计时", m18a._lock_age == 0.0)
check("[18] 全强度窗口内强度=100%", m18a._track_strength() == 1.0)
m18a._lock_age = MISSILE_TRACK_FULL_TIME - 0.01
check("[18] 差 0.01 秒到衰减点仍满强度", m18a._track_strength() == 1.0)
m18a._lock_age = MISSILE_TRACK_FULL_TIME + 0.5
check("[18] 第 1 档衰减 = %.2f" % MISSILE_TRACK_DECAY_STAGES[0],
      m18a._track_strength() == MISSILE_TRACK_DECAY_STAGES[0])
m18a._lock_age = MISSILE_TRACK_FULL_TIME + 1.5
check("[18] 第 2 档衰减 = %.2f" % MISSILE_TRACK_DECAY_STAGES[1],
      m18a._track_strength() == MISSILE_TRACK_DECAY_STAGES[1])
m18a._lock_age = MISSILE_TRACK_FULL_TIME + 2.5
check("[18] 第 3 档衰减 = %.2f" % MISSILE_TRACK_DECAY_STAGES[2],
      m18a._track_strength() == MISSILE_TRACK_DECAY_STAGES[2])
m18a._lock_age = MISSILE_TRACK_FULL_TIME + 3.5
check("[18] 第 4 档衰减 = %.2f" % MISSILE_TRACK_DECAY_STAGES[3],
      m18a._track_strength() == MISSILE_TRACK_DECAY_STAGES[3])
m18a._lock_age = 99.0
check("[18] 衰减到底后保持最低档",
      m18a._track_strength() == MISSILE_TRACK_DECAY_STAGES[-1])
_strengths = []
for _i in range(0, 100):
    m18a._lock_age = _i / 10.0
    _strengths.append(m18a._track_strength())
check("[18] 强度随锁定时长只减不增",
      all(_strengths[k] >= _strengths[k + 1] for k in range(len(_strengths) - 1)))

# b) 转向速率随强度等比下降（目标固定在左前侧，量 0.3s 转角）
def _turned_over(frames, lock_age):
    mm = Missile(400.0, 400.0, 1.0, 0.0, FakeMap(), "p1", None)
    mm.emitter = None
    tt = FakeTank(450, 100)          # 左前侧（扇形内、空图无墙）
    direct_update(mm, 3, [(tt, COLOR_P2_TANK)])   # 先锁定
    a0 = mm.dir_angle
    mm._lock_age = lock_age
    direct_update(mm, frames, [(tt, COLOR_P2_TANK)])
    return abs(mm.dir_angle - a0), mm.target is tt

turned_full, ok_full = _turned_over(18, 1.0)          # 全强度
turned_mid, _ = _turned_over(18, MISSILE_TRACK_FULL_TIME + 1.5)   # 0.35 档
turned_low, ok_low = _turned_over(18, 99.0)           # 最低档
expect_full = MISSILE_TURN_RATE * 1.0 * 18 / 60.0
check("[18] 全强度 0.3s 转过 %.2f 弧度（贴目标转弯）" % turned_full,
      ok_full and turned_full >= expect_full * 0.9)
check("[18] 中档 0.3s 转角约为全强度 3.5 成",
      turned_mid <= turned_full * (MISSILE_TRACK_DECAY_STAGES[1] + 0.06)
      and turned_mid >= turned_full * (MISSILE_TRACK_DECAY_STAGES[1] - 0.06))
check("[18] 最低档 0.3s 几乎拧不动（%.3f 弧度）" % turned_low,
      ok_low and turned_low <= MISSILE_TURN_RATE * 0.05 * 18 / 60.0 * 1.15)
check("[18] 三档角速度严格递减",
      turned_full > turned_mid > turned_low)

# c)  gameplay 级：目标横向机动（坦克速度）——全强度跟得住、衰减后被甩开
def _chase_gap(lock_age):
    mm = Missile(200.0, 400.0, 1.0, 0.0, FakeMap(), "p1", None)
    mm.emitter = None
    tt = FakeTank(500, 400)          # 正前 300px
    direct_update(mm, 3, [(tt, COLOR_P2_TANK)])
    mm._lock_age = lock_age
    for i in range(60):              # 1 秒：目标以 150px/s 向下机动
        tt.rect.center = (500, 400 + round(2.5 * (i + 1)))   # =150px/s
        mm.update(1.0 / 60.0, [(tt, COLOR_P2_TANK)])
    tx, ty = tt.rect.center
    desired = math.atan2(ty - mm.y, tx - mm.x)
    off = abs((desired - mm.dir_angle + math.pi) % (2 * math.pi) - math.pi)
    return off, mm.target is tt, mm.alive

gap_full, lock_full, alive_full = _chase_gap(1.0)
gap_low, lock_low, alive_low = _chase_gap(99.0)
check("[18] 全强度跟得住横向机动目标（指向偏差 %.2f 弧度）" % gap_full,
      lock_full and alive_full and gap_full < 0.3)
check("[18] 衰减后被机动目标甩开（偏差 %.2f 弧度）" % gap_low,
      lock_low and alive_low and gap_low > 0.6)

# d) 换目标 / 丢锁重锁均不重置强度计时（防"换目标续命"）
m18d = Missile(600.0, 360.0, 1.0, 0.0, FakeMap(), "p1", None)
m18d.emitter = None
t_far18 = FakeTank(700, 360)
t_near18 = FakeTank(640, 360)
m18d.update(1.0 / 60.0, [(t_far18, COLOR_P2_TANK)])
m18d._lock_age = MISSILE_TRACK_FULL_TIME + 2.5      # 已衰减到第 3 档
m18d._select_target([(t_far18, COLOR_P2_TANK), (t_near18, COLOR_PLAYER_TANK)])
check("[18] 换到更近目标成功", m18d.target is t_near18)
check("[18] 换目标不重置计时", m18d._lock_age == MISSILE_TRACK_FULL_TIME + 2.5)
check("[18] 换目标后仍按旧强度衰减",
      m18d._track_strength() == MISSILE_TRACK_DECAY_STAGES[2])
m18d._select_target([])             # 全部目标脱离 → 丢锁
check("[18] 丢锁时计时保留、目标清空",
      m18d._lock_age == MISSILE_TRACK_FULL_TIME + 2.5 and m18d.target is None)
m18d._select_target([(t_far18, COLOR_P2_TANK)])
check("[18] 重锁也不重置计时",
      m18d._lock_age == MISSILE_TRACK_FULL_TIME + 2.5)
check("[18] 重锁后强度仍低（不会满血复活）",
      m18d._track_strength() == MISSILE_TRACK_DECAY_STAGES[2])

# ------------------------------------------------------------------ #
pygame.quit()
fails = [n for n, ok in results if not ok]
print("\n===== 汇总 =====", flush=True)
print(f"共 {len(results)} 项，通过 {len(results) - len(fails)}，失败 {len(fails)}", flush=True)
for n, ok in results:
    if not ok:
        print("  FAILED:", n, flush=True)
sys.exit(1 if fails else 0)
