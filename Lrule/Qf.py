#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/05 03:40
# @Author  : Wu_RH
# @FileName: Qf.py

from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleQf(AbstractMinesRule):
    id = "Qf"
    name = "Squarefree"
    name.zh_CN = "免费的正方形"
    doc = "No four mines form the vertices of a square."
    doc.zh_CN = "雷不能同时是一个正方形的四个角(包括倾斜的)"
    author = ("Boi", -1)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for board_key in board.get_interactive_keys():
            size = board.get_config(board_key, "size")
            for dx in range(size[1]):
                for dy in range(size[0]):
                    if dx == 0 and dy == 0:
                        continue
                    for pos1, _ in board(key=board_key):
                        pos2 = pos1.shift(dx, dy)
                        pos3 = pos1.shift(dy, -dx)
                        pos4 = pos1.shift(dx + dy, dy - dx)
                        if any(not board.is_valid(pos) for pos in (pos2, pos3, pos4)):
                            continue
                        var_list = [board.get_variable(pos) for pos in (pos1, pos2, pos3, pos4)]
                        model.AddBoolOr([var.Not() for var in var_list]).OnlyEnforceIf(s)
