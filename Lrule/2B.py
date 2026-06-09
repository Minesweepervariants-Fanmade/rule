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


from ortools.sat.python import cp_model

def _get_index(a: list[cp_model.IntVar], model: cp_model.CpModel, name: str = "") -> list[cp_model.IntVar]:
    n = len(a)

    # 1. 创建前缀和数组 s
    # s[j] 表示 a 到 a[j-1] 中 1 的总数。它的取值范围是 0 到 n
    s = [model.new_int_var(0, n, f's_{name}_{j}') for j in range(n + 1)]
    model.add(s[0] == 0)
    for j in range(n):
        model.add(s[j+1] == s[j] + a[j])

    # 2. 创建目标输出数组 b
    # b[i] 代表第 i+1 个 1 出现的索引位置
    # 【核心技巧】：如果 a 中 1 的个数不够（小于 i+1 个），我们用一个虚拟位置 n 来表示不存在
    b = [model.new_int_var(0, n, f'b_{name}_{i}') for i in range(n)]

    # 3. 建立对偶映射（Channeling）
    # 逻辑：如果 a[j] 是一个 1，那么此时它前面的 1 的个数恰好是 s[j]。
    # 也就是说，a[j] 就是整个数组中的第 s[j] 个 1（以 0 为起始计数）。
    # 因此，目标数组中第 s[j] 个位置，必须记录当前的索引 j，即：b[s[j]] == j
    for j in range(n):
        # 只有当 a[j] == 1 时，才强制执行这个元素查找约束
        model.add_element(s[j], b, j).only_enforce_if(a[j])

    # 4. 处理 1 的数量不够时的边界情况
    # 确保 b 数组是递增的。如果某个 b[i] 变成了虚拟位置 n，后面所有的 b[i+1] 也必须是 n
    for i in range(n - 1):
        model.add(b[i+1] >= b[i])

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
