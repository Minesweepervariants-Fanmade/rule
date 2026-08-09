#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-10
# @Author  : Indiebard (Alith) (2513946475)
# @FileName: 5K.py
"""
[5K] 五马步：场上恰有5组雷构成马步，且这5组马步有一个共享雷。
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule5K(AbstractMinesRule):
    """
    [5K] 五马步：场上恰有5组雷构成马步，且这5组马步有一个共享雷。
    """

    id = "5K"
    name = "5 Knight Groups"
    name.zh_CN = "五马步"
    doc = "Exactly 5 pairs of mines form a knight's move, and these 5 pairs share a common mine."
    doc.zh_CN = "场上恰有5组雷构成马步，且这5组马步有一个共享雷"
    author = ("Indiebard (Alith)", 2513946475)
    tags = ["Original", "Local", "Mine-Position"]
    creation_time = "2026-07-27"

    def create_constraints(self, board: Board, switch: Switch) -> None:
        """
        添加 CP‑SAT 约束，实现规则语义。
        1. 对每对马步位置（dx,dy 为 (1,2) 或 (2,1)）创建边变量。
        2. 总边数 == 5。
        3. 存在一个顶点度数 == 5。
        """
        model = board.get_model()
        s = switch.get(model, self)

        # 收集所有交互式题板中的雷变量（只取 raw 命名空间）
        positions = []
        for key in board.get_interactive_keys():
            for pos, var in board(key=key, mode="variable", special="raw"):
                if var is not None:
                    positions.append((pos, var))

        n = len(positions)
        if n < 6:  # 至少需要 1 个中心 + 5 个叶子，所以至少 6 个位置
            model.Add(False).OnlyEnforceIf(s)
            return

        pos_list = [p for p, _ in positions]
        var_list = [v for _, v in positions]
        pos_to_idx = {pos: idx for idx, pos in enumerate(pos_list)}

        # 存储所有边变量
        edges = []  # (i, j, edge_var)
        degree_vars = [model.NewIntVar(0, n, f"degree_{i}") for i in range(n)]

        # 枚举所有位置对，检查是否马步
        for i in range(n):
            for j in range(i + 1, n):
                dx = abs(pos_list[i].col - pos_list[j].col)
                dy = abs(pos_list[i].row - pos_list[j].row)
                if (dx == 1 and dy == 2) or (dx == 2 and dy == 1):
                    edge = model.NewBoolVar(f"edge_{i}_{j}")
                    # edge <= var_i and edge <= var_j
                    model.Add(edge <= var_list[i]).OnlyEnforceIf(s)
                    model.Add(edge <= var_list[j]).OnlyEnforceIf(s)
                    # edge >= var_i + var_j - 1
                    model.Add(edge >= var_list[i] + var_list[j] - 1).OnlyEnforceIf(s)
                    edges.append((i, j, edge))

        # 如果没有边，则规则不可满足
        if not edges:
            model.Add(False).OnlyEnforceIf(s)
            return

        # 计算每个顶点的度数
        for i in range(n):
            incident = [edge for (a, b, edge) in edges if a == i or b == i]
            if incident:
                model.Add(degree_vars[i] == sum(incident)).OnlyEnforceIf(s)
            else:
                model.Add(degree_vars[i] == 0).OnlyEnforceIf(s)

        # 总边数 == 5
        total_edges = sum(edge for (_, _, edge) in edges)
        model.Add(total_edges == 5).OnlyEnforceIf(s)

        # 存在一个顶点度数为 5
        max_degree = model.NewIntVar(0, n, "max_degree")
        model.AddMaxEquality(max_degree, degree_vars).OnlyEnforceIf(s)
        model.Add(max_degree == 5).OnlyEnforceIf(s)

    def suggest_total(self, info: dict) -> None:
        """
        提供软约束，建议总雷数约为 6（中心 + 5 个叶子）。
        由于规则允许额外的孤立雷，此建议可提高生成效率。
        """
        ub = 0
        for key in info["interactive"]:
            ub += info["total"][key]
        # 若棋盘足够大，尝试 6 个雷；否则按比例
        if ub >= 6:
            info["soft_fn"](6, 0)
        else:
            info["soft_fn"](ub, 0)
