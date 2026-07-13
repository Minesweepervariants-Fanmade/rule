#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/13 22:37
# @Author  : Wu_RH
# @FileName: 3O^.py
"""
[3O^]八方向: 雷从八个方向中的任意一个连到题板外
在3O的基础上扩展为八方向（上、下、左、右、左上、右上、左下、右下）
"""
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule3O_Caret(AbstractMinesRule):
    id = "3O^"
    name = "Octagonal"
    name.zh_CN = "八方向"
    doc = "Mines connect from any of the eight directions to outside the board"
    doc.zh_CN = "雷从八个方向中的任意一个连到题板外"

    tags = ["Creative", "Global", "Construction", "Strict Shape"]
    creation_time = "2026-07-13"
    author = ("Wu_RH", 3140864122)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()

        # 八个方向: (行偏移, 列偏移)
        directions = [
            (-1, 0),   # 上
            (1, 0),    # 下
            (0, -1),   # 左
            (0, 1),    # 右
            (-1, -1),  # 左上
            (-1, 1),   # 右上
            (1, -1),   # 左下
            (1, 1)     # 右下
        ]

        for pos, var in board(mode="variable"):
            # 获取当前题板的边界
            boundary = board.boundary(pos.board_key)
            max_row = boundary.row
            max_col = boundary.col

            # 对于每个方向，获取从当前位置沿该方向到边界的连续位置序列
            direction_vars = []
            for dr, dc in directions:
                # 沿方向收集位置
                positions = []
                cur_row = pos.row + dr
                cur_col = pos.col + dc
                # 在边界内持续移动
                while 0 <= cur_row <= max_row and 0 <= cur_col <= max_col:
                    new_pos = pos.__class__(cur_col, cur_row, pos.board_key)
                    positions.append(new_pos)
                    cur_row += dr
                    cur_col += dc

                # 为每个方向创建一个布尔变量
                direction_var = model.NewBoolVar(f"dir_{pos}_{dr}_{dc}")
                # 如果该方向存在至少一个位置，则约束：方向变量为真 => 该方向上的所有位置都为雷
                # 如果positions为空，则sum(pos_vars) == 0，约束始终成立，但方向变量可以任意，但我们希望方向变量为真时无额外要求，但逻辑上方向为空表示该方向没有格子，可以认为已经到达边界，所以方向变量为真可以允许。但为了简单，我们仍然添加约束，但sum=0恒成立，所以方向变量可以自由。
                pos_vars = [board.get_variable(p) for p in positions]
                # 注意：如果positions为空，则sum(pos_vars) == 0，约束恒成立，方向变量不受限制。但根据规则，如果方向路径为空，意味着当前位置已经在边界上，那么该方向是有效的？实际上，如果路径为空，说明该方向没有格子，这通常发生在边界上，此时可以认为雷已经连接到边界，所以允许方向变量为真。我们允许方向变量为真，所以不额外约束。
                model.Add(sum(pos_vars) == len(pos_vars)).OnlyEnforceIf([direction_var])
                direction_vars.append(direction_var)

            # 如果当前位置是雷，则至少有一个方向变量为真
            if direction_vars:
                model.AddBoolOr(direction_vars).OnlyEnforceIf([var])
            else:
                # 如果没有方向（理论上不可能，但以防万一），添加一个恒假约束
                model.Add(var == 0)
