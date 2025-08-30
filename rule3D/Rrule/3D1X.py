#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/12 23:04
# @Author  : Wu_RH
# @FileName: 3D1X.py
"""
[3D1X] 三维十字 (Cross)：线索表示半径为 2 的十字范围内的雷数(上下左右前后)
"""
from typing import List

from .....abs.board import AbstractPosition, AbstractBoard
from .. import Abstract3DClueRule
from .....abs.Rrule import AbstractClueValue


class Rule3D1X(Abstract3DClueRule):
    name = ["3D1X", "三维十字"]
    doc = "线索表示(上下左右前后)2格的十字范围内的雷数"

    def __init__(self, board: AbstractBoard, data: str = None):
        super().__init__(board, data)
        # print(board.show_board())

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            nei = Rule3D1X.pos_neighbors(board, pos, 1)
            nei += Rule3D1X.pos_neighbors(board, pos, 4, 4)
            value = board.batch(nei, mode="type").count("F")
            obj = Value3D1X(pos, bytes([value]))
            board.set_value(pos, obj)

        return board


class Value3D1X(AbstractClueValue):

    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    def __repr__(self) -> str:
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition'] | None:
        nei = Rule3D1X.pos_neighbors(board, self.pos, 1)
        nei += Rule3D1X.pos_neighbors(board, self.pos, 4, 4)
        return nei

    @classmethod
    def type(cls) -> bytes:
        return Rule3D1X.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        nei = Rule3D1X.pos_neighbors(board, self.pos, 1)
        nei += Rule3D1X.pos_neighbors(board, self.pos, 4, 4)

        nei_vars = board.batch(nei, mode="variable", drop_none=True)

        model.Add(sum(nei_vars) == self.value).OnlyEnforceIf(s)
