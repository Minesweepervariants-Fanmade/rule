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
from ....impl.board.version3 import Board
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
        for key in board.get_interactive_keys():
            if len(board.get_config(key, "mask")) > 0:
                raise ValueError("1O 不支持异形题板")

        model = board.get_model()
        s = switch.get(model, self)

        # 非雷四连通
        connect(
            model,
            board,
            connect_value=0,
            nei_value=1,
            switch=s,
        )

        # 雷区连通到边界，相当于在题板外圈添加一圈雷后四连通
        border_board = Board(size=(board.boundary().x + 2, board.boundary().y + 2), rules=None)
        border_positions_vars = []
        for pos, var in board("always", mode="variable"):
            border_positions_vars.append((border_board.get_pos(pos.x + 1, pos.y + 1), var))
        for x in range(border_board.boundary().x):
            for y in range(border_board.boundary().y):
                pos = border_board.get_pos(x, y)
                if x == 0 or x == border_board.boundary().x or y == 0 or y == border_board.boundary().y:
                    border_positions_vars.append((pos, model.NewConstant(1)))  # 边界全为雷
        connect(
            model,
            border_board,
            connect_value=1,
            nei_value=1,
            switch=s,
            positions_vars=border_positions_vars,
        )

        # 1O大定式
        for pos, _ in board():
            pos_list = block(pos, board)
            if not pos_list:
                continue
            a, b, c, d = board.batch(pos_list, mode="variable")
            model.AddBoolOr([a.Not(), b, c, d.Not()]).OnlyEnforceIf(s)  # 排除 1010
            model.AddBoolOr([a, b.Not(), c.Not(), d]).OnlyEnforceIf(s)  # 排除 0101
