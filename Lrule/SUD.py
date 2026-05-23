#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/22 21:45
# @Author  : Wu_RH
# @FileName: SUD.py

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class RuleSUD(AbstractMinesRule):
    id = "SUD"
    name = "Sudoku"
    name.zh_CN = "数独"
    doc = "Sudoku: Each row and column of clue cells must contain unique numbers.(V only)"
    doc.zh_CN = "每行每列线索格数字不重复(仅限V)"
    tags = ["Original", 'Meta']
    author = ("小绿草", 3021857082)
    creation_time = "2026-05-21 00:32:21"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key=key)

            real_pos_sum = {
                pos: sum([
                    board.get_variable(_pos)
                    for _pos in pos.neighbors(2)
                    if board.is_valid(_pos)
                ]) for pos, _ in board(key=key)
            }
            ub = max(8, max(board.get_config(key, "size")))
            pos_sum = {
                pos: model.new_int_var(0, ub, str(pos))
                for pos, _ in board(key=key)
            }

            for pos, var in board(mode="var", key=key):
                model.add(real_pos_sum[pos] == pos_sum[pos]).OnlyEnforceIf(s, var.Not())

            row_bound_positions = board.get_row_pos(pos_bound)
            col_bound_positions = board.get_col_pos(pos_bound)

            col_positions = [
                [_pos for _pos in board.get_col_pos(pos)]
                for pos in row_bound_positions
            ]

            row_positions = [
                [_pos for _pos in board.get_row_pos(pos)]
                for pos in col_bound_positions
            ]

            for line in col_positions + row_positions:
                model.add_all_different(pos_sum[pos] for pos in line).OnlyEnforceIf(s)
