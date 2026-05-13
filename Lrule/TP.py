#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[TP] 三分：每行恰好有三段连续雷或者无雷
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleTP(AbstractMinesRule):
    id = "TP"
    name = "TripleSegment"
    name.zh_CN = "三分"
    doc = "Each row has exactly three segments of consecutive mines, or no mines at all"
    doc.zh_CN = "每行恰好有三段连续雷或者无雷"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-05-13"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            # iterate over each row
            for col_pos in board.get_col_pos(boundary):
                row = board.get_row_pos(col_pos)
                row_vars = board.batch(row, mode="variable")

                # total mines in row
                total_mines = sum(row_vars)

                # count number of transitions from 0 to 1 (start of a segment)
                start_vars = []
                prev = None
                for i, var in enumerate(row_vars):
                    if i == 0:
                        # start of row: if first cell is mine, that's a start
                        start = model.NewBoolVar(f"tp_start_{key}_{col_pos.x}_{i}")
                        model.Add(start == var).OnlyEnforceIf(s)
                        start_vars.append(start)
                    else:
                        # transition from prev to current: start when prev is 0 and current is 1
                        start = model.NewBoolVar(f"tp_start_{key}_{col_pos.x}_{i}")
                        model.AddBoolAnd([prev.Not(), var]).OnlyEnforceIf([start, s])
                        model.AddBoolOr([prev, var.Not()]).OnlyEnforceIf([start.Not(), s])
                        start_vars.append(start)
                    prev = var

                total_starts = sum(start_vars)

                # Two cases: either all zeros (total_mines == 0) OR exactly 3 segments
                is_zero = model.NewBoolVar(f"tp_iszero_{key}_{col_pos.x}")
                model.Add(total_mines == 0).OnlyEnforceIf([is_zero, s])
                model.Add(total_mines > 0).OnlyEnforceIf([is_zero.Not(), s])

                is_three = model.NewBoolVar(f"tp_isthree_{key}_{col_pos.x}")
                model.Add(total_starts == 3).OnlyEnforceIf([is_three, s])
                model.Add(total_starts != 3).OnlyEnforceIf([is_three.Not(), s])

                # Either zero or three
                model.AddBoolOr([is_zero, is_three]).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells

        # 添加硬约束：总雷数必须为3的倍数
        def hard_constraint(model, total):
            model.AddModuloEquality(0, total, 3)

        info["hard_fns"].append(hard_constraint)
