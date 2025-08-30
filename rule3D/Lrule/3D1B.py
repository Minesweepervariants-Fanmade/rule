#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/21 08:12
# @Author  : Wu_RH
# @FileName: 3D1B.py
"""
[3D1B']平衡: 所有平行面的总雷数均相等
"""
from math import gcd
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch
from .. import Abstract3DMinesRule


class Rule(Abstract3DMinesRule):
    name = ["3D1B'", "平衡"]
    doc = "所有平行面的总雷数均相等"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s1 = switch.get(model, self, "↔")
        s2 = switch.get(model, self, "↕")
        s3 = switch.get(model, self, "X")

        # 层间面平衡
        _var_list = None
        for key in board.get_interactive_keys():
            var_list = [var for pos, var in board(mode="var", key=key)]
            if _var_list is None:
                _var_list = var_list
                continue
            model.Add(sum(var_list) == sum(_var_list)).OnlyEnforceIf(s3)
            _var_list = var_list

        # col轴面平衡
        _var_list = None
        for pos in board.get_row_pos(board.boundary()):
            var_list = []
            for key in board.get_interactive_keys():
                _pos = pos.clone()
                _pos.board_key = key
                var_list.extend(board.batch(
                    board.get_col_pos(_pos),
                    mode="var"
                ))
            if _var_list is None:
                _var_list = var_list
                continue
            model.Add(sum(var_list) == sum(_var_list)).OnlyEnforceIf(s2)
            _var_list = var_list

        # row轴面平衡
        _var_list = None
        for pos in board.get_col_pos(board.boundary()):
            var_list = []
            for key in board.get_interactive_keys():
                _pos = pos.clone()
                _pos.board_key = key
                var_list.extend(board.batch(
                    board.get_row_pos(_pos),
                    mode="var"
                ))
            if _var_list is None:
                _var_list = var_list
                continue
            model.Add(sum(var_list) == sum(_var_list)).OnlyEnforceIf(s1)
            _var_list = var_list

    def suggest_total(self, info: dict):
        def lcm(a, b):
            # 计算两个数的最小公倍数
            if a == 0 or b == 0:
                return 0
            return a * b // gcd(a, b)

        def lcm3(a, b, c):
            # 计算三个数的最小公倍数
            return lcm(a, lcm(b, c))

        def add_constraints(model, total_var):
            nonlocal base
            # 计算乘数的上限：总雷数的最大值除以base
            max_multiplier = total_var.Proto().domain[1] // base + 1
            mult = model.NewIntVar(0, max_multiplier, f"mult")
            model.AddMultiplicationEquality(total_var, [mult, base])

        # 获取每个交互区域的尺寸，假设每个尺寸是三元组 (w, h, d)
        sizes = [info["size"][interactive] for interactive in info["interactive"]]
        d = len(info["interactive"])
        w, h = sizes[0][0], sizes[0][1]
        for size in sizes[1:]:
            if w != size[0] or h != size[1]:
                raise ValueError("保证题板尺寸相同")
        if w > 0 and h > 0 and d > 0:  # 确保所有尺寸为正
            base = lcm3(w, h, d)

        # 如果没有有效的base，则跳过添加约束
        info["hard_fns"].append(add_constraints)