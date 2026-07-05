#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/05
# @Author  : 咸鱼 (3898637422)
# @FileName: OQ.py
"""
[OQ] 奇数方阵 (Odd Quad): 每一个边长为奇数（不为1）的正方形范围中都有奇数个雷
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from ortools.sat.python import cp_model


class RuleOQ(AbstractMinesRule):
    id = "OQ"
    aliases = ("OQ",)
    name = "Odd Quad"
    name.zh_CN = "奇数方阵"
    doc = "Every odd-length (>=3) square contains an odd number of mines"
    doc.zh_CN = "每一个边长为奇数（不为1）的正方形范围中都有奇数个雷"
    tags = ["Original", "Local", "Construction"]
    creation_time = "2026-03-01"
    author = ("咸鱼", 3898637422)

    def suggest_total(self, info: dict):
        """建议总雷数范围：不超过总格子数的一半以上"""
        # 计算总格子数
        total_cells = 0
        for key in info.get("interactive", []):
            total_cells += info.get("total", {}).get(key, 0)
        if total_cells == 0:
            total_cells = 100
        # 设置较宽的范围，允许求解器自由选择
        info["hard_min"] = 1
        info["hard_max"] = total_cells
        info["soft_min"] = 1
        info["soft_max"] = total_cells // 2 + 1

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            # 获取该题板的所有位置
            positions = []
            for pos, _ in board(key=key):
                positions.append(pos)
            if not positions:
                continue

            # 计算题板边界
            min_row = min(p.row for p in positions)
            max_row = max(p.row for p in positions)
            min_col = min(p.col for p in positions)
            max_col = max(p.col for p in positions)
            rows = max_row - min_row + 1
            cols = max_col - min_col + 1

            # 最大可能的奇数边长（>=3）
            max_k = min(rows, cols)
            if max_k < 3:
                continue

            # 遍历所有奇数边长
            for k in range(3, max_k + 1, 2):
                # 遍历所有可能的左上角（基于实际坐标范围）
                for i in range(min_row, max_row - k + 2):
                    for j in range(min_col, max_col - k + 2):
                        var_list = []
                        ok = True
                        for di in range(k):
                            for dj in range(k):
                                pos = Position(i + di, j + dj, key)
                                if not board.in_bounds(pos):
                                    ok = False
                                    break
                                var = board.get_variable(pos)
                                if var is None:
                                    ok = False
                                    break
                                var_list.append(var)
                            if not ok:
                                break
                        if not ok or not var_list:
                            continue

                        # 创建整数变量表示正方形内的雷数
                        sum_var = model.NewIntVar(0, len(var_list), f'sum_{key}_{i}_{j}_{k}')
                        model.Add(cp_model.LinearExpr.Sum(var_list) == sum_var)
                        # 要求雷数为奇数：先取模，再约束为1
                        parity = model.NewIntVar(0, 1, f'parity_{key}_{i}_{j}_{k}')
                        model.AddModuloEquality(parity, sum_var, 2)
                        model.Add(parity == 1).OnlyEnforceIf(s)
