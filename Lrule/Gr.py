#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[Gr] Agreement: For each row, there is exactly one column that has the same mine count.
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard


class RuleGr(AbstractMinesRule):
    id = "Gr"
    name = "Agreement"
    name.zh_CN = "一致"
    doc = "For each row, there is exactly one column that has the same mine count."
    doc.zh_CN = "对于每一行，恰好有一列的雷数与该行的雷数相同。"
    author = ("DeepSeek", 0)
    tags = ["Creative", "Global", "Mine-Counting", "Strict R"]
    creation_time = "2026-05-13"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.x + 1
            cols = bound.y + 1
            # row sums
            row_sums = []
            for x in range(rows):
                row_vars = [board.get_variable(board.get_pos(x, y, key)) for y in range(cols)]
                row_sum = model.NewIntVar(0, cols, f"gr_row_sum_{key}_{x}")
                model.Add(row_sum == sum(row_vars)).OnlyEnforceIf(s)
                row_sums.append(row_sum)
            # column sums
            col_sums = []
            for y in range(cols):
                col_vars = [board.get_variable(board.get_pos(x, y, key)) for x in range(rows)]
                col_sum = model.NewIntVar(0, rows, f"gr_col_sum_{key}_{y}")
                model.Add(col_sum == sum(col_vars)).OnlyEnforceIf(s)
                col_sums.append(col_sum)

            # for each row, exactly one column with equal sum
            for i, row_sum in enumerate(row_sums):
                eq_vars = []
                for j, col_sum in enumerate(col_sums):
                    eq = model.NewBoolVar(f"gr_eq_{key}_{i}_{j}")
                    model.Add(row_sum == col_sum).OnlyEnforceIf([eq, s])
                    model.Add(row_sum != col_sum).OnlyEnforceIf([eq.Not(), s])
                    eq_vars.append(eq)
                model.AddExactlyOne(eq_vars).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        # soft constraint: suggest total mines around 40% of total cells
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        info["soft_fn"](int(ub * 0.4), 0)
