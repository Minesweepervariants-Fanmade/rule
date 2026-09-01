#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[7C*] 混合：(1) 所有四连通雷区形状不同，(2) 所有雷八连通。
作者：小中医 (3086842243)
最后编辑时间：2026-05-29 23:18:05
"""

from typing import List, Tuple, Optional

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger

from .connect import connect


class Rule7CStar(AbstractMinesRule):
    """
    [7C*] 混合规则：
    1) 所有四连通雷区形状不同（通过面积互异近似）。
    2) 所有雷八连通。
    """
    id = "7C*"
    name = "7C*"
    name.zh_CN = "7C*"
    doc = "(1) All 4-connected mine regions have different shapes; (2) All mines are 8-connected."
    doc.zh_CN = "(1) 所有四连通雷区形状不同；(2) 所有雷八连通。"
    author = ("小中医", 3086842243)
    tags = ["Creative", "Connectivity", "Strong"]
    creation_time = "2026-05-29 23:18:05"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        为每个交互式题板添加约束：
        1. 所有雷在八连通意义下恰好形成一个连通块（分量数 = 1）。
        2. 所有四连通分量的面积互不相同（形状不同的充分条件）。
        """
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            # 收集该题板所有有效位置及其原始雷变量
            positions_vars: List[Tuple[Position, object]] = []
            for pos, var in board(key=key, mode="variable", special="raw"):
                if var is not None:
                    positions_vars.append((pos, var))
            if not positions_vars:
                continue

            pos_list, var_list = zip(*positions_vars)
            n = len(pos_list)

            # ---------- 1. 八连通约束 ----------
            # 计算八连通分量，并约束分量数为 1
            connect(
                model=model,
                board=board,
                switch=rule_switch,
                component_num=1,          # 恰好一个八连通分量
                connect_value=1,          # 雷连通
                nei_value=2,              # 八连通（距离平方 ≤ 2）
                positions_vars=positions_vars,
                special='raw'
            )

            # ---------- 2. 四连通分量面积互异 ----------
            # 先计算四连通分量，获取分量 ID 和根变量
            root_vars = [model.NewBoolVar(f"root_{key}_{i}") for i in range(n)]
            component_ids = connect(
                model=model,
                board=board,
                switch=rule_switch,
                component_num=None,       # 不限制数量
                connect_value=1,          # 雷连通
                nei_value=1,              # 四连通（距离平方 ≤ 1）
                root_vars=root_vars,
                positions_vars=positions_vars,
                special='raw'
            )

            # 为每个可能的根位置 i 创建面积变量 area_i
            # 面积 = 属于分量 i 且为雷的格子数
            area_vars: List[object] = []
            for i in range(n):
                area_i = model.NewIntVar(0, n, f"area_{key}_{i}")
                area_vars.append(area_i)

                # 计算 area_i = sum_{j} (component_ids[j] == i and var_list[j])
                contribs = []
                for j in range(n):
                    # 创建布尔变量 eq_ji：component_ids[j] == i
                    eq_ji = model.NewBoolVar(f"eq_{key}_{j}_{i}")
                    model.Add(component_ids[j] == i).OnlyEnforceIf([eq_ji, rule_switch])
                    model.Add(component_ids[j] != i).OnlyEnforceIf([eq_ji.Not(), rule_switch])

                    # 贡献变量 contrib = eq_ji and var_list[j]
                    contrib = model.NewBoolVar(f"contrib_{key}_{j}_{i}")
                    model.Add(contrib <= eq_ji).OnlyEnforceIf(rule_switch)
                    model.Add(contrib <= var_list[j]).OnlyEnforceIf(rule_switch)
                    model.Add(contrib >= eq_ji + var_list[j] - 1).OnlyEnforceIf(rule_switch)
                    contribs.append(contrib)

                # area_i = sum(contribs)
                model.Add(area_i == sum(contribs)).OnlyEnforceIf(rule_switch)

            # 约束：对于任意两个根 i, j，如果它们都是根（即有雷分量），则它们的面积必须不同
            for i in range(n):
                for j in range(i + 1, n):
                    model.Add(area_vars[i] != area_vars[j]).OnlyEnforceIf(
                        [root_vars[i], root_vars[j], rule_switch]
                    )

        get_logger().debug("[7C*] 约束已添加")
