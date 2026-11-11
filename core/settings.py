# -*- coding: utf-8 -*-
"""
全局配置常量
坦克大战 - 项目骨架阶段
"""
import math
import os

# ---------- 窗口 ----------
WINDOW_TITLE = "坦克大战"
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
FPS = 60

# ---------- 窗口布局：游戏区 / UI 区分离 (Phase 7.0) ----------
# 游戏区 = 地图区（25×25 瓦片，固定 800×800）；UI 状态区位于游戏区下方，互不覆盖。
# 语义约定：SCREEN_HEIGHT 仍是"游戏区高度 / 实体下边界 clamp 值"，禁止改动其值，
# 否则冻结实体文件（enemy_tank/bullet/shotgun_pellet/player_tank）的 y 边界会随之
# 扩大，导致坦克/子弹穿出地图进入 UI 区。
GAME_AREA_HEIGHT = SCREEN_HEIGHT                # 游戏区高度（= 地图高度）
STATUS_PANEL_HEIGHT = 150                       # 游戏区下方 UI 状态区高度（待审，可调）
WINDOW_HEIGHT = GAME_AREA_HEIGHT + STATUS_PANEL_HEIGHT  # 建窗总高度
UI_AREA_Y = GAME_AREA_HEIGHT                    # UI 状态区顶部 y 坐标
COLOR_UI_AREA_BG = (255, 255, 255)              # [保留] 旧白底语义常量；实际底带改由 _render_ui_area 控制（见下方 UI_AREA_*）
COLOR_UI_AREA_TEXT = (236, 236, 240)             # UI 状态区文字颜色（浅色：适配深色金属驾驶舱底带）

# ---------- 状态栏深色驾驶舱底带配色（Phase 7.5-B）----------
# 取代纯白底带：深色金属渐变 + 阵营氛围光 + 中央 VS 徽记。
# 全部集中于此，便于统一热调。颜色取自战斗同款阵营色，保证状态栏与战场同世界。
UI_AREA_BG_TOP = (43, 43, 49)                   # 底带顶部色（比战场 COLOR_BG 略亮一档）
UI_AREA_BG_BOTTOM = (28, 28, 34)                # 底带底部色（更沉，形成控制台层次）
UI_AREA_VIGNETTE = (12, 12, 16)                 # 左右暗角色（径向压暗边角，制造"有厚度"）
UI_AREA_GLOW_RED = (204, 30, 30)                # P1 左区氛围光（= COLOR_PLAYER_TANK）
UI_AREA_GLOW_BLUE = (60, 90, 210)               # P2 右区氛围光（= COLOR_PLAYER2_TANK）
UI_AREA_GLOW_GREEN = (46, 190, 92)              # P3 中区氛围光（= COLOR_PLAYER3_TANK）
UI_AREA_GLOW_ALPHA = 30                         # 阵营氛围光透明度（0~255，柔和氛围基线；不抢文字，与原始纯绿版一致）
# 红/蓝边缘锚定、视觉焦点弱于中央绿，故各自额外提亮系数（只抬红/蓝，绿不乘）。
# 绿在正中（焦点）而红蓝在边缘，等亮度仍显绿更亮——用系数补偿边缘劣势，使三色视觉拉平。
UI_AREA_GLOW_RED_SCALE = 80 / 30                 # 红方(P1)稳态基准=80（=ALPHA×80/30；呼吸系数另设1.0）
UI_AREA_GLOW_GREEN_SCALE = 57 / 30                # 绿方(P3)稳态≈69（方案A：压暗一档；闪未封顶、Δ≈91由系数定）
UI_AREA_GLOW_BLUE_SCALE = 2.0                     # 蓝方(P2)稳态≈58、击杀闪Δ≈130（用户要求跳变130：压低稳态放大落差）
# 三色呼吸均满幅(1.0)：红/绿/蓝呼吸振幅=±12（BREATH_AMP）。蓝呼吸不乘(满幅)。
# 蓝稳态基准=30*3.8=114，距满值255留141余量→击杀闪(封顶255)跳变≈红闪，看得见。
UI_AREA_GLOW_GREEN_BREATH_SCALE = 1.0           # 绿方呼吸振幅系数（=1 满幅）
UI_AREA_GLOW_RED_BREATH_SCALE = 1.0             # 红方呼吸振幅系数（=1 满幅，与绿齐平；原0.15极弱已撤销）
UI_AREA_SEAM_TOP = (96, 96, 104)                # 顶沿高光细线（金属接缝）
UI_AREA_SEAM_BOTTOM = (8, 8, 10)                # 底沿收边细线（下沉感）
UI_AREA_BRUSH = (255, 255, 255)                 # 底部金属拉丝线（低不透明叠加，近不可见纹理）
UI_AREA_BRUSH_ALPHA = 12                        # 拉丝线不透明度
UI_AREA_VS_BG = (52, 52, 60)                    # 中央 VS 金属圆底（中灰，凸出底面）
UI_AREA_VS_RING = (120, 120, 132)               # VS 圆外描边（高光金属边）
UI_AREA_VS_INNER = (20, 20, 24)                 # VS 圆内凹陷线（立体感）
UI_AREA_VS_TEXT = (236, 236, 240)               # VS 文字色（浅色，与整体浅字一致）
UI_AREA_VS_RADIUS = 36                          # VS 圆半径（px）

# ---------- 档位 C 动态辉光（Phase 7.5-C）：呼吸 / 换弹提亮 / 命中闪光 ----------
# 三者合成同一套 per-side 辉光透明度公式，统一热调；UI_AREA_DYNAMIC=False 退回静态 B 档。
UI_AREA_DYNAMIC = True                          # 总开关（False=静态辉光，=B 档）
UI_AREA_GLOW_BREATH_AMP = 12                    # 呼吸振幅（叠加在 UI_AREA_GLOW_ALPHA 上，与原始纯绿版一致）
UI_AREA_GLOW_BREATH_PERIOD = 3.2                # 呼吸周期（秒）
UI_AREA_RELOAD_BOOST = 38                       # 换弹中该方辉光额外透明度
UI_AREA_FLASH_DURATION = 1.0                    # 命中闪光持续（秒，放慢拉长，卡在 1.5s 慢动作爆炸窗口内可见）
UI_AREA_FLASH_BOOST = 150                       # 命中闪光峰值额外透明度

