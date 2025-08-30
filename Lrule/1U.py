#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:35
# @Author  : Wu_RH
# @FileName: 1U.py
"""
[1U] 一元 (Unary)：所有雷不能与其他雷相邻
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1H(AbstractMinesRule):
    name = ["1U", "一元", "Unary"]
    doc = "所有雷不能与其他雷相邻"
    subrules = [
        [True, "[1U]一元"]
    ]

    def create_constraints(self, board: 'AbstractBoard', switch):
        if not self.subrules[0][0]:
            return
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            if board.in_bounds(pos.down()):
                model.Add(board.get_variable(pos.down()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.up()):
                model.Add(board.get_variable(pos.up()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.right()):
                model.Add(board.get_variable(pos.right()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.left()):
                model.Add(board.get_variable(pos.left()) == 0).OnlyEnforceIf([var, s])
