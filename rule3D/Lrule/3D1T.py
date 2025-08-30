#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/15 11:59
# @Author  : Wu_RH
# @FileName: 1T.py

"""
[3D1T]无三连: 雷不能在横竖对角构成三连
"""

from .. import Abstract3DMinesRule
from .....abs.board import AbstractBoard


class Rule1T(Abstract3DMinesRule):
    name = ["3D1T", "无三连"]
    doc = "雷不能在横竖对角构成三连"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, _ in board():
            for positions in [
                [pos, pos.left(), pos.left().left()],
                [pos, pos.down(), pos.down().down()],
                [pos, pos.left().down(), pos.left().down().left().down()],
                [pos, pos.left().up(), pos.left().up().left().up()],
                [pos, self.up(board, pos), self.up(board, pos, 2)],
                [pos, self.up(board, pos.left()), self.up(board, pos.left(2), 2)],
                [pos, self.up(board, pos.up()), self.up(board, pos.up(2), 2)],
                [pos, self.up(board, pos.up().left()), self.up(board, pos.up(2).left(2), 2)],
            ]:
                if None in positions:
                    continue
                var_list = board.batch(positions, mode="variable")
                if True in [None is i for i in var_list]:
                    continue
                model.Add(sum(var_list) != 3).OnlyEnforceIf(s)