# ---------- HUD 克制档案卡（白色状态栏顶部中央波次信息）----------
# 内容：波次编号（波次 03/05）+ 本波击杀进度刻度条（一格=一个敌人）+ 敌情（敌方存活数）。
# 位置：白色状态栏（UI 区）水平居中，垂直居中于"档案格之上的空白区"；卡片正下方中央列为中场读条。
# 样式：无底色（透明）、白底深字 + 细浅灰边框；文字整体加深保证白底清晰可见。
# 仅 PLAYING 绘制；PVP 无波次概念，整卡隐藏。全部参数集中于此，便于统一微调。
HUD_UI_FREE_H = 88                             # 卡片在白色栏内的可用高度（px）：SCORE/KILLS 档案格自 y=88 起，卡片在 0~88 内垂直居中
HUD_CARD_MIN_W = 200                           # 卡片最小宽度（px）：固定档案卡宽度，防波次/敌数变化时卡片忽窄忽宽
HUD_PAD = 6                                    # 卡片内边距（px，压缩腾空间给下方读条/即将来敌）
HUD_LINE_GAP = 4                               # 行间距（px）
HUD_FONT_SIZE = 14                             # 卡片字号（中文字体）
HUD_FONT_BOLD = True                           # 卡片文字加粗（加黑手感，非全粗）
HUD_TICK_W = 6                                 # 进度刻度宽（px，一格 = 一个敌人）
HUD_TICK_H = 12                                # 进度刻度高（px）
HUD_TICK_GAP = 2                               # 刻度间距（px）
HUD_COLOR_TEXT = (15, 15, 18)                  # 主文字（近黑，白底高对比）
HUD_COLOR_DIM = (38, 40, 46)                   # 次要文字（敌方存活数等，深灰清晰）
HUD_COLOR_TICK = (15, 15, 18)                  # 已消灭刻度（近黑）
HUD_COLOR_TICK_EMPTY = (150, 152, 160)         # 未消灭刻度（中灰，白底可见但弱于满格）
HUD_COLOR_BORDER = (110, 112, 120)             # 卡片细边框（深中灰，纸面档案线）

# ---------- 清波中场休息 UI（下一波生成倒计时读条 + 即将来敌）----------
# 读条位于白色状态栏卡片正下方的中央列（SCORE/KILLS 档案格收于左右两侧，中央空白留读条）；
# 布局自上而下：「即将来敌」→ 读条 → 倒计时数字（三者居中同列，读条下方数字圆润粗体）。
INTERMISSION_BAR_UI_TOP = 110                 # 读条顶部在白色栏内的 y 偏移（px）：卡片与即将来敌之下
INTERMISSION_BAR_W = 220                       # 状态栏中央读条宽度（像素）
INTERMISSION_BAR_H = 8                         # 读条高度（像素）
INTERMISSION_BAR_TRACK = (210, 210, 215)       # 读条轨道底色（白底带上浅灰，衬托收缩）
INTERMISSION_BAR_FILL = (0, 0, 0)              # 收缩填充色（高亮纯黑，白底醒目）
INTERMISSION_NUM_COLOR = (0, 0, 0)             # 倒计时数字色（高亮黑）
INTERMISSION_NUM_SIZE = 22                     # 倒计时数字字号（粗体，圆润；略收以适配布局）
INTERMISSION_NUM_GAP = 4                       # 数字/即将来敌 距读条间距（px，压缩保证全放下）
INTERMISSION_INCOMING_COLOR = (225, 25, 25)    # 「即将来敌」文字色（高亮红，白底最醒目）
INTERMISSION_INCOMING_BREATH_PERIOD = 1.2      # 「即将来敌」呼吸灯周期（秒），略快于道具 1.5s

# ---------- 颜色 (R, G, B) ----------
COLOR_BG = (30, 30, 30)
COLOR_TEXT = (255, 255, 255)
COLOR_FPS_BG = (0, 0, 0)
COLOR_HELP_TEXT = (0, 0, 0)          # 游戏说明页正文（浅色背景上用黑色文字，避免与背景不搭）

# ---------- 网格 / 地图 ----------
GRID_SIZE = 25
TILE_SIZE = SCREEN_WIDTH // GRID_SIZE  # 32px
# Phase 5.3 F1：视觉随碰撞——障碍整格绘制（1.0），视觉=碰撞语义。
# 原 0.6 为"缩小色块预留移动空间"的未兑现意图，已移除，渲染层直接整格绘制。
COLOR_BRICK = (176, 92, 60)
COLOR_STEEL = (150, 150, 160)
SHOW_GRID_LINES = False
COLOR_GRID_LINE = (50, 50, 50)

# ---------- 道具系统 (Phase 5.4 Item System Foundation) ----------
# 护盾光环颜色（玩家拾取护盾后，围绕玩家的蓝色光圈）
COLOR_SHIELD_RING = (80, 160, 255)
# T7 道具系统调优（全局全模式生效；冻结文件 item.py / item_spawn_manager.py 内的
# 旧默认值保留为"未使用默认"，实际值以本表为准，经 main.py 构造/子类传入）
ITEM_SPAWN_INTERVAL = 3.0   # 道具刷新间隔（秒），原 5.0 → 3.0（更快）
ITEM_MAX_ACTIVE   = 4       # 同场上限，原 1 → 2 → 4（更多；有空位即继续生成）
ITEM_MIN_SPACING  = 96.0    # 道具最小间距（像素，=3 格）：一个范围内只生成一个
ITEM_LIFETIME     = 20.0    # 道具在场时长（秒），原 15 → 20（+5s）
ITEM_FLASH_START  = 10.0    # 最后 10 秒进入"呼吸灯"提醒阶段（透明度正弦呼吸）
ITEM_BREATH_PERIOD = 1.5    # 呼吸灯周期（秒）：一个完整由暗到亮再回暗的来回
# 道具类型 -> 生成权重（加权随机抽选，数值仅表示相对出现概率；全模式统一生效）
ITEM_SPAWN_WEIGHTS = {
    "SHOTGUN": 26,   # 霰弹
    "SHIELD": 35,    # 护盾
    "SPEED": 25,     # 加速（有意压低：加速强度高的同时出现率调低）
    "LASER": 30,     # 激光（虚线预测 + 快速射线，一次性充能；激光出现率略高于霰弹）
    "MISSILE": 25,   # 追踪导弹（锁定最近坦克追击，可误伤自己；概率略低）
}

