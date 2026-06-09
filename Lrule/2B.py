#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/09 03:33
# @Author  : Wu_RH
# @FileName: 2B.py
"""
[2B] 桥 (Bridge)：所有雷构成若干组桥。桥是从题版左边界八连通连接（水平或斜角连接）到右边界，宽度为 1、长度与题版相等的一条路径
"""
from minesweepervariants.impl.summon.solver import Switch

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from ortools.sat.python.cp_model import IntVar, CpModel


def _get_index(line: list[IntVar], model: CpModel, col_name: str = "") -> list[IntVar]:
    n = len(line)

    a = line + [True]
    b = [model.new_int_var(0, n, f'col_idx_{col_name}_{i}') for i in range(n)]

    s = [model.new_int_var(0, n + 1, f's_{col_name}_{j}') for j in range(n + 2)]
    model.add(s[0] == 0)
    for j in range(n + 1):
        model.add(s[j+1] == s[j] + a[j])

    for i in range(n):
        # 约束 A：a[b[i]] == 1
        model.add_element(b[i], a, 1)

        # 约束 B：前 n+1 个元素来自 s，最后一个元素直接填入目标值 i + 1
        s_lookup = [s[j] for j in range(n + 1)] + [i + 1]

        b_plus_one = model.new_int_var(1, n + 1, f'b_plus_one_{col_name}_{i}')
        model.add(b_plus_one == b[i] + 1)
        model.add_element(b_plus_one, s_lookup, i + 1)

    for i in range(n - 1):
        model.add(b[i+1] >= b[i])

    model.add_element(s[n], b +[n], n)
    
    return b

class Rule2B(AbstractMinesRule):
    id = "2B"
    name = "Bridge"
    name.zh_CN = "桥"
    doc = "All mines form several bridges. A bridge is a path from the left boundary to the right boundary with eight-connected (horizontal or diagonal), width 1, and length equal to the board."
    doc.zh_CN = "所有雷构成若干组桥。桥是从题版左边界八连通连接（水平或斜角连接）到右边界，宽度为 1、长度与题版相等的一条路径"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            cols, rows = boundary.col + 1, boundary.row + 1

            col_idx: list[list[IntVar]] = []
            for col_pos in board.get_row_pos(boundary):
                column = board.get_col_pos(col_pos)
                line = [var for pos in column if (var := board.get_variable(pos)) is not None]
                idx_vars = _get_index(line, model, f"{key}_{col_pos}")
                col_idx.append(idx_vars)

            for r in range(rows):
                for c in range(cols - 1):
                    this_idx = col_idx[c][r]
                    next_idx = col_idx[c + 1][r]

                    diff = model.new_int_var(-1, 1, f'diff_{key}_{r}_{c}')
                    model.add(diff == next_idx - this_idx).OnlyEnforceIf(s)

    def create_constraints_(self, board: 'Board', switch):
        """
        约束建议提供:哈嘿袁
        """
        # if self.get_name() == "2B:":
        #     return self.create_constraints_(board, switch)
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            last_row = board.get_row_pos(boundary_pos)
            for index in range(len(last_row)):
                col_b = board.get_col_pos(last_row[index])
                col_var = []
                for index_t in range(len(col_b) - 1):
                    tmp_t = model.NewBoolVar(f"tmp_t_{col_b[index_t]}_{col_b[index_t + 1]}")
                    var_t_a = board.get_variable(col_b[index_t])
                    var_t_b = board.get_variable(col_b[index_t + 1])
                    model.AddBoolOr([var_t_a, var_t_b]).OnlyEnforceIf([tmp_t, s])
                    model.AddBoolAnd([var_t_a.Not(), var_t_b.Not()]).OnlyEnforceIf([tmp_t.Not(), s])
                    col_var.append(tmp_t)

                for index_a in range(len(col_b) - 1):
                    for index_b in range(index_a + 1, len(col_b)):
                        if -1 < index - 1 < len(last_row):
                            col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                            model.Add(
                                sum(col_c[index_a+1:index_b]) ==
                                sum(board.batch(col_b[index_a+2:index_b-1], mode="variable"))
                            ).OnlyEnforceIf(col_var[index_a+1:index_b-1] +
                                            [col_var[index_a].Not(), col_var[index_b-1].Not(), s])
                        if -1 < index + 1 < len(last_row):
                            col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                            model.Add(
                                sum(col_a[index_a+1:index_b]) ==
                                sum(board.batch(col_b[index_a+2:index_b-1], mode="variable"))
                            ).OnlyEnforceIf(col_var[index_a+1:index_b-1] +
                                            [col_var[index_a].Not(), col_var[index_b-1].Not(), s])

                for index_t in range(1, len(col_b) - 1):
                    if -1 < index - 1 < len(last_row):
                        col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                        model.Add(
                            sum(col_c[:index_t+1]) ==
                            sum(board.batch(col_b[:index_t], mode="variable"))
                        ).OnlyEnforceIf(col_var[:index_t]+[col_var[index_t].Not(), s])
                    if -1 < index + 1 < len(last_row):
                        col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                        model.Add(
                            sum(col_a[:index_t+1]) ==
                            sum(board.batch(col_b[:index_t], mode="variable"))
                        ).OnlyEnforceIf(col_var[:index_t]+[col_var[index_t].Not(), s])

                for index_t in range(1, len(col_b) - 1):
                    if -1 < index - 1 < len(last_row):
                        col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                        model.Add(
                            sum(col_c[index_t:]) ==
                            sum(board.batch(col_b[index_t+1:], mode="variable"))
                        ).OnlyEnforceIf(col_var[index_t:] + [col_var[index_t-1].Not(), s])
                    if -1 < index + 1 < len(last_row):
                        col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                        model.Add(
                            sum(col_a[index_t:]) ==
                            sum(board.batch(col_b[index_t+1:], mode="variable"))
                        ).OnlyEnforceIf(col_var[index_t:] + [col_var[index_t-1].Not(), s])

            # 两个并排的非雷其上下两侧的雷数必然相同
            for pos in board.get_col_pos(boundary_pos):
                row = board.get_row_pos(pos)
                for index in range(len(row) - 1):
                    pos_a, pos_b = row[index], row[index + 1]
                    var_a, var_b = board.batch([pos_a, pos_b], mode="variable")
                    line_a = board.get_col_pos(pos_a)
                    line_a = line_a[:line_a.index(pos_a)]
                    line_b = board.get_col_pos(pos_b)
                    line_b = line_b[:line_b.index(pos_b)]
                    vars_a = board.batch(line_a, mode="variable")
                    vars_b = board.batch(line_b, mode="variable")
                    model.Add(sum(vars_a) == sum(vars_b)).OnlyEnforceIf([var_a.Not(), var_b.Not(), s])

            # 列平衡
            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            # 所有 row_sums 相等
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i] == row_sums[0]).OnlyEnforceIf(s)


    def suggest_total(self, info: dict):
        size_list = [info["size"][key] for key in info["interactive"]]

        def a(model, total):
            nonlocal size_list
            var_list = []
            for i, (height, width) in enumerate(size_list):
                n = model.NewIntVar(0, height * width, f"width_{i}")
                model.AddModuloEquality(0, n, width)
                var_list.append(n)
            model.Add(sum(var_list) == total)

        info["hard_fns"].append(a)
