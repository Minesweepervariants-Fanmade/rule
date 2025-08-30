#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 11:44
# @Author  : xxx
# @FileName: Q1.py

"""
[3D1Q]无方: 每个2x2x2区域内都至少有2个雷
"""

from typing import List

from .. import Abstract3DMinesRule
from .....abs.board import AbstractPosition, AbstractBoard


def block(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    e_pos = a_pos.clone()
    e_pos = Rule1Q.up(board, e_pos)
    if e_pos is None:
        return []
    f_pos = e_pos.up()
    g_pos = e_pos.left()
    h_pos = f_pos.left()
    if not board.in_bounds(h_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos, e_pos, f_pos, g_pos, h_pos]


class Rule1Q(Abstract3DMinesRule):
    name = ["3D1Q", "3DQ", "三维无方"]
    doc = "每个2x2x2区域内都至少有2个雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, _ in board():
            if not (pos_block := block(pos, board)):
                continue
            var_list = [board.get_variable(pos) for pos in pos_block]
            model.Add(sum(var_list) > 1).OnlyEnforceIf(s)
