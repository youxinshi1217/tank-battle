# -*- coding: utf-8 -*-
"""
游戏状态管理框架 (Phase 6.0 Game State Foundation)

定义游戏基础状态机：
    MENU      —— 菜单（本阶段未接入 UI，仅保留定义）
    PLAYING   —— 战斗进行中（保持现有战斗 update/render 逻辑）
    PAUSED    —— 暂停（本阶段未接入暂停 UI / 按键，仅保留定义）
    GAME_OVER —— 玩家被摧毁（战斗结束，停止更新）
    VICTORY   —— 通关胜利（战斗结束，停止更新）

使用 from enum import Enum，保证状态可序列化、可比较、可扩展。
本模块不依赖 pygame 以外的任何代码，属于纯定义层。
"""
import enum


class GameState(enum.Enum):
    """游戏状态枚举。"""

    MENU = "MENU"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"
    VICTORY = "VICTORY"