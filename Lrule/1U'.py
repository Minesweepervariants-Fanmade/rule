#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:35
# @Author  : Wu_RH
# @FileName: 1U.py
"""
[1U] 一元 (Unary)：所有雷不能与其他雷相邻
"""
import itertools
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1H(AbstractMinesRule):
    name = ["1U'", "一元'", "Unary'"]
    doc = "所有雷不能与其他雷相邻或对角相邻"
    subrules = [
        [True, "[1U]一元'"]
    ]

    def create_constraints(self, board: 'AbstractBoard', switch):
        if not self.subrules[0][0]:
            return
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            for dx, dy in itertools.product([-1, 0, 1], repeat=2):
                if dx == 0 and dy == 0: continue
                nei = pos.shift(dx, dy)
                if board.in_bounds(nei):
                    model.Add(board.get_variable(nei) == 0).OnlyEnforceIf([var, s])
