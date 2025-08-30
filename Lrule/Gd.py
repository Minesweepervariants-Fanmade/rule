#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/28 15:59
# @Author  : Wu_RH
# @FileName: Gd.py
"""
[Gd]: 每列雷数不少于左一列雷数；每行雷数不少于上一行雷数
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleGd(AbstractMinesRule):
    name = ["Gd", "GD"]
    doc = "1.每行值不大于上一行 2.每列值不大于左一列"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)
        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            col_positions = board.get_col_pos(boundary_pos)
            col_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_row_pos(pos))
                for pos in col_positions
            ]
            # 所有 col_sums 相等
            for i in range(1, len(col_sums)):
                model.Add(col_sums[i - 1] <= col_sums[i]).OnlyEnforceIf(s1)

            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            # 所有 row_sums 相等
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i - 1] <= row_sums[i]).OnlyEnforceIf(s2)
