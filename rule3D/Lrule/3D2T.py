#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/15 11:59
# @Author  : Wu_RH
# @FileName: 3D2T.py

"""
[3D2T]无三连: (1)雷不能在横竖上下向构成三连, (2)非雷不能在横竖上下向构成三连
"""

from .. import Abstract3DMinesRule
from .....abs.board import AbstractBoard


class Rule2T(Abstract3DMinesRule):
    name = ["3D2T", "无三连"]
    doc = "(1)雷不能在横竖上下向构成三连, (2)非雷不能在横竖上下向构成三连"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)

        for pos, _ in board():
            for positions in [
                [pos, pos.left(), pos.left().left()],
                [pos, pos.down(), pos.down().down()],
                [pos, self.up(board, pos), self.up(board, pos, 2)],
            ]:
                if None in positions:
                    continue
                var_list = board.batch(positions, mode="variable")
                if True in [None is i for i in var_list]:
                    continue
                model.Add(sum(var_list) != 0).OnlyEnforceIf(s1)
                model.Add(sum(var_list) != 3).OnlyEnforceIf(s2)

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            size = info["size"][key]
            ub += size[0] * size[1]
        info["soft_fn"](ub * 0.5, 0)
