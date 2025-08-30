#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 18:09
# @Author  : Wu_RH
# @FileName: 1M.py
"""
[1M1X]多雷 + 十字
"""

from ....abs.board import AbstractBoard, AbstractPosition
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

def cross_neighbors(pos : AbstractPosition) -> list[AbstractPosition]:
    return [
        pos.up(2),
        pos.down(2),
        pos.left(2),
        pos.right(2),
        pos.up(1),
        pos.down(1),
        pos.left(1),
        pos.right(1)
    ]

class Rule1M1X(AbstractClueRule):
    name = ["1M1X", "MX", "多雷 + 十字", "Multiple + Cross"]
    doc = ""

    def fill(self, board: 'AbstractBoard'):
        logger = get_logger()
        for pos, _ in board("N"):
            positions = cross_neighbors(pos)
            value = 0
            for t, d in zip(
                    board.batch(positions, "type"),
                    board.batch(positions, "dye")
            ):
                if t != "F":
                    continue
                if d:
                    value += 2
                else:
                    value += 1
            obj = Value1M1X(pos, code=bytes([value]))
            board.set_value(pos, obj)
            logger.debug(f"[1M1X]: put {value} to {pos}")
        return board

    def clue_class(self):
        return Value1M1X


class Value1M1X(AbstractClueValue):
    value: int
    neighbors: list

    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]
        self.neighbors = cross_neighbors(pos)

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule1M1X.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        vals = []
        offset = 0
        dyes = board.batch(self.neighbors, "dye")
        for pos, dye in zip(self.neighbors, dyes):
            if board.get_type(pos) == "C":
                continue
            if board.get_type(pos) == "F":
                offset += 2 if dye else 1
                continue
            if not board.in_bounds(pos):
                continue
            if dye:
                vals.append(board.get_variable(pos) * 2)
            else:
                vals.append(board.get_variable(pos))
        if vals:
            model.Add(sum(vals) == (self.value - offset)).OnlyEnforceIf(s)
