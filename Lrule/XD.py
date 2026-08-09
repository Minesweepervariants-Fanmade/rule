#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/09 20:48:58
# @Author  : DeepSeek Agent
# @FileName: XD.py
"""
[XD]斜对偶: 雷组成若干1x2区域（可以斜向），属于不同雷区的雷不能边相邻，可以角相邻。
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class RuleXD(AbstractMinesRule):
    id = "XD"
    aliases = ("DiagonalDual",)
    name = "Diagonal Dual"
    name.zh_CN = "斜对偶"
    doc = "Mines are grouped into 1x2 regions (diagonal allowed). Mines from different groups cannot be edge-adjacent, but can be corner-adjacent."
    doc.zh_CN = "雷组成若干1x2区域（可以斜向），属于不同雷区的雷不能边相邻，可以角相邻。"
    author = ("未知", 740652480)
    tags = ["Variant", "Local", "Strict R", "Strong"]
    creation_time = "2026-08-05"
    last_modified = "2026-08-09"

    def create_constraints(self, board: 'Board', switch):
        """
        实现规则XD的约束。

        方法：使用配对变量。
        - 为每个八方向相邻的位置对创建一个布尔变量，表示它们属于同一雷区。
        - 每个雷必须恰好属于一个配对。
        - 如果两个雷边相邻，则它们必须配对（从而确保不同雷区的雷不能边相邻）。
        - 配对变量隐含两个位置都是雷。
        - 不同配对的雷可以角相邻（因为没有约束禁止角相邻的雷属于不同配对）。
        """
        model = board.get_model()
        s = switch.get(model, self)

        positions = list(board(mode="pos"))
        n = len(positions)
        if n < 2:
            return

        pos_to_idx = {pos: i for i, pos in enumerate(positions)}
        is_mine = [board.get_variable(pos, special='raw') for pos in positions]

        # 配对变量：pair_vars[(i, j)] 表示位置 i 和 j 属于同一雷区
        pair_vars = {}
        for i, pos_i in enumerate(positions):
            for nb in pos_i.neighbors(2):  # 曼哈顿距离 <= 2，即八方向
                j = pos_to_idx.get(nb)
                if j is not None and j > i:
                    var = model.new_bool_var(f'pair_{i}_{j}')
                    pair_vars[(i, j)] = var
                    pair_vars[(j, i)] = var

        # 约束1：每个雷必须恰好与一个其他雷配对
        # 如果 i 是雷，则它必须恰好选择一个配对变量为真
        for i in range(n):
            pairs = [pair_vars[(i, j)] for j in range(n) if (i, j) in pair_vars]
            if pairs:
                model.add(sum(pairs) == is_mine[i]).only_enforce_if(s)
            else:
                model.add(is_mine[i] == 0).only_enforce_if(s)

        # 约束2：如果两个雷边相邻，则它们必须配对
        # 这是为了确保不同雷区的雷不能边相邻
        for i, pos_i in enumerate(positions):
            for nb in pos_i.neighbors(1):  # 曼哈顿距离 == 1，即边相邻
                j = pos_to_idx.get(nb)
                if j is not None and j > i:
                    var = pair_vars.get((i, j))
                    if var is not None:
                        model.add(var == 1).only_enforce_if([is_mine[i], is_mine[j], s])

        # 约束3：如果配对变量为真，则两个位置都是雷
        # 确保配对只包含雷
        for (i, j), var in pair_vars.items():
            if i < j:
                model.add(var <= is_mine[i]).only_enforce_if(s)
                model.add(var <= is_mine[j]).only_enforce_if(s)

        # 注意：不同雷区的雷可以角相邻
        # 这是因为约束1只要求每个雷选择一个配对，没有禁止角相邻的雷选择不同的配对
        # 如果两个雷角相邻，它们可以各自选择与另一个邻居配对，从而属于不同雷区

    def suggest_total(self, info: dict):
        def a(model, total):
            model.add_modulo_equality(0, total, 2)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.295, 0)
        info["hard_fns"].append(a)
