#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1B±]弱平衡：相邻两行或两列中的雷数之差不超过1
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch


class Rule1Bpm(AbstractMinesRule):
    id = "1B±"
    aliases = ("B±",)
    name = "Weak Balance"
    name.zh_CN = "弱平衡"
    doc = "The difference in mine counts between adjacent rows or columns does not exceed 1"
    doc.zh_CN = "相邻两行或两列中的雷数之差不超过1"
    tags = ["Variant", "Global", "Weak"]
    creation_time = "2026-05-26"
    author = ("NT", 2201963934)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)
            
            # 行约束
            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(pos) for pos in board.get_col_pos(row_pos))
                for row_pos in row_positions
            ]
            for i in range(len(row_sums) - 1):
                # |row_sums[i] - row_sums[i+1]| <= 1
                model.Add(row_sums[i] - row_sums[i+1] <= 1).OnlyEnforceIf(s)
                model.Add(row_sums[i+1] - row_sums[i] <= 1).OnlyEnforceIf(s)

            # 列约束
            col_positions = board.get_col_pos(boundary_pos)
            col_sums = [
                sum(board.get_variable(pos) for pos in board.get_row_pos(col_pos))
                for col_pos in col_positions
            ]
            for i in range(len(col_sums) - 1):
                # |col_sums[i] - col_sums[i+1]| <= 1
                model.Add(col_sums[i] - col_sums[i+1] <= 1).OnlyEnforceIf(s)
                model.Add(col_sums[i+1] - col_sums[i] <= 1).OnlyEnforceIf(s)
