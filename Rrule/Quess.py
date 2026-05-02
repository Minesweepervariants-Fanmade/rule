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
from ....abs.board import AbstractBoard
from ....utils.impl_obj import VALUE_QUESS
from ....utils.tool import get_random


class RuleQuess(AbstractClueRule):
    id = "?"
    name = "Quess"
    name.zh_CN = "问号"
    doc = "Clue indicates that the cell is a non-mine"
    doc.zh_CN = "线索表示该格是一个非雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.data = -1 if data is None else (int(data) if data else 0)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            board.set_value(pos, VALUE_QUESS)
        return board

    def init_clear(self, board: 'AbstractBoard'):
        if self.data == -1:
            for pos, obj in board("C"):
                if obj is not VALUE_QUESS:
                    continue
                board.set_value(pos, None)
        else:
            positions = [pos for pos, obj in board("C") if obj is VALUE_QUESS]
            random = get_random()
            positions = random.sample(positions, k=len(positions) - self.data)
            for pos in positions:
                board.set_value(pos, None)
