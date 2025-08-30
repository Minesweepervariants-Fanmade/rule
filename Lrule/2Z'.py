#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 19:40
# @Author  : Wu_RH
# @FileName: 2Z'.py
"""
[2Z']零和'(Zero-Sum'):每个4x4方块内的染色格和非染色格雷数相等
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


def block4(board: AbstractBoard, pos: AbstractPosition):
    positions = []
    pos_list = [pos.right(i) for i in range(4)]
    for pos in pos_list:
        positions.extend([pos.down(i) for i in range(4)])
    if '' in board.batch(positions, mode="type"):
        return None
    return positions


class Rule2Zp(AbstractMinesRule):
    name = ["2Z'", "零和'", "Zero-Sum'"]
    doc = "每个4x4方块内的染色格和非染色格雷数相等"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, _ in board():
            block = block4(board, pos)
            if block is None:
                continue
            dye_list = board.batch(block, mode="dye")
            var_list = board.batch(block, mode="var")
            var1_list = [v for v, d in zip(var_list, dye_list) if d]
            var2_list = [v for v, d in zip(var_list, dye_list) if not d]

            model.Add(sum(var1_list) == sum(var2_list)).OnlyEnforceIf(s)
