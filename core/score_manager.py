# -*- coding: utf-8 -*-
"""
Phase 6.4 - Score Manager（独立分数系统数据层）
Phase 7.1 - 扩展击毁数量统计（kill_count / add_kill）

职责（只管分数与击毁数据，不做任何判断/流程/HUD）：
  - 当前分数（current_score）
  - 增加分数（add_score）
  - 当前击毁数量（kill_count）
  - 击毁数量 +1（add_kill）
  - 分数重置（reset）

不负责（由 Game 层负责）：
  - 击杀计分时机 -> main 层在 PVP 击杀时把价值算好传入 add_score(amount)
  - 系列赛判定    -> RoundManager + Game
  - 面板显示      -> 渲染层读取 current_score / kill_count

注意：
  - add_score 的原有行为不变（只加分数）；add_kill 仅由 Game 层在 PVP 击杀分支调用。

纯粹数据容器，不含游戏规则 / 不依赖 pygame，便于 headless 单元测试。
"""

class ScoreManager:
    """分数与击毁数据管理器：累计 / 读取 / 复位。

    Phase 8.0：新增单关数据（stage_score / stage_kill_count）。
    Total（_score / _kill_count）跨关保留；单关数据在进入下一关时由
    reset_stage() 归零（Total 不受影响）。
    """

    def __init__(self):
        self._score = 0
        self._kill_count = 0
        # Phase 8.0：单关分数 / 单关击毁（进入下一关时归零）
        self._stage_score = 0
        self._stage_kill_count = 0

    @property
    def current_score(self) -> int:
        """读取当前分数。"""
        return self._score

    @property
    def kill_count(self) -> int:
        """读取当前击毁数量（仅统计被玩家击毁的敌人）。"""
        return self._kill_count

    @property
    def stage_score(self) -> int:
        """读取当前单关分数（进下一关时归零）。"""
        return self._stage_score

    @property
    def stage_kill_count(self) -> int:
        """读取当前单关击毁数量（进下一关时归零）。"""
        return self._stage_kill_count

    def add_score(self, amount: int = 0) -> None:
        """增加分数（amount 为调用方已算好的分值）。原行为保持不变。"""
        self._score += amount

    def add_kill(self) -> None:
        """击毁数量 +1。仅 Game 层在敌人被击毁分支调用；Wave/Victory 奖励不算击杀。"""
        self._kill_count += 1

    def add_stage_score(self, amount: int = 0) -> None:
        """增加单关分数（仅记录当前 Stage）。不改变 Total 分数。"""
        self._stage_score += amount

    def add_stage_kill(self) -> None:
        """单关击毁数量 +1（仅记录当前 Stage）。不改变 Total 击毁数。"""
        self._stage_kill_count += 1

    def reset_stage(self) -> None:
        """单关数据清零（进入下一关时调用）。Total 分数/击毁数不受影响。"""
        self._stage_score = 0
        self._stage_kill_count = 0

    def reset(self) -> None:
        """总分 / 总击毁 / 单关分数 / 单关击毁全部清零。"""
        self._score = 0
        self._kill_count = 0
        self._stage_score = 0
        self._stage_kill_count = 0