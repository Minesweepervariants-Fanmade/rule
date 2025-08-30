#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/11 14:25
# @Author  : xxx
# @FileName: 1D.py
"""
[1D]对偶: 雷均有1x2或2x1的矩阵组成
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1D(AbstractMinesRule):
    name = ["1D", "D", "对偶"]
    doc = "雷均有1x2或2x1的矩阵组成"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, _ in board():
            positions = pos.neighbors(1)
            # sum(vals) 表示周围雷数
            sum_vals = sum(board.batch(positions, mode="variable", drop_none=True))
            val = board.get_variable(pos)
            # val 为1时，vals中必须有且仅有一个1
            # 约束：val=1 => sum(vals) == 1
            model.Add(sum_vals == 1).OnlyEnforceIf([val, s])

    def suggest_total(self, info: dict):
        def a(model, total):
            model.AddModuloEquality(0, total, 2)
        info["hard_fns"].append(a)
