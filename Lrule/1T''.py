#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/15 11:59
# @Author  : Wu_RH
# @FileName: 1T''.py

"""
[1T'']纯三连：每个雷属于唯一的三连组(横/竖/斜)
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1Tpp(AbstractMinesRule):
    name = ["1T''", "纯三连"]
    doc = "每个雷属于唯一的三连组(横/竖/斜)"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        # 实现: 每个雷格必须且只能属于一个三连 (横/竖/对角)
        position_coverage = {pos: [] for pos, _ in board()}

        # 生成所有可能的三连 (8 个方向)
        for pos, _ in board():
            directions = [
                (0, 1), (0, -1), (1, 0), (-1, 0),  # 横/竖
                (1, 1), (1, -1), (-1, 1), (-1, -1)  # 对角
            ]

            for dx, dy in directions:
                positions = [
                    pos,
                    pos.shift(dx, dy),
                    pos.shift(2 * dx, 2 * dy)
                ]

                if all(board.is_valid(p) for p in positions):
                    var_list = [board.get_variable(p) for p in positions]

                    # 三连变量
                    b = model.NewBoolVar(f"triple_{pos}_{dx}_{dy}")
                    model.AddBoolAnd(var_list).OnlyEnforceIf([b, s])

                    for p in positions:
                        position_coverage[p].append(b)

        # 对每个位置，覆盖它的三连数量必须等于该位置是否为雷 (0 或 1)
        for pos, var in board(mode="variable"):
            coverage_list = position_coverage[pos]
            if coverage_list:
                # 将 Bool vars 的和与位置变量相等
                model.Add(sum(coverage_list) == var).OnlyEnforceIf(s)
            else:
                # 若位置没有任何三连覆盖，则不能为雷
                model.Add(var == 0).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):

        def hard_constraint(m, total):
            m.AddModuloEquality(0, total, 3)

        info["hard_fns"].append(hard_constraint)
