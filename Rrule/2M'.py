#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 18:09
# @Author  : Wu_RH
# @FileName: 1M.py
"""
[2M']多雷: 每个下方是雷的雷被视为两个(总雷数不受限制)
"""

from ....abs.board import AbstractBoard, AbstractPosition
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger


class Rule1M(AbstractClueRule):
    name = ["2M'", "多雷'"]
    doc = "每个下方是雷的雷被视为两个(总雷数不受限制)"

    def fill(self, board: 'AbstractBoard'):
        logger = get_logger()
        for pos, _ in board("N"):
            positions = pos.neighbors(2)
            positions_d = pos.down().neighbors(2)
            value = 0
            for t, d in zip(
                    board.batch(positions, "type"),
                    board.batch(positions_d, "type")
            ):
                if t != "F":
                    continue
                if d == "F":
                    value += 2
                else:
                    value += 1
            obj = Value1M(pos, code=bytes([value]))
            board.set_value(pos, obj)
            logger.debug(f"[1M]: put {obj} to {pos}")
        return board


class Value1M(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = self.neighbors[:]
        pos_list = [self.pos.down().left(), self.pos.down(), self.pos.down().right()]
        for pos in pos_list:
            if board.get_type(pos) == "F":
                positions.append(pos.down())
        return positions

    @classmethod
    def type(cls) -> bytes:
        return Rule1M.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        vals = []
        value = self.value
        for pos in self.neighbors:
            if not board.is_valid(pos):
                continue
            if not board.is_valid(pos.down()):
                if board.get_type(pos) == "F":
                    value -= 1
                elif board.get_type(pos) == "N":
                    vals.append(board.get_variable(pos))
                continue
            if board.get_type(pos) == "F":
                if board.get_type(pos.down()) == "F":
                    value -= 2
                elif board.get_type(pos.down()) == "C":
                    value -= 1
                elif board.get_type(pos.down()) == "N":
                    vals.append(board.get_variable(pos.down()) + 1)
            elif board.get_type(pos) == "N":
                if board.get_type(pos.down()) == "F":
                    vals.append(board.get_variable(pos) * 2)
                elif board.get_type(pos.down()) == "C":
                    vals.append(board.get_variable(pos))
                elif board.get_type(pos.down()) == "N":
                    z = model.NewIntVar(0, 2, f"{pos}*{pos.down()}")
                    a = board.get_variable(pos)
                    b = board.get_variable(pos.down())
                    # 枚举所有情况
                    model.Add(z == 0).OnlyEnforceIf([a.Not()])
                    model.Add(z == 1).OnlyEnforceIf([a, b.Not()])
                    model.Add(z == 2).OnlyEnforceIf([a, b])
                    vals.append(z)
        if vals:
            model.Add(sum(vals) == value).OnlyEnforceIf(s)
