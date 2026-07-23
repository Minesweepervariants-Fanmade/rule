#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/23
# @Author  : NT (2201963934)
# @FileName: 1T''''.py

"""
[1T'''']五子棋: 行列斜方向上，雷/非雷中一方至少有一个五连及以上，另一方无五连及以上
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule1Tpppp(AbstractMinesRule):
    id = "1T''''"
    aliases = ("T''''", "1T'''''")
    name = "Goban"
    name.zh_CN = "五子棋"
    doc = "In horizontal, vertical, and diagonal directions, one side (mines or non-mines) must have at least one five-in-a-row or more, while the other side has no five-in-a-row or more"
    doc.zh_CN = "行列斜方向上，雷/非雷中一方至少有一个五连及以上，另一方无五连及以上"
    tags = ["Variant", "Global", "Construction"]
    creation_time = "2026-07-23"
    author = ("NT", 2201963934)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 四个方向：水平(0,1), 垂直(1,0), 对角线(1,1), 反对角线(1,-1)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        # 收集所有五连组的雷变量和非雷变量
        mine_five_groups = []
        non_mine_five_groups = []

        for pos, _ in board():
            for dx, dy in directions:
                # 检查从 pos 开始的连续5个位置是否都在棋盘内
                positions = [pos.shift(dx * i, dy * i) for i in range(5)]
                if all(board.is_valid(p) for p in positions):
                    vars = [board.get_variable(p) for p in positions]

                    # 创建“全雷”变量：这5个位置都是雷
                    all_mine = model.NewBoolVar(f"all_mine_{pos}_{dx}_{dy}")
                    model.AddBoolAnd(vars).OnlyEnforceIf([all_mine, s])
                    model.AddBoolOr([v.Not() for v in vars]).OnlyEnforceIf([all_mine.Not(), s])
                    mine_five_groups.append(all_mine)

                    # 创建“全非雷”变量：这5个位置都是非雷
                    all_non_mine = model.NewBoolVar(f"all_non_mine_{pos}_{dx}_{dy}")
                    model.AddBoolAnd([v.Not() for v in vars]).OnlyEnforceIf([all_non_mine, s])
                    model.AddBoolOr(vars).OnlyEnforceIf([all_non_mine.Not(), s])
                    non_mine_five_groups.append(all_non_mine)

        # 如果棋盘太小，无法形成任何五连，则规则无法满足
        if not mine_five_groups and not non_mine_five_groups:
            # 添加矛盾约束，使得该规则在启用时无解
            model.Add(0 == 1).OnlyEnforceIf(s)
            return

        # 是否存在至少一个雷五连
        mines_five_exists = model.NewBoolVar("mines_five_exists")
        if mine_five_groups:
            model.AddBoolOr(mine_five_groups).OnlyEnforceIf([mines_five_exists, s])
            model.AddBoolAnd([v.Not() for v in mine_five_groups]).OnlyEnforceIf([mines_five_exists.Not(), s])
        else:
            # 没有雷五连组，则雷五连不存在
            model.Add(mines_five_exists == 0).OnlyEnforceIf(s)

        # 是否存在至少一个非雷五连
        non_mines_five_exists = model.NewBoolVar("non_mines_five_exists")
        if non_mine_five_groups:
            model.AddBoolOr(non_mine_five_groups).OnlyEnforceIf([non_mines_five_exists, s])
            model.AddBoolAnd([v.Not() for v in non_mine_five_groups]).OnlyEnforceIf([non_mines_five_exists.Not(), s])
        else:
            # 没有非雷五连组，则非雷五连不存在
            model.Add(non_mines_five_exists == 0).OnlyEnforceIf(s)

        # 核心约束：至少存在一种五连，且不能同时存在两种五连
        model.AddBoolOr([mines_five_exists, non_mines_five_exists]).OnlyEnforceIf(s)
        model.AddBoolOr([mines_five_exists.Not(), non_mines_five_exists.Not()]).OnlyEnforceIf(s)
