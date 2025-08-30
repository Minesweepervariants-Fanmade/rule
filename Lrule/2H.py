#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:37
# @Author  : Wu_RH
# @FileName: 2H.py
"""
[2H] 横向 (Horizontal)：所有雷必须存在横向相邻的雷
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule2H(AbstractMinesRule):
    name = ["2H", "横向", "Horizontal"]
    doc = "所有雷必须存在横向相邻的雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            if not board.in_bounds(pos.right()):
                model.Add(board.get_variable(pos.left()) == 1).OnlyEnforceIf([var, s])
            elif not board.in_bounds(pos.left()):
                model.Add(board.get_variable(pos.right()) == 1).OnlyEnforceIf([var, s])
            else:
                model.AddBoolOr(board.batch([pos.right(), pos.left()], mode="variable")).OnlyEnforceIf([var, s])
