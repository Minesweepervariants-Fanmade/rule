#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/09 01:30
# @Author  : Wu_RH
# @FileName: B1.py
"""
[1B]平衡: 每行每列雷数相同
"""
from math import gcd

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1B(AbstractMinesRule):
    name = ["1B", "平衡"]
    doc = "1.每一列的雷数相同 且2.每一行的雷数相同"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)
        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            # 所有 row_sums 相等
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i] == row_sums[0]).OnlyEnforceIf(s1)

            col_positions = board.get_col_pos(boundary_pos)
            col_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_row_pos(pos))
                for pos in col_positions
            ]
            # 所有 col_sums 相等
            for i in range(1, len(col_sums)):
                model.Add(col_sums[i] == col_sums[0]).OnlyEnforceIf(s2)

    def suggest_total(self, info: dict):
        def lcm(a, b):
            return a * b // gcd(a, b) if a and b else 0

        def add_constraints(model, total_var):
            """实际添加约束的函数（保持最小化）"""
            nonlocal bases

            # 创建分量变量
            components = []
            for i, base in enumerate(bases):
                max_multiplier = (total_var.Proto().domain[1] // base) + 1
                mult = model.NewIntVar(0, max_multiplier, f"mult_{i}")
                product = model.NewIntVar(0, total_var.Proto().domain[1], f"prod_{i}")

                # 添加乘积约束
                model.AddMultiplicationEquality(product, [mult, base])
                components.append(product)

            # 添加总和约束
            model.Add(sum(components) == total_var)

        sizes = [info["size"][interactive] for interactive in info["interactive"]]

        # 预处理阶段：计算各size的base_i
        bases = [lcm(w, h) for w, h in sizes if w > 0 and h > 0]

        info["hard_fns"].append(add_constraints)
