#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/05
# @Author  : DeepSeek Agent
# @FileName: XD.py
"""
[XD]斜对偶: 雷组成若干1x2区域（可以斜向），每组雷区中的雷不能和其它雷区中的雷边相邻。
"""
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleXD(AbstractMinesRule):
    id = "XD"
    aliases = ("DiagonalDual",)
    name = "Diagonal Dual"
    name.zh_CN = "斜对偶"
    doc = "Each mine area is a 1x2 rectangle (diagonal allowed), and mines in different groups cannot be edge-adjacent."
    doc.zh_CN = "雷组成若干1x2区域（可以斜向），每组雷区中的雷不能和其它雷区中的雷边相邻。"
    author = ("未知", 740652480)
    tags = ["Variant", "Local", "Strict R", "Strong"]
    creation_time = "2026-08-05"

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, _ in board():
            # 获取八个方向的邻居（上下左右 + 四个对角）
            positions = pos.neighbors(1) + pos.neighbors(2, 2)
            # 统计邻居中的雷数
            sum_vals = sum(board.batch(positions, mode="variable", drop_none=True))
            val = board.get_variable(pos)

            # 核心约束：如果当前格是雷，则其八个邻居中恰好有1个雷
            model.Add(sum_vals == 1).OnlyEnforceIf([val, s])

    def suggest_total(self, info: dict):
        """建议总雷数：雷以对出现，总雷数应为偶数，密度约为30%"""
        def a(model, total):
            model.AddModuloEquality(0, total, 2)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.295, 0)
        info["hard_fns"].append(a)