# ---------- 战斗空间 (Phase 5.3 Battle Space Foundation) ----------
# 是否启用确定性战斗空间布局；False 时回退到 Phase 5.2 地图（空地图 + 中央 LJR 拼字）。
BATTLE_SPACE_ENABLED = True

# ---------- 玩家坦克 ----------
TANK_SIZE = int(TILE_SIZE * 0.8)
TANK_SPEED = 150
COLOR_PLAYER_TANK = (204, 30, 30)
COLOR_PLAYER_OUTLINE = (40, 5, 5)

# ---------- 子弹 ----------
BULLET_SIZE = max(4, TILE_SIZE // 6)
BULLET_SPEED = 260
BULLET_MAX_BOUNCES = 2
BULLET_FIRE_COOLDOWN = 0.1
COLOR_BULLET = (255, 230, 120)        # 玩家子弹：亮黄色

# 霰弹道具 (Phase 5.4)：独立弹夹，一次发射 16 颗随机散射小弹丸
SHOTGUN_MAGAZINE = 5          # 独立弹夹：5 次射击机会，用尽后失效
SHOTGUN_PELLETS = 16          # 每次发射的弹丸数量
SHOTGUN_PELLET_SIZE = 4       # 小颗粒弹丸边长（像素，小于普通子弹）
SHOTGUN_SPEED = 320           # 弹丸初速（略快于普通子弹 260）
SHOTGUN_SPREAD_RADIANS = 0.5  # 散射半角（弧度），以当前朝向为中心随机扰动
SHOTGUN_DAMAGE = 1            # 每颗弹丸伤害

# ---------- 激光道具（虚线预测 + 快速射线）----------
# 拾取后一次性充能：坦克前方实时虚线预览实际弹道（固定 4 次反射）；
# 按发射键以极快速度射出，最多反射 LASER_MAX_BOUNCES 次，命中坦克或反射满即消失。
LASER_SPEED = 1200          # 激光飞行速度（像素/秒，约普通子弹 4.6 倍，观感"极快"）
LASER_MAX_BOUNCES = 10      # 实射激光最大反射次数
LASER_PREVIEW_BOUNCES = 4   # 虚线预览固定反射次数
LASER_WIDTH = 2             # 激光束线宽（像素）
LASER_TRAIL_LENGTH = 110.0  # 曳光拖尾弧长（像素）：头部以 LASER_SPEED 飞出，
                            # 光束按此弧长滞后头部展开（约 0.09s 行程），
                            # 出膛时拖尾为 0，随后整条光条脱离炮口
COLOR_LASER = (255, 238, 170)          # 激光束颜色（暖亮黄）
COLOR_LASER_PREVIEW = (255, 235, 120)  # 预测虚线颜色
LASER_PREVIEW_FLOW_SPEED = 65.0   # 虚线走马灯流动速度（像素/秒，沿路径朝落点方向；130 偏快再减半）
LASER_TRACE_STEP = 4.0      # 预计算/推进子步长（像素）：小于坦克边长，防高速穿透
LASER_TRACE_MAX_STEPS = 6000  # 轨迹追踪步数硬上限（兜底防死循环）
COLOR_PLAYER2_TANK = (60, 90, 210)  # P2 坦克颜色（蓝；与 entities/player2_tank.py 的 COLOR_P2_TANK 一致）
COLOR_PLAYER3_TANK = (46, 190, 92)  # P3 坦克颜色（绿；三人混战鼠标玩家，与 entities/player3_tank.py 的 COLOR_P3_TANK 一致）
# 激光颜色按发射方阵营走：虚线预览与实射激光共用同一映射（红方红 / 蓝方蓝 / 绿方绿）
COLOR_LASER_BY_OWNER = {
    "p1": COLOR_PLAYER_TANK,        # 红方激光（= P1 坦克本色）
    "p2": COLOR_PLAYER2_TANK,       # 蓝方激光（= P2 坦克本色）
    "p3": COLOR_PLAYER3_TANK,       # 绿方激光（= P3 坦克本色）
}
COLOR_LASER_FALLBACK = (255, 238, 170)  # owner 未知时的兜底色（原亮黄）

# ---------- 追踪导弹道具（MISSILE）----------
# 拾取 +1 发（可累计）。发射后沿炮口前飞；无目标直线巡航，锁定目标后弧线追击；
# 撞墙 10 秒寿命内无限反弹；10 秒寿命到头化作一团灰烟消失（无伤害）。
# 弹体/尾焰/尾烟颜色 = 当前目标坦克颜色（自伤宽限期后自己也可成为目标）。
# 锁定范围=弹头正前方 180° 扇形内最近者，且必须"看得见"：
# 导弹与目标中心连线被墙隔断则不可锁（不能隔着障碍物探测追踪）。
# 追踪强度：首次锁定后 5 秒全强度（MISSILE_TURN_RATE），随后每 1 秒降一档
# （0.6→0.35→0.15→0.05 倍），跑得快的目标持续拐弯即可甩开；换目标/丢锁
# 重锁均不重置计时（防"换目标续命"）。
MISSILE_MAGAZINE = 1               # 拾取一次获得的追踪弹数量（可累计叠加、不封顶）
MISSILE_SPEED = 1.0 * TANK_SPEED   # 用户口径"1 倍坦克移速"（150px/s，与坦克同速）
MISSILE_FUEL = 10.0                # 寿命（秒）：到头未命中则化灰烟消失
MISSILE_TURN_RATE = 2.6            # 追踪转向速率（弧度/秒）：越大拐弯越急（=全强度）
MISSILE_TRACK_FULL_TIME = 5.0      # 首次锁定后全强度追踪时长（秒）：内贴目标转弯
MISSILE_TRACK_DECAY_STEP = 1.0     # 衰减步长（秒）：全强度窗口后每步降一档
MISSILE_TRACK_DECAY_STAGES = (0.6, 0.35, 0.15, 0.05)  # 逐档转向速率乘数（只减不增）
MISSILE_GRACE = 0.35               # 发射后自伤宽限（秒）：防出膛即锁/撞自己
MISSILE_CONE_HALF_ANGLE = math.pi / 2  # 锁定扇形半角（弧度）：90° → 正前方 180° 扇形
MISSILE_RETARGET_INTERVAL = 0.15   # 重评"扇形内谁最近"的间隔（秒）：更近则转移目标
MISSILE_LOS_STEP = 20.0            # 视线采样步长（像素）：<格宽 40，保证不跳过整格墙
MISSILE_WARN_DISTANCE = int(TANK_SIZE * 7)  # "即将命中"音效触发距离（≈175px，6~8 车身取中）
MISSILE_SIZE = 10                  # 导弹碰撞/渲染尺寸（像素）
MISSILE_SUBSTEP = 8.0              # 每子步最大移动距离（像素）：小于坦克边长，防穿透
MISSILE_DISSOLVE_TIME = 0.5        # 寿命到头后灰烟消散持续时间（秒）
MISSILE_SND_FADEOUT = 0.4          # 导弹消失时自身各音效统一淡出（秒）
MISSILE_LOCK_FADEOUT = 0.3         # 锁定音效被"即将命中"顶替时的淡出（秒）
# 尾烟粒子（目标同色，向后扩散、逐渐变淡、像被风吹散）
MISSILE_SMOKE_PER_FRAME = 1        # 每帧喷出的烟粒数（1=稀，2=浓）
MISSILE_SMOKE_LIFE = 0.75          # 单颗粒子存活时长（秒）
MISSILE_SMOKE_SIZE_MIN = 2         # 初始半径下限（像素）
MISSILE_SMOKE_SIZE_MAX = 5         # 初始半径上限（像素）
MISSILE_SMOKE_EXPAND = 20.0        # 半径膨胀速度（像素/秒）
MISSILE_SMOKE_DRIFT = 55.0         # 随机漂移速度上限（像素/秒）
MISSILE_SMOKE_ALPHA = 115          # 初始不透明度（0~255；115=淡烟）
MISSILE_SMOKE_BURST = 14           # 寿命到头时一次性喷出的灰烟粒数

# ---------- 弹药（弹匣） ----------
MAGAZINE_CAPACITY = 5
RELOAD_DURATION = 4.0
COLOR_AMMO_FULL = (255, 230, 120)
COLOR_AMMO_EMPTY = (70, 70, 70)
COLOR_AMMO_RELOADING = (150, 120, 40)

# 换弹读条 UI（底部面板 AMMO 行：子弹打光进入换弹读秒时，图标行整体替换为读条）
# 样式与中场休息读条同款：浅灰轨道 + 高亮黑填充两端向中央收缩 + 高亮黑倒计时数字
RELOAD_UI_BAR_W = 110             # 读条宽度（px，= 满弹匣 5 × 图标槽宽 22）
RELOAD_UI_BAR_H = 8               # 读条高度
RELOAD_UI_BOTTOM_OFFSET = 2       # 读条底边距 AMMO 行底部的距离（落在行内空白带）
RELOAD_UI_TRACK = (210, 210, 215) # 轨道底色（浅灰细条，白底衬托收缩）
RELOAD_UI_FILL = (0, 0, 0)        # 收缩填充色（高亮纯黑，白底最醒目）
RELOAD_UI_NUM_SIZE = 18           # 倒计时数字字号（粗体圆润，略小于中场读条）
RELOAD_UI_NUM_COLOR = (0, 0, 0)   # 倒计时数字色（高亮黑）
RELOAD_UI_NUM_GAP = 8             # 数字与读条横向间距

# ---------- 出生区判定 ----------
# 供地图出生区回归脚本（_verify_830/831/832）使用：出生点距玩家安全距离（格数）
ENEMY_SPAWN_SAFE_DISTANCE = 10

# ---------- 物理系统 ----------
PHYSICS_ACCEL = 400.0              # 加速度 (px/s²)
PHYSICS_FRICTION = 2.0             # 运动中自然阻力系数 (1/s)，exp(-2·dt)
PHYSICS_TURN_SPEED = 5.0           # 转向速度 (rad/s)，约 286°/s（原 4.189≈240°/s，转得更跟手）
WALL_FRICTION_DAMPING = 1.5        # 墙摩擦阻尼系数 (1/s)（旧用，已移入 enemy 碰撞）
WALL_BASE_DAMPING = 0.1            # 围墙基础阻尼 (1/s)，仅 face_into_wall≈0 时生效
BRAKE_DECELERATION = 350.0         # 松键后线性刹车减速度 (px/s²)
REVERSE_SPEED_LIMIT = 0.9          # 倒车速度上限为前进最高速的 70%
REVERSE_ACCEL_FACTOR = 0.9        # 倒车加速度为前进的 85%

# ==================================================================
# 菜单界面 / 存档 / 音频 (Phase UI: 第一步 主菜单多级导航 + 音频 + 进度)
# ==================================================================

# ---------- 存档路径 ----------
# 从项目根目录启动（python main.py）时，存档文件落在项目根的 save/ 下。
SAVE_DIR = "save"
PROGRESS_FILE = os.path.join(SAVE_DIR, "progress.json")   # 关卡解锁进度
AUDIO_FILE = os.path.join(SAVE_DIR, "audio.json")         # 音量 / 静音设置

# ---------- 音频 ----------
# 预留音效资源目录：放置 <name>.wav 即可被 AudioManager 加载。
# 当前无真实音效文件时，AudioManager 会生成一段程序化「点击音」用于菜单反馈，保证音量系统立即可用。
SFX_DIR = "assets/sfx"
SFX_NAME_CLICK = "ui_click"   # 菜单点击音效键名（预留：ui_click.wav）

# ---------- 玩家开炮音效 ----------
# 用户提供的开炮音效（任意 wav/ogg/mp3 均可，由 AudioManager.register_sound 加载）。
# 路径按项目根目录（core/ 的上一级）解析，避免受运行 cwd 影响。
SFX_CANNON_FIRE = "cannon_fire"   # 开炮音效键名（play 时引用）
SFX_CANNON_FIRE_FILE = "开炮声cannon_fire.ogg"  # 音效文件名（位于项目根目录）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_CANNON_FIRE_PATH = os.path.join(_PROJECT_ROOT, SFX_CANNON_FIRE_FILE)
SFX_CANNON_FIRE_VOLUME = 0.5      # 开炮音效额外音量缩放（相对 effective，调小避免刺耳）

# ---------- 道具拾取音效 ----------
# 用户提供的拾取音效（原 MP3 已裁掉头部 ~1.07s 静音段、转 WAV，确保一捡到立刻出声）。
# 音量偏小，仅"能听见即可"，由 play(volume_scale) 控制。
SFX_ITEM_PICKUP = "item_pickup"   # 拾取音效键名
SFX_ITEM_PICKUP_FILE = "拾取道具的声音.wav"  # 音效文件名（位于项目根目录，已去静音头）
SFX_ITEM_PICKUP_PATH = os.path.join(_PROJECT_ROOT, SFX_ITEM_PICKUP_FILE)
SFX_ITEM_PICKUP_VOLUME = 0.35     # 拾取音效额外音量缩放（相对 effective，保持小音量）

# ---------- 激光射线发射音效 ----------
# 用户提供的激光道具音效（wav，时长 0.19s，短促）。
# 对标开炮音效：同为"玩家武器发射"行为，音量与 register/play 方式完全一致。
SFX_LASER_FIRE = "laser_fire"   # 激光发射音效键名（play 时引用）
SFX_LASER_FIRE_FILE = "激光道具音效.wav"  # 音效文件名（位于项目根目录）
SFX_LASER_FIRE_PATH = os.path.join(_PROJECT_ROOT, SFX_LASER_FIRE_FILE)
SFX_LASER_FIRE_VOLUME = 0.5      # 激光发射音效额外音量缩放（对标开炮音效）

# --- 追踪导弹音效（MP3；pygame 2.4 / SDL2_mixer 直接支持）---
SFX_MISSILE_FLIGHT = "missile_flight"           # 飞行音效键名（发射时播放一次，12.2s）
SFX_MISSILE_FLIGHT_FILE = "导弹飞行音效.MP3"
SFX_MISSILE_FLIGHT_PATH = os.path.join(_PROJECT_ROOT, SFX_MISSILE_FLIGHT_FILE)
SFX_MISSILE_FLIGHT_VOLUME = 0.5    # 飞行音效额外音量缩放
SFX_MISSILE_LOCK = "missile_lock"               # 锁定目标音效键名（每次锁定/换目标播放一次，11.1s）
SFX_MISSILE_LOCK_FILE = "导弹锁定目标时.MP3"
SFX_MISSILE_LOCK_PATH = os.path.join(_PROJECT_ROOT, SFX_MISSILE_LOCK_FILE)
SFX_MISSILE_LOCK_VOLUME = 0.6      # 锁定音效额外音量缩放
SFX_MISSILE_WARN = "missile_warn"               # 即将命中音效键名（贴近目标 4~5 车身时顶替锁定音，10.0s）
SFX_MISSILE_WARN_FILE = "导弹锁定目标即将命中时.MP3"
SFX_MISSILE_WARN_PATH = os.path.join(_PROJECT_ROOT, SFX_MISSILE_WARN_FILE)
SFX_MISSILE_WARN_VOLUME = 0.65     # 即将命中音效额外音量缩放（警告位，略响）
SFX_MISSILE_EXPLODE = "missile_explode"         # 命中爆炸音效键名（命中坦克/炸护盾时播放一次，1.3s）
SFX_MISSILE_EXPLODE_FILE = "导弹命中后爆炸音效.MP3"
SFX_MISSILE_EXPLODE_PATH = os.path.join(_PROJECT_ROOT, SFX_MISSILE_EXPLODE_FILE)
SFX_MISSILE_EXPLODE_VOLUME = 0.6   # 爆炸音效额外音量缩放

# ---------- 按钮悬停提示音效 ----------
# 用户提供的"碰到按钮"音效（鼠标移入可交互菜单按钮时播放一次）。
# 音量适中，用 volume_scale 压低避免盖过点击音 / 背景音乐。
SFX_NAME_HOVER = "button_hover"   # 悬停音效键名（play 时引用）
SFX_BUTTON_HOVER_FILE = "碰到按钮的声.wav"  # 音效文件名（位于项目根目录）
SFX_BUTTON_HOVER_PATH = os.path.join(_PROJECT_ROOT, SFX_BUTTON_HOVER_FILE)
SFX_BUTTON_HOVER_VOLUME = 0.1     # 悬停音额外音量缩放（相对 effective，极小幅，轻提示不打扰）

# ---------- 玩家坦克被摧毁爆炸音效 ----------
# 用户提供的爆炸录音（hjm-big_explosion_3.wav），仅取前 0.5s 作为短促爆炸冲击。
# 音量偏大，用 volume_scale 压到 0.6 避免盖过其它反馈。
SFX_PLAYER_DESTROYED = "player_destroyed"   # 玩家被摧毁爆炸音效键名
SFX_PLAYER_DESTROYED_FILE = "坦克爆炸声_player_destroyed_0.5s.wav"  # 音效文件名（项目根目录，已裁前 0.5s）
SFX_PLAYER_DESTROYED_PATH = os.path.join(_PROJECT_ROOT, SFX_PLAYER_DESTROYED_FILE)
SFX_PLAYER_DESTROYED_VOLUME = 0.6    # 玩家被摧毁爆炸音效额外音量缩放（相对 effective）

# ---------- 大厅主菜单背景音乐 (BGM) ----------
# 用户提供的主菜单音乐（ogg，时长约 225s）。要求：循环播放 + 最后 5s 渐隐 + 自然衔接。
# 实现：受控循环（非裸 loops=-1 硬跳），每段结构 = 头 2s 淡入 → 中段稳音量 → 尾 5s 淡出，
# 循环时首尾音量都为 0，听感为连续呼吸而非硬切。
# 音量并入主音量 master（随主音量滑块 + 静音开关变化），不单独占用音效音量轨。
SFX_BGM_MENU = "bgm_menu"                       # BGM 键名
SFX_BGM_MENU_FILE = "主菜单音乐.ogg"             # BGM 文件名（项目根目录）
SFX_BGM_MENU_PATH = os.path.join(_PROJECT_ROOT, SFX_BGM_MENU_FILE)
BGM_MENU_FADEIN = 2.0        # 开头淡入时长（秒）：头轻，避免开头突兀
BGM_MENU_FADEOUT = 5.0       # 结尾淡出窗口（秒）：最后 5s 渐隐
BGM_MENU_TARGET_VOLUME = 0.25 # BGM 相对主音量的目标音量（菜单乐不喧宾夺主，减半防初始音量 100% 过响）

# ---------- 第一关战斗 BGM ----------
# 用户提供的第一关音乐（mp3，pygame.mixer.Sound 可直接加载，无需转码）。
# 播放范围：PVP 进入第 1 关地图（selected_stage==0）战斗时。
SFX_BGM_STAGE1 = "bgm_stage_01"                # BGM 键名
SFX_BGM_STAGE1_FILE = "第一关音乐.mp3"          # BGM 文件名（位于项目根目录）
SFX_BGM_STAGE1_PATH = os.path.join(_PROJECT_ROOT, SFX_BGM_STAGE1_FILE)
BGM_STAGE1_FADEIN = 2.0       # 开头淡入时长（秒）：与菜单乐一致的自然进入
BGM_STAGE1_FADEOUT = 5.0      # 结尾淡出窗口（秒）：循环尾段渐隐，衔接自然
BGM_STAGE1_TARGET_VOLUME = 0.3  # BGM 相对主音量的目标音量（战斗乐略高于菜单乐，仍让位音效）
BGM_STOP_FADE = 3.0    # 离开战斗（进入结算/回菜单）时音乐淡出秒数：各关共用，柔和渐隐

# ---------- 第二关战斗 BGM ----------
# 用户提供的第二关音乐（flac，pygame.mixer.Sound 实测可直接加载，无需转码；时长约 76.7s）。
# 播放范围：PVP 进入第 2 关地图（selected_stage==1）战斗时。
SFX_BGM_STAGE2 = "bgm_stage_02"                # BGM 键名
SFX_BGM_STAGE2_FILE = "第二关音乐.mp3"       # BGM 文件名（由无损 FLAC 转码为 320k MP3，控制仓库体积）
SFX_BGM_STAGE2_PATH = os.path.join(_PROJECT_ROOT, SFX_BGM_STAGE2_FILE)
BGM_STAGE2_FADEIN = 2.0       # 开头淡入时长（秒）：与第一关一致的自然进入
BGM_STAGE2_FADEOUT = 5.0      # 结尾淡出窗口（秒）：循环尾段渐隐，衔接自然
BGM_STAGE2_TARGET_VOLUME = 0.3  # BGM 相对主音量的目标音量（战斗乐略高于菜单乐，仍让位音效）

# ---------- 第三关战斗 BGM ----------
# 用户提供的第三关音乐（mp3，与第一关同格式；pygame.mixer.Sound 实测可加载，无需转码；时长约 162.0s）。
# 播放范围：PVP 进入第 3 关地图（selected_stage==2）战斗时。
SFX_BGM_STAGE3 = "bgm_stage_03"                # BGM 键名
SFX_BGM_STAGE3_FILE = "第三关音乐.mp3"          # BGM 文件名（位于项目根目录）
SFX_BGM_STAGE3_PATH = os.path.join(_PROJECT_ROOT, SFX_BGM_STAGE3_FILE)
BGM_STAGE3_FADEIN = 2.0       # 开头淡入时长（秒）：与第一关一致的自然进入
BGM_STAGE3_FADEOUT = 5.0      # 结尾淡出窗口（秒）：循环尾段渐隐，衔接自然
BGM_STAGE3_TARGET_VOLUME = 0.3  # BGM 相对主音量的目标音量（战斗乐略高于菜单乐，仍让位音效）

# ---------- 第四关战斗 BGM ----------
# 用户提供的第四关音乐（mp3，与第一/三关同格式；pygame.mixer.Sound 实测可加载，无需转码；时长约 141.2s）。
# 播放范围：PVP 进入第 4 关地图（selected_stage==3）战斗时。
SFX_BGM_STAGE4 = "bgm_stage_04"                # BGM 键名
SFX_BGM_STAGE4_FILE = "第4关音乐.mp3"          # BGM 文件名（位于项目根目录）
SFX_BGM_STAGE4_PATH = os.path.join(_PROJECT_ROOT, SFX_BGM_STAGE4_FILE)
BGM_STAGE4_FADEIN = 2.0       # 开头淡入时长（秒）：与第一关一致的自然进入
BGM_STAGE4_FADEOUT = 5.0      # 结尾淡出窗口（秒）：循环尾段渐隐，衔接自然
BGM_STAGE4_TARGET_VOLUME = 0.3  # BGM 相对主音量的目标音量（战斗乐略高于菜单乐，仍让位音效）

# ---------- 关卡 → 战斗 BGM 映射 ----------
# 键：关卡索引（0 起，与 main.STAGES 对齐）；值：战斗 BGM 键名。
# 纯数据映射（settings 不依赖 pygame，可直接单测）；后续新关接入在此追加一行即可。
STAGE_BGM_MAP = {0: SFX_BGM_STAGE1, 1: SFX_BGM_STAGE2, 2: SFX_BGM_STAGE3, 3: SFX_BGM_STAGE4}

# ---------- 关卡战斗背景图（1~4 关共用）----------
# 用户提供的横图（720×474，JPEG 无透明），整窗非等比拉伸到 800×950 铺满
# （含底部白色状态栏，满足"覆盖到底部状态栏"需求）。
# 状态栏改为半透明白面纱（LEVEL_BG_UI_ALPHA）叠加：背景透出的同时深色 UI 仍清晰。
# 图片缺失/加载失败 或 LEVEL_BG_ENABLED=False 时自动回退旧行为
# （纯色底 + 不透明白带 255），是可回退开关。
LEVEL_BG_ENABLED = True                          # 总开关：False 完全还原现状（无背景图）
LEVEL_BG_IMAGE = "关卡背景.jpg"                  # 背景图文件名（位于项目根目录）
LEVEL_BG_PATH = os.path.join(_PROJECT_ROOT, LEVEL_BG_IMAGE)  # 路径按项目根解析，防 cwd 影响
LEVEL_BG_UI_ALPHA = 170                          # 状态栏白面纱透明度（0~255；255=不透明白带还原现状，越小图越透）
# 整图垂直下移量（px）：左上角商标/品牌标避开关卡顶部障碍物遮挡。
# 下移后在窗口顶部露出的条带，用"图片上边缘平均色 → 纯色底"的纵向渐变软填充，
# 观感自然；0 = 不下移（还原旧行为）。
LEVEL_BG_OFFSET_Y = 0    # 旧图有商标需下移 40px 避让；新 4 张关卡背景无此需求，设 0 使背景铺满整窗（顶部不留渐变缝）

# ---------- 菜单按钮布局 (几何集中在此，便于整体调整) ----------
GAME_VERSION = "v1.0.0"           # 版本号（首页页脚显示，按当前阶段手动维护）
MENU_BG_IMAGE = "首页图片.png"     # 主菜单背景图（项目根目录，缺失时回退纯色底）
MENU_BG_PATH = os.path.join(_PROJECT_ROOT, MENU_BG_IMAGE)  # 绝对路径（打包 exe 后仍能定位）
MENU_BG_CROP_MAX_RATIO = 0.15    # 底部黑色带裁切上限（占原图高度比例），防误裁大片暗区
MENU_BG_BLACK_THRESH = 30        # 行亮度均值低于此值判为黑色带（自动裁切用）
MENU_TITLE_IMAGE = "menu_title.jpg"  # 主菜单标题 Logo 图（缺失时回退用文字渲染标题）
MENU_TITLE_PATH = os.path.join(_PROJECT_ROOT, MENU_TITLE_IMAGE)  # 绝对路径（打包 exe 后仍能定位）
MENU_TITLE_W = 460                # 标题 Logo 显示宽度（高度按原图比例缩放）
MENU_FOOTER_H = 72                # 页脚栏高度（半透明白色背景 + 版权/作者/版本）
COLOR_FOOTER_BG = (255, 255, 255)      # 页脚栏底色（白，配合 FOOTER_BG_ALPHA 做半透明）
FOOTER_BG_ALPHA = 102                 # 页脚白底透明度（0~255，102 = 40%，透出主菜单背景）
COLOR_FOOTER_TEXT = (28, 28, 34)       # 页脚栏文字色（近黑深灰，半透明红褐底上确保清晰可见）
FOOTER_AUTHOR = "梁家睿"           # 作者
FOOTER_YEAR = "@2026"             # 版权年份
MENU_BTN_W = 260                 # 按钮宽
MENU_BTN_H = 56                  # 按钮高
MENU_BTN_GAP = 18                # 按钮垂直间距
MENU_TITLE_Y = 180               # 标题中心 y
MENU_BTN_TOP = 280               # 按钮列上边界（须在标题下方，避免遮挡游戏名）
MENU_VOLUME_STEP = 0.1           # 音量调节步长（0~1）
VOLUME_MIN = 0.0
VOLUME_MAX = 1.0

# ---------- 战斗暂停菜单 (Phase UI Step 1-B：ESC 暂停覆盖层) ----------
# 战斗中按 ESC 弹出；遮罩压暗全窗（含 UI 状态区），下层面面冻结（PAUSED 态不跑 update）。
# 暂停主菜单含"设置"入口 → 子页：游戏说明 / 音量 / 音效（复用主菜单的音量调节逻辑）。
PAUSE_OVERLAY_ALPHA = 140        # 暂停遮罩不透明度（0~255；介于局间提示 100 与结果 160 之间）
PAUSE_TITLE = "游戏暂停"          # 暂停面板主标题
PAUSE_SETTINGS_TITLE = "设置"     # 设置子页标题
PAUSE_HELP_TITLE = "游戏说明"     # 帮助子页标题
PAUSE_AUDIO_TITLE = "音量调节"    # 音量/音效子页标题（kind 附加显示）
PAUSE_TITLE_Y = 250              # 标题中心 y
PAUSE_INFO_TOP = 315             # 系列进度信息行 y（居中；仅在局制模式有值）
PAUSE_BTN_W = 260                # 暂停按钮宽（与主菜单按钮同尺寸）
PAUSE_BTN_H = 56                 # 暂停按钮高
PAUSE_BTN_GAP = 20               # 暂停按钮垂直间距
PAUSE_BTN_TOP = 360              # 按钮列上边界
PAUSE_BTN_LABELS = ("继续游戏", "重新本局", "设置", "返回主菜单")
PAUSE_SETTINGS_LABELS = ("返回", "游戏说明", "音量", "音效")
PAUSE_AUDIO_LABELS = ("＋ 增大", "－ 减小", "静音开关", "返回")
PAUSE_HELP_LABELS = ("返回",)
PAUSE_ALLOWED_DURING_INTRO = False  # 局间/开局提示期（round_over_pause>0）是否允许按 ESC 暂停
PAUSE_HOVER_BORDER = (255, 235, 160)  # 暂停按钮悬停高亮描边（金色，与主菜单聚焦一致）

# ---------- 结算界面（结果页档案卡） ----------
# 结果状态（VICTORY / GAME_OVER）：遮罩 + 顶部系列比分小字 + 模式差异化档案卡 + 返回按钮。
# 颜色与局间界面（_render_intermission）的 win/loss 收敛一致，保持视觉统一。
RESULT_TITLE_Y = 250             # 结果大字标题中心 y
RESULT_SERIES_TOP = 315          # 顶部系列比分小字中心 y（solo=P1方/PVP/…统一显示）
RESULT_CARD_TOP = 355            # 档案卡顶部 y（卡高随行数自适应，max 4 行 → 底 ≤ 527）
RESULT_CARD_W = 440              # 档案卡宽（水平居中）
RESULT_CARD_PAD_X = 24           # 卡内左右内边距
RESULT_CARD_PAD_Y = 18           # 卡内上下内边距
RESULT_CARD_LINE_GAP = 34        # 卡内行间距（标签行与大比分行共用）
RESULT_CARD_BG = (24, 26, 32)    # 档案卡底色（深灰蓝）
RESULT_CARD_BORDER = (120, 120, 132)  # 档案卡描边框
RESULT_LABEL_COLOR = (180, 182, 192)  # 档案卡标签色（克制档案系）
RESULT_VALUE_COLOR = (255, 255, 255)  # 档案卡数值色
RESULT_WIN_COLOR = (50, 255, 120)     # 胜利绿（与局间 win 一致）
RESULT_LOSE_COLOR = (255, 50, 50)     # 战败红（与局间 loss 一致）
RESULT_BTN_W = 220               # 返回按钮宽
RESULT_BTN_H = 56                # 返回按钮高
RESULT_BTN_TOP = 560             # 返回按钮顶 y（档案卡下方，原 530 上移下放以避开卡）

# ---------- 高亮指示三角（悬停/选中态按钮左右各一，尖端指向按钮） ----------
TRIANGLE_HALF_RATIO = 0.32   # 三角半高 = 按钮高 × 该比例（随按钮高，避免过扁/过大）
TRIANGLE_LEN = 12            # 三角尖端到底边的水平长度（px）
TRIANGLE_GAP = 6             # 三角底边与按钮边缘的间隙（px）
TRIANGLE_ANIM_AMPLITUDE = 4.0  # 镜像摆动峰值幅度（px；须 ≤ TRIANGLE_GAP，防止尖端刺入按钮/字体）
TRIANGLE_ANIM_SPEED = 5.2      # 摆动角速度 rad/s（约 1.2s 一个来回）

# ---------- 选关地图预览卡（悬停关卡按钮时按钮右侧弹出迷你图） ----------
PREVIEW_CELL_SIZE = 7          # 迷你图每格像素（25 格 → 175px，细节可辨）
PREVIEW_GROUND = (232, 232, 236)   # 空地底色（浅档案灰）
PREVIEW_BRICK = (150, 96, 60)      # 砖墙（暖砖色）
PREVIEW_STEEL = (70, 74, 80)       # 钢墙（深钢色）
PREVIEW_CARD_BG = (248, 248, 250)  # 卡片底（近白档案卡）
PREVIEW_CARD_BORDER = (185, 187, 195)  # 卡片描边
PREVIEW_CARD_RADIUS = 8         # 卡片圆角
PREVIEW_CARD_PAD = 10           # 卡片内边距
PREVIEW_LABEL_H = 22            # 标签行高
PREVIEW_LABEL_GAP = 6           # 标签与迷你图间距
PREVIEW_LABEL_COLOR = (25, 26, 30)  # 标签文字色
PREVIEW_GAP = 16                # 按钮右缘 → 卡片左缘间距
PREVIEW_SCALE_MIN = 0.7         # 弹出起始缩放（0.7 → 1.0 缓出）
PREVIEW_SLIDE = 10              # 弹出上浮像素（随进度淡出）
PREVIEW_SMOOTH = 14.0           # 指数平滑系数（越大越快，帧率无关）
PREVIEW_LABEL_SIZE = 16         # 卡片标签字号（中文字体）

# ---------- PVP 随机地图转盘（开图动画，CSGO 开箱式） ----------
# 播放时长每次开图随机抽取于 [MIN, MAX]；MAX 恒为上限 5 秒，绝不超过。
PVP_ROULETTE_DURATION_MIN = 2.0   # 随机时长下限（秒）
PVP_ROULETTE_DURATION_MAX = 5.0   # 随机时长上限（秒），恒 ≤ 5
PVP_ROULETTE_CELL = 5             # 转盘卡带迷你图每格像素（25 格 → 125px）
PVP_ROULETTE_CARD_GAP = 12        # 卡带相邻卡片间距（px）
PVP_ROULETTE_SLOTS = 7            # 转盘可见槽位数（奇数，中央槽=选中位）
PVP_ROULETTE_SPIN_CARDS = 24      # 滚动总位移（卡片数，含收尾对齐量）
PVP_ROULETTE_LABEL_SIZE = 16      # 卡片地图名标签字号
PVP_ROULETTE_ARROW = (70, 70, 70)   # 选中箭头色（深灰，深于判定线 120 灰，层次分明）
PVP_ROULETTE_LINE = (120, 120, 120)   # CSGO 判定线色（中性灰，贯穿卡带）
PVP_ROULETTE_CAPTION_SIZE = 26         # 落定状态文字字号（圆润粗体：微软雅黑 + bold）
PVP_ROULETTE_STRIP_Y = 250        # 卡带行顶 y（须在标题 MENU_TITLE_Y=180 之下，避免遮挡标题）
PVP_ROULETTE_RESULT_Y = 610       # 落定结果按钮行顶 y（页脚 728 / 底部提示 688 之上，留有留白）
PVP_ROULETTE_FINAL_INSET = 8      # 落定点距卡片边缘最小留白（px）：保证指针绝不落缝、绝不贴边

# ---------- 菜单文字 ----------
HELP_TEXT = [
    "—— 双人对战 ——",
    "玩家一：移动 WASD    攻击 J",
    "玩家二：移动 方向键  攻击 空格",
    "",
    "—— 道具与弹药 ——",
    "子弹为弹匣制（5发），射空自动换弹",
    "护盾 / 加速 / 霰弹 拾取后限时生效",
    "霰弹枪为独立弹夹（5次），一次散射16发",
    "",
    "—— 胜负条件 ——",
    "击杀对方一次得 1 分",
    "系列赛先胜（对局数+1)/2 局者获胜",
]