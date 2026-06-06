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
from minesweepervariants.board import Board, Size
from minesweepervariants.utils.impl_obj import VALUE_CROSS

if TYPE_CHECKING:
    from ....impl.summon.solver import Switch

FB_BOARD_NAME = "FB"


class RuleFB(AbstractMinesRule):
    id = "FB"
    name = "Fibonacci Columns"
    name.zh_CN = "斐波那契列"
    doc = "For column N, total mines = |col(N-1) + col(N-2)| or |col(N-1) - col(N-2)|, cyclic indices."
    doc.zh_CN = "对于第N列，其总雷数为第N-1列与第N-2列的和或差的绝对值，索引在题板边界循环。"
    author = ("雾", 3140864122)
    tags = ["Creative", "Global", "Mine-Counting"]
    creation_time = "2026-05-24"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        pos_bound = board.boundary()
        if pos_bound.col % 3 != 2:
            raise ValueError("列数必须在3的倍数的情况下才存在解")
        board.generate_board(
            FB_BOARD_NAME, labels=[f"{i}" for i in range(pos_bound.col + 2)] + ["+"],
            size=Size(pos_bound.row + 1, pos_bound.col + 3)
        )
        board.set_config(FB_BOARD_NAME, "pos_label", True)

    def init_board(self, board: 'Board') -> None:
        for pos, _ in board("N", key=FB_BOARD_NAME):
            board[pos] = VALUE_CROSS

    def init_clear(self, board: 'Board') -> None:
        for pos, _ in board(key=FB_BOARD_NAME):
            board[pos] = None

    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        model = board.get_model()
        rule_switchs = []
        for i in range(board.boundary().row + 1):
            rule_switchs.append(switch.get(model, self, chr(i + 65)))
        # rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.row + 1
            cols = bound.col + 1
            if cols < 2:
                continue

            col_sums: list[IntVar] = []
            for col in range(cols):
                col_sum = model.new_int_var(0, rows, f"FB_col_sum_{key}_{chr(col + 65)}")
                col_vars = [board.get_variable(board.get_pos(row, col, key), special="raw") for row in range(rows)]
                model.add(col_sum == sum(col_vars)).OnlyEnforceIf(rule_switchs[col])
                col_sums.append(col_sum)

            # 每列的选择变量：True=加法，False=减法
            # choices = [model.new_bool_var(f"FB_choice_{key}_{col}") for col in range(cols)]
            choices = [board.get_variable(pos) for pos in board.get_row_pos(board.boundary(FB_BOARD_NAME))]

            for i in range(cols):
                prev1 = (i - 1) % cols
                prev2 = (i - 2) % cols
                # 和
                sum_val = model.new_int_var(0, 2 * rows, f"FB_sum_val_{key}_{i}")
                model.add(sum_val == col_sums[prev1] + col_sums[prev2])
                # 差的绝对值
                diff_val = model.new_int_var(0, rows, f"FB_diff_val_{key}_{i}")
                diff_raw = model.new_int_var(-rows, rows, f"FB_diff_raw_{key}_{i}")
                model.add(diff_raw == col_sums[prev1] - col_sums[prev2])
                model.add_abs_equality(diff_val, diff_raw)

                switchs = [rule_switchs[i], rule_switchs[prev1], rule_switchs[prev2]]
                # 根据 choice 选择
                chosen = model.new_int_var(0, 2 * rows, f"FB_chosen_{key}_{i}")
                model.add(chosen == sum_val).OnlyEnforceIf([choices[i]] + switchs)
                model.add(chosen == diff_val).OnlyEnforceIf([choices[i].Not()] + switchs)
                model.add(col_sums[i] == chosen).OnlyEnforceIf(switchs)

                for j in range(cols + 1):
                    model.add(col_sums[i] == j).OnlyEnforceIf(
                        board.get_variable(board.get_pos(j, i, FB_BOARD_NAME)),
                        rule_switchs[i]
                    )
                    model.add(col_sums[i] != j).OnlyEnforceIf(
                        board.get_variable(board.get_pos(j, i, FB_BOARD_NAME)).Not(),
                        rule_switchs[i]
                    )

                model.add(
                    sum([
                        board.get_variable(
                            board.get_pos(j, i, FB_BOARD_NAME)
                        ) for j in range(cols + 1)
                    ]) == 1
                ).OnlyEnforceIf(rule_switchs[i])
