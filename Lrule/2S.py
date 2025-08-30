#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 18:32
# @Author  : Wu_RH
# @FileName: 2S.py
"""
[2S] 分段 (Segment)：每行有且仅有一组连续的雷
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule2S(AbstractMinesRule):
    name = ["2S", "分段", "Segment"]
    doc = "每行有且仅有一组连续的雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            d_pos = board.boundary(key)
            for pos in board.get_col_pos(d_pos):
                line = board.get_row_pos(pos)
                line_var = board.batch(line, mode="variable")
                model.AddBoolOr(line_var)
                for index, var in enumerate(line_var[:-1]):
                    model.Add(sum(line_var[index + 1:]) == 0).OnlyEnforceIf([var, line_var[index + 1].Not(), s])
                for index, var in enumerate(line_var[1:]):
                    model.Add(sum(line_var[:index+1]) == 0).OnlyEnforceIf([var, line_var[index].Not(), s])
