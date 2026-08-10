#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-10
# @Author  : 波常未来 (81500378)
# @FileName: Star1Zp.py
"""
[*1Z'] 环非雷: 所有四连通的非雷格必须与其他非雷格组成环。
即每个非雷格在四连通邻域中恰好有 2 个非雷邻居。
"""

from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleStar1Zp(AbstractMinesRule):
    """
    [*1Z'] 环非雷：所有非雷格的四连通邻居中恰好有 2 个非雷格。
    """

    id = "*1Z'"
    name = "Non-mine Loop"
    name.zh_CN = "环非雷"
    doc = "All 4-connected non-mine cells must form loops, i.e., each non-mine cell has exactly 2 non-mine neighbors."
    doc.zh_CN = "所有四连通的非雷格必须与其他非雷格组成环，即每个非雷格恰好有 2 个非雷邻居。"
    author = ("波常未来", 81500378)
    tags = ["Variant", "Connectivity", "Strict Shape"]
    creation_time = "2026-08-10"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        添加 CP-SAT 约束：对每个非雷格，其四连通邻居中非雷格的数量必须等于 2。
        """
        model = board.get_model()
        # 获取该规则的开关变量，用于条件启用
        rule_switch = switch.get(model, self)

        # 遍历所有交互式题板
        for key in board.get_interactive_keys():
            # 获取该题板的边界位置
            bound = board.boundary(key)
            rows = bound.row + 1
            cols = bound.col + 1

            # 遍历所有位置
            for r in range(rows):
                for c in range(cols):
                    pos = board.get_pos(r, c, key)
                    if not board.is_valid(pos):
                        continue

                    # 当前格子的雷变量 (raw)
                    mine_var = board.get_variable(pos, special='raw')
                    if mine_var is None:
                        continue

                    # 收集四个正交邻居的雷变量 (只包括有效邻居)
                    neighbor_vars = []
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        npos = board.get_pos(nr, nc, key)
                        if npos is None:
                            continue
                        if board.is_valid(npos):
                            nvar = board.get_variable(npos, special='raw')
                            if nvar is not None:
                                neighbor_vars.append(nvar)

                    # 如果该位置没有邻居（孤立点），无法满足度数为 2，但这种情况在棋盘上不会发生（除非 1x1 棋盘）。
                    # 但对于 1x1 棋盘，无非雷邻居，如果该格非雷则度数为 0，不满足，所以添加约束使其不能为非雷。
                    if not neighbor_vars:
                        # 如果当前格非雷，则无法满足度数为 2，因此强制其为雷
                        model.Add(mine_var == 1).OnlyEnforceIf(rule_switch)
                        continue

                    # 计算邻居中雷的数量之和
                    neighbor_sum = sum(neighbor_vars)

                    # 期望的非雷邻居数量 = 2
                    # 即：如果当前格非雷 (mine_var == 0)，则 neighbor_sum 必须等于 len(neighbor_vars) - 2
                    # 等价于：当前格非雷 => neighbor_sum == len(neighbor_vars) - 2
                    # 使用 OnlyEnforceIf 实现条件约束
                    model.Add(neighbor_sum == len(neighbor_vars) - 2).OnlyEnforceIf([mine_var.Not(), rule_switch])

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数：此规则不强制特定总雷数，但提供软约束以辅助生成。
        """
        # 计算总格子数
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]

        # 如果棋盘太小（如 1x1），则无法满足规则（因为非雷格无法形成环），因此建议总雷数为总格子数（全部为雷）。
        # 但更通用的处理是：如果棋盘尺寸小于 3x3，则建议全部为雷。
        # 这里简单处理：如果总格子数小于 9（3x3），则建议总雷数为总格子数。
        if total_cells < 9:
            info["soft_fn"](total_cells, 0)
        else:
            # 否则建议总雷数不超过总格子数的 70%，以便有足够非雷格形成环。
            info["soft_fn"](int(total_cells * 0.6), 0)
