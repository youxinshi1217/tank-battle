# -*- coding: utf-8 -*-
"""
统一的字体创建工具（源码发布版）。

禁止在游戏代码中直接调用 pygame.font.SysFont / match_font：
它们会触发 pygame 的系统字体枚举（读 Windows 注册表字体项）。在
PyInstaller 打包的 exe 环境中，若注册表里存在值为整数（DWORD）的字体项，
枚举会在 ntpath.splitext 处崩溃：
    TypeError: expected str, bytes or os.PathLike object, not int
该错误与用户机器注册表内容有关，极难排查。

因此本模块只按「已知路径」逐个尝试加载字体，绝不枚举系统字体：
    1. 项目 fonts/ 下自备的字体（源码仓库不分发字体文件，版权原因）
    2. 各操作系统自带中文字体的标准安装路径
    3. pygame 默认字体（兜底，此时中文会显示为方块）
"""
import os
import sys

import pygame

_RESOURCE_BASE = getattr(
    sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

_FONT_CANDIDATES = [
    # 1) 自备字体（放 fonts/ 下，不随仓库分发）
    os.path.join(_RESOURCE_BASE, "fonts", "msyh.ttc"),
    os.path.join(_RESOURCE_BASE, "fonts", "NotoSansCJK-Regular.ttc"),
    os.path.join(_RESOURCE_BASE, "fonts", "SourceHanSansSC-Regular.otf"),
    # 2) Windows 自带
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    # 3) macOS 自带
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    # 4) Linux 常见中文字体
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]

_font_path = None
for _candidate in _FONT_CANDIDATES:
    if os.path.exists(_candidate):
        _font_path = _candidate
        break


def game_font(size: int, bold: bool = False):
    """创建字体对象。数字/英文与中文统一用同一个字体，避免系统枚举。"""
    if _font_path:
        font = pygame.font.Font(_font_path, size)
    else:
        font = pygame.font.Font(None, size)
    font.set_bold(bold)
    return font
