# -*- coding: utf-8 -*-
"""
Phase 8.0 - Level Manager（关卡流程管理，纯逻辑层）

职责（只负责）：
  - Stage 管理（多 Stage 列表驱动）
  - 地图切换（advance_stage）
  - 关卡流程（start_game_at 指定关开局）

不负责（保留给各自管理）：
  - 分数（ScoreManager）
  - 玩家状态（PlayerTank）
  - 战斗逻辑（main.Game）

设计：
  - 不依赖 pygame。
  - LevelManager 由 main.py 以 STAGES 列表构造（每个元素为 stage_XX.py 的
    STAGE_CONFIG，只存引用，不存大量数据）。
  - 后续追加多 Stage：向 STAGES 列表追加 map_XX/stage_XX/wave_XX 数据文件即可，
    无需改核心代码。
"""


class LevelManager:
    """多 Stage 关卡流程管理。"""

    def __init__(self, stages):
        if not stages:
            raise ValueError("LevelManager 需要至少一个 Stage 配置")
        self.stages = list(stages)
        self.current_stage = self.stages[0]
        self._index = 0

    # ------------------------------------------------------------------
    # 对外查询
    # ------------------------------------------------------------------
    @property
    def stage_number(self) -> int:
        """当前阶段编号（1 起）。"""
        return self._index + 1

    @property
    def total_stages(self) -> int:
        """总 Stage 数量。"""
        return len(self.stages)

    @property
    def is_last_stage(self) -> bool:
        """是否为最后一关。"""
        return self._index >= len(self.stages) - 1

    # ------------------------------------------------------------------
    # 对外操作
    # ------------------------------------------------------------------
    def start_game_at(self, index: int) -> None:
        """从指定关开始（Phase UI：选关开局，第 index 关，0 起索引）。"""
        if not (0 <= index < len(self.stages)):
            raise IndexError(f"无效的关卡索引: {index}")
        self._index = index
        self.current_stage = self.stages[index]

    def advance_stage(self) -> bool:
        """推进到下一关。

        Returns:
            bool：非末关推进成功返回 True；末关返回 False（不推进）。
        """
        if self.is_last_stage:
            return False
        self._index += 1
        self.current_stage = self.stages[self._index]
        return True

    # ------------------------------------------------------------------
    # 数据访问（从 current_stage 取出引用）
    # ------------------------------------------------------------------
    def get_map_data(self):
        """返回当前 Stage 的地图数据构建函数（Map Data 引用）。"""
        return self.current_stage["map_data"]