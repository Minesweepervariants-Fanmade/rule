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
from minesweepervariants.board import Board


class Rule1H(AbstractMinesRule):
    id = "1U"
    aliases = ("U",)
    name = "Unary"
    name.zh_CN = "一元"
    doc = "No mine is adjacent to another mine"
    doc.zh_CN = "所有雷不能与其他雷相邻"

    tags = ["Creative", "Anti-Construction", "Local", "Strict R"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch):
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

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.295, 0)
