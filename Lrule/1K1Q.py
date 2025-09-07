#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 11:44
# @Author  : xxx
# @FileName: Q1.py

"""
[1K1Q]马步无方: 每一个边长为sqrt5的格点正方形定点上至少1雷
"""

from typing import List

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractPosition, AbstractBoard


def block1(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.left().left().up()
    c_pos = b_pos.up().up().right()
    d_pos = c_pos.right().right().down()

    if not board.in_bounds(b_pos) or not board.in_bounds(c_pos) or not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


def block2(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.left().up().up()
    c_pos = b_pos.right().right().up()
    d_pos = c_pos.down().down().right()

    if not board.in_bounds(b_pos) or not board.in_bounds(c_pos) or not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


class Rule1K1Q(AbstractMinesRule):
    name = ["1K1Q", "1K1Q", "马步无方"]
    doc = "每一个边长为sqrt5的格点正方形定点上至少1雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            a_pos = board.boundary(key=key)
            for b_pos in board.get_col_pos(a_pos):
                for i_pos in board.get_row_pos(b_pos):
                    if not (pos_block := block1(i_pos, board)):
                        continue
                    var_list = [board.get_variable(pos) for pos in pos_block]
                    model.AddBoolOr(var_list).OnlyEnforceIf(s)
        for key in board.get_interactive_keys():
            a_pos = board.boundary(key=key)
            for b_pos in board.get_col_pos(a_pos):
                for i_pos in board.get_row_pos(b_pos):
                    if not (pos_block := block2(i_pos, board)):
                        continue
                    var_list = [board.get_variable(pos) for pos in pos_block]
                    model.AddBoolOr(var_list).OnlyEnforceIf(s)
