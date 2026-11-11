# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # ---- 字体 ----
        # 源码仓库不分发中文字体（版权原因）。core/game_fonts.py 会按已知路径
        # 加载操作系统自带的中文字体，因此打包时无需内置字体文件。
        # 若自备了可自由分发的字体并放入 fonts/，请把下一行取消注释：
        # ('fonts/NotoSansCJK-Regular.ttc', 'fonts'),
        # ---- 图片（菜单 / 关卡背景 / 道具 / 玩家图标）----
        ('首页图片.png', '.'),
        ('menu_title.jpg', '.'),
        ('关卡背景.jpg', '.'),
        ('加速道具.png', '.'),
        ('护盾道具.jpg', '.'),
        ('霰弹道具.png', '.'),
        ('激光道具图标.png', '.'),
        ('坦克炮弹弹匣图标.png', '.'),
        ('霰弹显示图标.png', '.'),
        ('红色坦克图标.png', '.'),
        ('蓝色坦克图标.png', '.'),
        ('preview_map_01.png', '.'),
        ('preview_map_02.png', '.'),
        ('preview_map_03.png', '.'),
        # ---- 音效（开炮 / 拾取 / 悬停 / 爆炸 / 激光发射）----
        ('开炮声cannon_fire.ogg', '.'),
        ('拾取道具的声音.wav', '.'),
        ('碰到按钮的声.wav', '.'),
        ('坦克爆炸声_player_destroyed_0.5s.wav', '.'),
        ('激光道具音效.wav', '.'),
        # ---- BGM（菜单 / 各关卡）----
        ('主菜单音乐.ogg', '.'),
        ('第一关音乐.mp3', '.'),
        ('第二关音乐.mp3', '.'),
        ('第三关音乐.mp3', '.'),
        ('第4关音乐.mp3', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='tank_battle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
