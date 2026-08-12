#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/13 03:26
# @Author  : 饿魔茶茶 (3507742359)
# @FileName: 1X'&.py
"""
[1X'&]: 雷的上下邻居雷数之和不等于左右邻居雷数之和
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule1X_And(AbstractMinesRule):
    id = "1X'&"
    name = "Cross Imbalance"
    name.zh_CN = "十字失衡"
    doc = "For any mine, the sum of mines in its up/down neighbors must not equal the sum in its left/right neighbors."
    doc.zh_CN = "雷的上下邻居雷数之和不等于左右邻居雷数之和"
    author = ("饿魔茶茶", 3507742359)
    tags = ["Variant", "Local"]
    creation_time = "2026-08-13"

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, var in board(mode="variable"):
            # 获取上下左右四个邻居的变量（仅当它们在边界内）
            up_var = board.get_variable(pos.up()) if board.in_bounds(pos.up()) else None
            down_var = board.get_variable(pos.down()) if board.in_bounds(pos.down()) else None
            left_var = board.get_variable(pos.left()) if board.in_bounds(pos.left()) else None
            right_var = board.get_variable(pos.right()) if board.in_bounds(pos.right()) else None

            # 计算上下邻居的雷数之和
            up_down_sum = 0
            if up_var is not None:
                up_down_sum += up_var
            if down_var is not None:
                up_down_sum += down_var

            # 计算左右邻居的雷数之和
            left_right_sum = 0
            if left_var is not None:
                left_right_sum += left_var
            if right_var is not None:
                left_right_sum += right_var

            # 如果当前格是雷，则上下邻居雷数之和不等于左右邻居雷数之和
            model.Add(up_down_sum != left_right_sum).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict):
        # 提供软约束建议，使总雷数略低于棋盘的一半，以增加规则的可满足性
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        # 建议总雷数为总格子数的 40%，与许多左线规则一致
        info["soft_fn"](int(ub * 0.4), 0)
