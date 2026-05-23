#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[FB] 斐波那契列：对于第N列，其总雷数为第N-1列与第N-2列的总雷数之和或差的绝对值（索引在题板边界循环），
每列独立选择使用和或差。
作者：雾 (3140864122)
"""
from typing import TYPE_CHECKING

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

if TYPE_CHECKING:
    from ....impl.summon.solver import Switch


class RuleFB(AbstractMinesRule):
    id = "FB"
    name = "Fibonacci Columns"
    name.zh_CN = "斐波那契列"
    doc = "For column N, total mines = |col(N-1) + col(N-2)| or |col(N-1) - col(N-2)|, each column chooses independently, cyclic indices."
    doc.zh_CN = "对于第N列，其总雷数为第N-1列与第N-2列的和或差的绝对值，每列独立选择，索引在题板边界循环。"
    author = ("雾", 3140864122)
    tags = ["Creative", "Global", "Mine-Counting"]
    creation_time = "2026-05-24"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        if board.boundary().col % 3 != 2:
            raise ValueError("必须在3的倍数的情况下才存在解")

    def create_constraints(self, board: "AbstractBoard", switch: "Switch") -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.x + 1
            cols = bound.y + 1
            if cols < 2:
                continue

            col_sums: list[IntVar] = []
            for col in range(cols):
                col_sum = model.NewIntVar(0, rows, f"FB_col_sum_{key}_{col}")
                col_vars = [board.get_variable(board.get_pos(row, col, key), special="raw") for row in range(rows)]
                model.Add(col_sum == sum(col_vars)).OnlyEnforceIf(rule_switch)
                col_sums.append(col_sum)

            # 每列的选择变量：True=加法，False=减法
            choices = [model.NewBoolVar(f"FB_choice_{key}_{col}") for col in range(cols)]

            for i in range(cols):
                prev1 = (i - 1) % cols
                prev2 = (i - 2) % cols
                # 和
                sum_val = model.NewIntVar(0, 2 * rows, f"FB_sum_val_{key}_{i}")
                model.Add(sum_val == col_sums[prev1] + col_sums[prev2])
                # 差的绝对值
                diff_val = model.NewIntVar(0, rows, f"FB_diff_val_{key}_{i}")
                diff_raw = model.NewIntVar(-rows, rows, f"FB_diff_raw_{key}_{i}")
                model.Add(diff_raw == col_sums[prev1] - col_sums[prev2])
                model.AddAbsEquality(diff_val, diff_raw)

                # 根据 choice 选择
                chosen = model.NewIntVar(0, 2 * rows, f"FB_chosen_{key}_{i}")
                model.Add(chosen == sum_val).OnlyEnforceIf(choices[i])
                model.Add(chosen == diff_val).OnlyEnforceIf(choices[i].Not())
                model.Add(col_sums[i] == chosen).OnlyEnforceIf(rule_switch)
