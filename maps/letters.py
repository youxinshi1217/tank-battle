# -*- coding: utf-8 -*-
"""
LJR 拼字图案定义
三个字母的像素点阵，每个字母用 7×7 的 0/1 矩阵表示。
LETTER_WIDTH / LETTER_HEIGHT 控制单个字母占用网格数，
LETTER_GAP 控制字母之间的间距网格数。
"""
# 字母 L (5×5)
L_PATTERN = [
    "01000",
    "01000",
    "01000",
    "01000",
    "01110",
]
# 字母 J (5×5)
J_PATTERN = [
    "011110",
    "000100",
    "000100",
    "010100",
    "011100",
]
# 字母 R (5×5)
R_PATTERN = [
    "011110",
    "010010",
    "011110",
    "010100",
    "010010",
]
LJR_SEQUENCE = [L_PATTERN, J_PATTERN, R_PATTERN]
LETTER_WIDTH = 5
LETTER_HEIGHT = 5
LETTER_GAP = 0

