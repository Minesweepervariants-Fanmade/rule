#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/15 09:01
# @Author  : Wu_RH
# @FileName: 3Q.py
"""
[3Q]正方形(Square): 所有四连通的雷格区域组成实心正方形
"""
from typing import List

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


def block(a_pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


class Rule3Q(AbstractMinesRule):
    name = ["3Q", "正方形", "Square"]
    doc = "所有四连通的雷格区域组成实心正方形"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, var in board(mode="var"):
            block_pos = block(pos, board)
            if block_pos:
                block_var = board.batch(block_pos, mode="var")
                model.Add(sum(block_var) != 3)

            row = board.get_row_pos(pos)
            col = board.get_col_pos(pos)

            var_list = [var]
            if board.in_bounds(pos.up()):
                var_list.append(board.get_variable(pos.up()).Not())
            if board.in_bounds(pos.left()):
                var_list.append(board.get_variable(pos.left()).Not())

            tmp_list = []

            for row_pos, col_pos in zip(
                row[row.index(pos):],
                col[col.index(pos):]
            ):
                tmp = model.NewBoolVar(f"tmp[{pos}, {row_pos}, {col_pos}]")
                model.AddBoolAnd(var_list).OnlyEnforceIf(tmp)
                row_box = board.get_pos_box(pos, row_pos)
                col_box = board.get_pos_box(pos, col_pos)
                row_var = board.batch(row_box, "var")
                col_var = board.batch(col_box, "var")
                model.AddBoolAnd(row_var).OnlyEnforceIf(tmp)
                model.AddBoolAnd(col_var).OnlyEnforceIf(tmp)
                if board.is_valid(row_pos.right()):
                    model.AddBoolAnd(board.get_variable(row_pos.right()).Not()).OnlyEnforceIf(tmp)
                if board.is_valid(col_pos.down()):
                    model.AddBoolAnd(board.get_variable(col_pos.down()).Not()).OnlyEnforceIf(tmp)
                tmp_list.append(tmp)
            model.AddBoolOr(tmp_list).OnlyEnforceIf(var_list + [s])
