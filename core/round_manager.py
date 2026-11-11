# -*- coding: utf-8 -*-
"""
系列赛局次管理（纯逻辑层，不依赖 pygame）。

职责（只记账，不做胜负判定）：
  - 当前局号 current_round
  - A/B 两方胜局计数（side_a_wins / side_b_wins）
  - 本局是否已结束 round_over
  - 系列赛是否决出胜负 match_over
  - 单局归属由 Game 层判定后调用 record_round(side_a_win) 记账

判定边界（在 Game 层执行，此处只存账）：
  - match_over = side_a_wins == win_needed 或 side_b_wins == win_needed
"""
from core.match_config import get_win_rounds_from_n


class RoundManager:
    """系列赛(N局, 先赢W局)局次记账。

    局数来源：调用方传入 rounds（PVP 对局数选择），胜局 = ceil(N/2)。
    """

    def __init__(self, mode: str, difficulty: str = None, rounds: int = None):
        self.mode = mode
        self.rounds_total = rounds
        self.win_needed = get_win_rounds_from_n(rounds)
        self.current_round = 1
        self.side_a_wins = 0        # PVP=P1
        self.side_b_wins = 0        # PVP=P2
        self.side_c_wins = 0        # 三人混战（pvp3）=P3（1v1 恒为 0）
        self.round_over = False
        self.match_over = False

    def record_round(self, side_a_win: bool) -> None:
        """结算本局：计入胜方胜局数；若已达胜局数则系列赛结束。

        Args:
            side_a_win: True=side_a 赢本局，False=side_b 赢本局。
        """
        if self.match_over or self.round_over:
            return                      # 幂等：已结算则忽略
        if side_a_win:
            self.side_a_wins += 1
        else:
            self.side_b_wins += 1
        self.round_over = True
        if (self.side_a_wins >= self.win_needed
                or self.side_b_wins >= self.win_needed):
            self.match_over = True
        else:
            self.current_round += 1     # 系列未结束，进入下一局

    def record_win(self, side: str) -> None:
        """三人混战（pvp3）通用记账：按 side（'a'/'b'/'c'）计一胜局；
        任一达胜局数则系列赛结束。1v1 请继续用 record_round()。

        Args:
            side: 'a'=玩家一 / 'b'=玩家二 / 'c'=玩家三。
        """
        if self.match_over or self.round_over:
            return                      # 幂等：已结算则忽略
        if side == "a":
            self.side_a_wins += 1
        elif side == "b":
            self.side_b_wins += 1
        elif side == "c":
            self.side_c_wins += 1
        else:
            return
        self.round_over = True
        if (self.side_a_wins >= self.win_needed
                or self.side_b_wins >= self.win_needed
                or self.side_c_wins >= self.win_needed):
            self.match_over = True
        else:
            self.current_round += 1     # 系列未结束，进入下一局

    @property
    def a_win(self) -> bool:
        """系列赛最终是否由 side_a 获胜（match_over 时才有意义）。"""
        return self.side_a_wins >= self.win_needed

    def reset_for_round(self) -> None:
        """进入下一局前的战场复位（不清胜局账）。Game 层据此重载战场。"""
        self.round_over = False
