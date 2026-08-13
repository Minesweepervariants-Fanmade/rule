#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/13 16:19
# @Author  : NT (2201963934)
# @FileName: 1X^.py
"""
[1X^] 十字奇偶: 染色格上的雷的邻居雷数之和是奇数, 非染色格上的邻居雷数是偶数
"""

from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule1XHat(AbstractMinesRule):
    id = "1X'^"
    name = "Cross Parity"
    name.zh_CN = "十字奇偶"
    doc = "For a mine in a dyed cell, the sum of mines in its 8 neighbors is odd; for a mine in an undyed cell, the sum is even."
    doc.zh_CN = "染色格上的雷的邻居雷数之和是奇数, 非染色格上的邻居雷数是偶数"
    author = ("NT", 2201963934)
    tags = ["Variant", "Local", "Dyed", "Mine-Position"]
    creation_time = "2026-08-13"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        添加 CP-SAT 约束。
        对每个雷格，根据其染色状态约束邻居雷数之和的奇偶性。
        """
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for pos in board(mode="position"):
            if not board.is_valid(pos):
                continue

            # 获取当前格子的雷变量
            mine_var = board.get_variable(pos, special="raw")
            if mine_var is None:
                continue

            # 获取周围八格的邻居变量
            neighbor_vars = []
            for neighbor in pos.neighbors(2):
                if board.is_valid(neighbor):
                    var = board.get_variable(neighbor, special="raw")
                    if var is not None:
                        neighbor_vars.append(var)

            if not neighbor_vars:
                continue

            # 计算邻居雷数之和
            neighbor_sum = sum(neighbor_vars)

            # 获取染色状态
            is_dyed = board.get_dyed(pos)

            if is_dyed:
                # 染色格：邻居雷数之和为奇数 (sum % 2 == 1)
                # 用取模约束实现：sum = 2*k + 1
                parity = model.NewIntVar(0, 1, f"parity_{pos}")
                model.AddModuloEquality(parity, neighbor_sum, 2)
                model.Add(parity == 1).OnlyEnforceIf([mine_var, rule_switch])
            else:
                # 非染色格：邻居雷数之和为偶数 (sum % 2 == 0)
                parity = model.NewIntVar(0, 1, f"parity_{pos}")
                model.AddModuloEquality(parity, neighbor_sum, 2)
                model.Add(parity == 0).OnlyEnforceIf([mine_var, rule_switch])

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数：为满足奇偶性约束，总雷数不宜过密或过疏。
        建议为总格子数的 40% 左右。
        """
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells

        info["soft_fn"](int(ub * 0.4), 0)
