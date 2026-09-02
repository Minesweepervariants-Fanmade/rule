#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-09-03
# @Author  : DeepSeek Agent
# @FileName: RL325'.py
"""
[RL325'] 左线规则：所有非雷格周围八格的总雷数只能是 2、3 或 5。
"""

from typing import TYPE_CHECKING

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleRL325p(AbstractMinesRule):
    """
    [RL325'] 左线规则：对于每个非雷格，其周围八格的总雷数只能为 2、3 或 5。
    """
    id = "RL325'"
    name = "RL325'"
    name.zh_CN = "RL325'"
    doc = "For every non-mine cell, the total number of mines in its 8 neighbors must be 2, 3, or 5."
    doc.zh_CN = "所有的非雷格周围八格的总雷数只能是3或2或5"
    author = ("雾", 3140864122)
    tags = ["Variant", "Local", "Mine-Position"]
    creation_time = "2026-09-03"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        添加约束：对于每个非雷格，其周围八格雷数之和 ∈ {2, 3, 5}。
        """
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for pos, mine_var in board(mode="var", special="raw"):
            if mine_var is None:
                continue

            # 获取周围八格的变量
            neighbor_vars: list[IntVar] = []
            for neighbor in pos.neighbors(2):  # 八邻域
                if board.is_valid(neighbor):
                    var = board.get_variable(neighbor, special="raw")
                    if var is not None:
                        neighbor_vars.append(var)

            if not neighbor_vars:
                # 没有邻居（例如 1x1 棋盘），则非雷格不可能满足条件，强制为雷
                model.Add(mine_var == 1).OnlyEnforceIf(rule_switch)
                continue

            # 邻居雷数之和
            neighbor_sum = sum(neighbor_vars)

            # 约束：如果该格是非雷（mine_var == 0），则 neighbor_sum 必须是 2、3 或 5
            # 使用辅助变量表示三个允许值
            is_2 = model.NewBoolVar(f"RL325p_neighbor_sum_2_{pos}")
            is_3 = model.NewBoolVar(f"RL325p_neighbor_sum_3_{pos}")
            is_5 = model.NewBoolVar(f"RL325p_neighbor_sum_5_{pos}")

            model.Add(neighbor_sum == 2).OnlyEnforceIf([is_2, rule_switch])
            model.Add(neighbor_sum != 2).OnlyEnforceIf([is_2.Not(), rule_switch])

            model.Add(neighbor_sum == 3).OnlyEnforceIf([is_3, rule_switch])
            model.Add(neighbor_sum != 3).OnlyEnforceIf([is_3.Not(), rule_switch])

            model.Add(neighbor_sum == 5).OnlyEnforceIf([is_5, rule_switch])
            model.Add(neighbor_sum != 5).OnlyEnforceIf([is_5.Not(), rule_switch])

            # 当该格为非雷时，必须满足其中一个条件
            model.AddBoolOr([is_2, is_3, is_5]).OnlyEnforceIf([mine_var.Not(), rule_switch])

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数：该规则倾向于中等密度，建议占总格子数的 40% 左右。
        """
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells

        # 建议总雷数约为总格子数的 40%，这是一个经验值
        info["soft_fn"](int(ub * 0.4), 0)
