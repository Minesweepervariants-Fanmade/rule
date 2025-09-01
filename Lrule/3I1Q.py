#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 11:44
# @Author  : xxx
# @FileName: Q1.py

"""
[3I1Q]反相无方: 每个2x2区域内都至少有一个雷,染色格中非雷视为雷,雷视为非雷
"""

from typing import List

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractPosition, AbstractBoard


def block(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


class Rule3I1Q(AbstractMinesRule):
    name = ["3I1Q", "3I1Q", "反相无方"]
    doc = "每个2x2区域内都至少有一个雷,染色格中非雷视为雷,雷视为非雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            a_pos = board.boundary(key=key)
            for b_pos in board.get_col_pos(a_pos):
                for i_pos in board.get_row_pos(b_pos):
                    if not (pos_block := block(i_pos, board)):
                        continue
                    # 修改这一部分
                    var_list = []
                    for pos in pos_block:
                        if board.get_dyed(pos):
                            # 对于染色格，创建反转变量
                            inverted_var = model.NewBoolVar(f"invert_{pos}")
                            model.Add(inverted_var == 1 - board.get_variable(pos)).OnlyEnforceIf(s)
                            var_list.append(inverted_var)
                        else:
                            # 对于非染色格，直接使用原变量
                            var_list.append(board.get_variable(pos))
                    # 结束修改
                    model.AddBoolOr(var_list).OnlyEnforceIf(s)
