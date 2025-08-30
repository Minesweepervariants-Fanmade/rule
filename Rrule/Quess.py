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


class RuleQuess(AbstractClueRule):
    name = ["?", "问号"]
    doc = "线索表示该格是一个非雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.clear = data is not None

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            board.set_value(pos, VALUE_QUESS)
        return board

    def init_clear(self, board: 'AbstractBoard'):
        if self.clear:
            for pos, obj in board("C"):
                if obj is not VALUE_QUESS:
                    continue
                board.set_value(pos, None)
