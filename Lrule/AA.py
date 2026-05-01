#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/03/01 13:28
# @Author  : botif (1643337042)
# @FileName: AA.py
"""
[AA] 吸引 (Attraction)：场上不存在横竖方向上的雷—空—雷(由AI生成 质量不保证)
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleAA(AbstractMinesRule):
    id = "AA"
    name = "Attraction"
    name.zh_CN = "吸引"
    doc = "场上不存在横竖方向上的雷—空—雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 水平方向检查：雷 - 空 - 雷
        for pos, var in board(mode="variable"):
            # 检查右边两个格子是否存在
            right1 = pos.right()
            right2 = pos.right(2)
            if board.in_bounds(right1) and board.in_bounds(right2):
                var_r1 = board.get_variable(right1)
                var_r2 = board.get_variable(right2)
                # 不允许 var == 1, var_r1 == 0, var_r2 == 1
                # 等价于 (var == 0) or (var_r1 == 1) or (var_r2 == 0)
                model.AddBoolOr([var.Not(), var_r1, var_r2.Not()]).OnlyEnforceIf(s)

        # 垂直方向检查：雷 - 空 - 雷
        for pos, var in board(mode="variable"):
            down1 = pos.down()
            down2 = pos.down(2)
            if board.in_bounds(down1) and board.in_bounds(down2):
                var_d1 = board.get_variable(down1)
                var_d2 = board.get_variable(down2)
                model.AddBoolOr([var.Not(), var_d1, var_d2.Not()]).OnlyEnforceIf(s)