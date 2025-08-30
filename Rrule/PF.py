#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 20:44
# @Author  : Wu_RH
# @FileName: PF.py
"""
[PF]素因子（Prime Factor）:除0和1外的线索显示真实值的最大素因子
"""
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch

PRIME_MAP = {
    0: [0],
    1: [1],
    2: [2, 4, 8],
    3: [3, 6],
    5: [5],
    7: [7],
}


class RulePF(AbstractClueRule):
    name = ["PF", "素因子", "Prime Factor"]
    doc = "除0和1外的线索显示真实值的最大素因子"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            pos_list = pos.neighbors(2)
            value = board.batch(pos_list, mode="type").count("F")
            for _value in PRIME_MAP:
                if value in PRIME_MAP[_value]:
                    value = _value
                    continue
            obj = ValuePF(pos, bytes([value]))
            board[pos] = obj
        return board


class ValuePF(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.value = code[0]

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return RulePF.name[0].encode()

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        var_list = board.batch(self.pos.neighbors(2), mode="var", drop_none=True)
        value_list = PRIME_MAP[self.value]
        tmp_list = []
        for value in value_list:
            tmp = model.NewBoolVar("tmp")
            model.Add(sum(var_list) == value).OnlyEnforceIf([s, tmp])
            tmp_list.append(tmp)
        model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
