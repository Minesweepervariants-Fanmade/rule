#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/24 18:24
# @Author  : Wu_RH
# @FileName: 1B'.py

"""
[1B']失衡: 每行每列雷数均不相同
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1B(AbstractMinesRule):
    name = ["1B'", "失衡"]
    doc = "每行每列雷数均不相同 1.每列雷数不相同 2.每行雷数不相同"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            col_boundary = board.get_col_pos(boundary_pos)
            col_sums = [
                sum(board.batch(board.get_row_pos(pos), mode="variable"))
                for pos in col_boundary
            ]
            for i in range(len(col_sums)):
                for j in range(i + 1, len(col_sums)):
                    model.Add(col_sums[i] != col_sums[j]).OnlyEnforceIf(s1)

            row_boundary = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.batch(board.get_col_pos(pos), mode="variable"))
                for pos in row_boundary
            ]
            for i in range(len(row_sums)):
                for j in range(i + 1, len(row_sums)):
                    model.Add(row_sums[i] != row_sums[j]).OnlyEnforceIf(s2)

    def suggest_total(self, info: dict):
        sizes = [info["size"][interactive] for interactive in info["interactive"]]

        total = 0

        for size in sizes:
            if size[0] != size[1]:
                raise ValueError("题板不可为非正方矩形")
            else:
                total += int((size[0] - 1) * size[1] / 2)

        def a(model, total_var):
            model.Add(total == total_var)

        info["hard_fns"].append(a)
