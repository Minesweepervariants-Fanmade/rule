#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/21 20:17
# @Author  : 小中医 (3086842243)
# @FileName: QQ.py
"""
[QQ] 每个3*3框至少2雷
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleQQ(AbstractMinesRule):
    id = "QQ"
    aliases = ()
    name = "Every 3x3 box has at least 2 mines"
    name.zh_CN = "三三至少二雷"
    doc = "Every 3x3 box has at least 2 mines"
    doc.zh_CN = "每个3*3框至少2雷"
    author = ("小中医 (3086842243)", 3086842243)
    tags = ["Original", "Local", "Strict R", "Strong"]
    creation_time = "2026-07-21"

    def create_constraints(self, board: 'Board', switch):
        """
        为每个完整的3x3区域添加约束：该区域内的雷数 >= 2。
        只考虑完全位于题板内部的区域。
        """
        model = board.get_model()
        s = switch.get(model, self)
        # 获取 raw 键对应的棋盘边界位置
        boundary_pos = board.boundary("raw")
        rows = boundary_pos.row + 1
        cols = boundary_pos.col + 1
        # 遍历所有可能的3x3区域的左上角位置
        for i in range(rows - 2):
            for j in range(cols - 2):
                # 获取该3x3区域内的所有位置
                positions = []
                for di in range(3):
                    for dj in range(3):
                        pos = board.get_pos(i + di, j + dj, "raw")
                        if pos and board.in_bounds(pos):
                            positions.append(pos)
                # 计算该区域内所有雷变量的和
                sum_mines = sum(board.batch(positions, mode="variable", drop_none=True))
                # 约束：雷数 >= 2
                model.Add(sum_mines >= 2).OnlyEnforceIf([s])

    def suggest_total(self, info: dict):
        """
        根据棋盘大小给出雷总数的建议范围。
        对于m行n列，至少需要 (m-2)*(n-2)*2/9 个雷（近似），但这里采用更宽松的估计。
        """
        def a(model, total):
            # 总雷数至少为2（因为至少要有一个3x3区域）
            model.Add(total >= 2)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        # 建议的雷数范围：至少占棋盘面积的约 1/9 * 2 = 2/9，但最少为2
        min_mines = max(2, int(ub * 0.22))  # 略大于2/9
        info["soft_fn"](min_mines, 0)
        info["hard_fns"].append(a)
