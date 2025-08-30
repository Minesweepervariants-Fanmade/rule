#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/09 09:33
# @Author  : Wu_RH
# @FileName: 1N.py
"""
[1N] 负雷 (Negative)：线索表示 3x3 范围内染色格与非染色格的雷数差
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition


class Rule1N(AbstractClueRule):
    name = ["1N", "N", "负雷", "Negative"]
    doc = "线索表示 3x3 范围内染色格与非染色格的雷数差"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            value = sum(board.get_type(_pos) == "F" if
                        board.get_dyed(_pos)
                        else -(board.get_type(_pos) == "F")
                        for _pos in pos.neighbors(2))
            obj = Value1N(pos, bytes([abs(value)]))
            board.set_value(pos, obj)
        return board


class Value1N(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.nei = pos.neighbors(2)
        self.pos = pos

    def __repr__(self) -> str:
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.nei

    @classmethod
    def type(cls) -> bytes:
        return Rule1N.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        nei_a = [_pos for _pos in self.nei if board.get_dyed(_pos)]
        nei_b = [_pos for _pos in self.nei if not board.get_dyed(_pos)]

        vars_a = board.batch(nei_a, mode="variable", drop_none=True)
        vars_b = board.batch(nei_b, mode="variable", drop_none=True)

        diff = sum(vars_a) - sum(vars_b)

        # 估计最大绝对值可能为 len(vars_a) + len(vars_b)
        max_abs = len(vars_a) + len(vars_b)
        abs_diff = model.NewIntVar(0, max_abs, "abs_diff")

        model.AddAbsEquality(abs_diff, diff)
        model.Add(abs_diff == self.value).OnlyEnforceIf(s)
