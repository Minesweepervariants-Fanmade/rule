#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-09-02
# @Author  : NT (2201963934)
# @FileName: MB-.py

"""
[MB*] 2-平衡点: 任意两个雷的平均位置是整点

规则语义: 对于任意两个雷，它们的横纵坐标之和均为偶数，即所有雷的列奇偶性和行奇偶性分别相同。
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleMBStar(AbstractMinesRule):
    """
    [MB*] 2-平衡点: 任意两个雷的平均位置是整点。
    约束等价于所有雷的列奇偶性相同且行奇偶性相同。
    """

    id = "MB*"
    name = "2-Balance Point"
    name.zh_CN = "2-平衡点"
    doc = "For any two mines, the average position is an integer point."
    doc.zh_CN = "任意两个雷的平均位置是整点。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Strict R", "Mine-Position"]
    creation_time = "2026-09-02"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)

    def create_constraints(self, board: Board, switch: "Switch") -> None:
        """
        添加约束：所有雷的列奇偶性相同，行奇偶性相同。
        引入两个布尔变量 even_col 和 even_row，对于每个雷格，强制其奇偶性等于对应全局变量。
        """
        model = board.get_model()
        s = switch.get(model, self)

        # 全局奇偶性变量
        even_col = model.NewBoolVar("MB*_even_col")
        even_row = model.NewBoolVar("MB*_even_row")

        # 遍历所有位置
        for pos, var in board(mode="var", special='raw'):
            if var is None:
                continue
            # 如果该位置是雷（var==1），则其列奇偶性必须等于 even_col
            model.Add(even_col == pos.col % 2).OnlyEnforceIf([var, s])
            # 同理行奇偶性
            model.Add(even_row == pos.row % 2).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict) -> None:
        """
        软约束建议总雷数。
        该规则不强制特定总数，但可建议一个合理的值（例如总格子的40%）。
        """
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        # 建议总雷数约为总格子数的40%
        info["soft_fn"](int(ub * 0.4), 0)
