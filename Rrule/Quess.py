#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/29 05:15
# @Author  : Wu_RH
# @FileName: Quess.py
"""
[?]标准线索: 线索表示该格是一个非雷
"""

from ....abs.Rrule import AbstractClueRule, ValueQuess
from minesweepervariants.board import Board
from ....utils.impl_obj import VALUE_QUESS
from ....utils.tool import get_random


class RuleQuess(AbstractClueRule):
    id = "?"
    name = "Quess"
    name.zh_CN = "问号"
    doc = "Clue indicates that the cell is a non-mine"
    doc.zh_CN = "线索表示该格是一个非雷"
    tags = ["Meta", "Local", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.data = -1 if data is None else (int(data) if data else 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            board.set_value(pos, VALUE_QUESS)
        return board

    def init_clear(self, board: 'Board'):
        if self.data > -1:
            positions = [pos for pos, obj in board("C", mode="obj") if obj is VALUE_QUESS]
            random = get_random()
            positions = random.sample(positions, k=len(positions) - self.data)
            for pos in positions:
                board.set_value(pos, None)
