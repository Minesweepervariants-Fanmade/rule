# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:28
# @Author  : Wu_RH
# @FileName: 1H.py
"""
[1H] 横向 (Horizontal)：所有雷不能与其他雷横向相邻
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1H(AbstractMinesRule):
    name = ["1H", "H", "横向", "Horizontal"]
    doc = "所有雷不能与其他雷横向相邻"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            if board.in_bounds(pos.right()):
                model.Add(board.get_variable(pos.right()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.left()):
                model.Add(board.get_variable(pos.left()) == 0).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total
        def a(model, total):
            s = model.NewIntVar(0, 2, "s")
            model.AddModuloEquality(s, total, 2)
            model.AddHint(s, 0)
            model.Add(s != 1)
        info["soft_fn"](ub * 0.295, 0)
        info["hard_fns"].append(a)
