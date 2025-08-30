#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/08 06:30
# @Author  : Wu_RH
# @FileName: 1O.py
"""
[1O] 外部 (Outside)：非雷区域四连通；每个雷区域以四连通连接到题版边界
"""
from typing import List

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition
from .connect import connect


def block(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


class Rule1O(AbstractMinesRule):
    name = ["1O", "O", "外部", "Outside"]
    doc = "非雷区域四连通；每个雷区域以四连通连接到题版边界"

    def create_constraints(self, board: 'AbstractBoard', switch):
        positions_vars = [(pos, var) for pos, var in board("always", mode="variable")]
        model = board.get_model()
        s = switch.get(model, self)
        connect(
            model,
            board,
            ub=len(positions_vars),
            connect_value=0,
            nei_value=1,
            switch=s,
        )
        root_list = [model.NewBoolVar(f'root_{i}') for i in range(len(positions_vars))]
        for index, (pos, var) in enumerate(positions_vars):
            model.Add(var == 1).OnlyEnforceIf(root_list[index])
            flag = True
            for _pos in pos.neighbors(1):
                if not board.in_bounds(_pos):
                    flag = False
                    break
            if flag:
                model.Add(root_list[index] == 0)
                continue
            model.Add(root_list[index] == 1).OnlyEnforceIf(var)
            model.Add(root_list[index] == 0).OnlyEnforceIf(var.Not())
        connect(
            model,
            board,
            connect_value=1,
            nei_value=1,
            root_vars=root_list,
            ub=len(positions_vars),
            switch=s,
        )
        # 1O大定式
        for pos, _ in board():
            pos_list = block(pos, board)
            if not pos_list:
                continue
            a, b, c, d = board.batch(pos_list, mode="variable")
            model.AddBoolOr([a.Not(), b, c, d.Not()]).OnlyEnforceIf(s)  # 排除 1010
            model.AddBoolOr([a, b.Not(), c.Not(), d]).OnlyEnforceIf(s)  # 排除 0101
