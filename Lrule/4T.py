#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/14 00:33
# @Author  : Wu_RH
# @FileName: 4T.py
"""
[4T]温度计(Temperature): 没写
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_random


class Rule4T(AbstractMinesRule):
    # name = ["4T", "温度计", "Temperature"]
    doc = "将会随机"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        def put_temperature():
            nonlocal board, deny_map, positions
            nonlocal size, random
            end_pos = random.choice([
                _pos for _pos in positions
                if _pos not in deny_map
            ])
            index = int(random.random() * 6)
            if index % 2:
                lenght = int(random.random() * (size[0] - end_pos.x)) + end_pos.x
            else:
                lenght = int(random.random() * (size[1] + end_pos.y)) + end_pos.y

        super().__init__(board, data)
        random = get_random()
        self.map = []
        deny_map = {}
        for key in board.get_interactive_keys():
            size = board.get_config(key, "size")
            positions = [pos for pos, _ in board(key=key)]
            attr_index = 3
            for x in range(100, -1, -1):
                if not x:
                    raise ValueError("Temperature init fail")
                try:
                    put_temperature()
                except:
                    continue
                attr_index -= 1
                if attr_index == 0:
                    break

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        super().create_constraints(board, switch)
