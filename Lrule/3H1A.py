#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/02/15
# @Author  : xxx
# @FileName: 3H1A.py
"""
[3H1A] 六角无马步: 所有雷的UN UE NW ES DW DS的位置不能有雷
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule3H1A(AbstractMinesRule):
    name = ["3H1A", "Hex1A", "六角无马步", "Anti-Knight-Hex"]
    doc = "六角无马步: 所有雷的UN UE NW ES DW DS的位置不能有雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        for key in board.get_board_keys():
            board.set_config(key, "grid_type", "hex")

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        b = switch.get(model, self)

        for pos, var in board(mode="variable"):
            pos_list = [
                pos.up().north(),
                pos.up().east(),
                pos.north().west(),
                pos.east().south(),
                pos.down().west(),
                pos.down().south(),
            ]
            var_list = board.batch(pos_list, mode="variable", drop_none=True)
            for _var in var_list:
                model.AddBoolOr([_var.Not(), var.Not()]).OnlyEnforceIf(b)
