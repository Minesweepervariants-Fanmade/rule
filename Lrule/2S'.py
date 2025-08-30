#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/21 07:33
# @Author  : Wu_RH
# @FileName: 2S'.py
"""
[2S']分段': 每行连续雷长度不同
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class Rule(AbstractMinesRule):
    name = ["2S'", "分段'"]
    doc = "每行连续雷长度不同"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            for col_pos in board.get_col_pos(pos_bound):
                row = board.get_row_pos(col_pos)
                int_var_row = [model.NewIntVar(0, len(row), f"{pos}") for pos in row]
                var_row = board.batch(row, mode="var")

                model.Add(int_var_row[0] == var_row[0])

                for index in range(1, len(int_var_row)):
                    model.Add(
                        int_var_row[index] == int_var_row[index - 1] + 1
                    ).OnlyEnforceIf(var_row[index])
                    model.Add(int_var_row[index] == 0).OnlyEnforceIf(
                        var_row[index].Not()
                    )

                for index_a in range(len(int_var_row)):
                    for index_b in range(index_a + 1, len(int_var_row)):
                        model.Add(
                            int_var_row[index_a] !=
                            int_var_row[index_b]
                        ).OnlyEnforceIf([
                            var_row[index_a],
                            var_row[index_a + 1].Not(),
                            var_row[index_b], s
                        ] + ([] if len(row) == index_b + 1 else [
                            var_row[index_b + 1].Not()
                        ]))
