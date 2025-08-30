#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 18:09
# @Author  : Wu_RH
# @FileName: 2Z.py
"""
[2Z] 零和 (Zero-Sum)：每行的染色格与非染色格的雷数相等
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule2Z(AbstractMinesRule):
    name = "2Z", "零和", "Zero-Sum"
    doc = "每行的染色格与非染色格的雷数相等"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            for _pos in board.get_col_pos(bound):
                line = board.get_row_pos(_pos)
                line_dye = board.batch(line, mode="dye")
                line_var = board.batch(line, mode="variable")
                vars_a = []
                vars_b = []
                for var, dye in zip(line_var, line_dye):
                    if dye:
                        vars_a.append(var)
                    else:
                        vars_b.append(var)
                model.Add(sum(vars_a) == sum(vars_b)).OnlyEnforceIf(s)
