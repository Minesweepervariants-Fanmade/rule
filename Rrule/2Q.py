#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/11 21:41
# @Author  : Wu_RH
# @FileName: 2Q.py
"""
[2Q]皇后Queen: 线索表示八方向有雷的方向数。
"""
from typing import List

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


def pos_shift(
        board: AbstractBoard,
        pos: AbstractPosition,
        index: int
):
    shift = [
        (1, 1), (1, 0), (1, -1),
        (0, 1), (0, -1),
        (-1, 1), (-1, 0), (-1, -1)
    ][index]
    positions = []
    while board.is_valid(_pos := pos.shift(shift[0], shift[1])):
        shift = (
            0 if shift[0] == 0 else (shift[0] + 1 if shift[0] > 0 else shift[0] - 1),
            0 if shift[1] == 0 else (shift[1] + 1 if shift[1] > 0 else shift[1] - 1),
        )
        positions.append(_pos)
    return positions


class Rule2Q(AbstractClueRule):
    name = ["2Q", "皇后", "Queen"]
    doc = "线索表示八方向有雷的方向数量"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            value = 0
            for i in range(8):
                if "F" in board.batch(pos_shift(board, pos, i), mode="type"):
                    value += 1
            board[pos] = Value2Q(pos, bytes([value]))
        return board


class Value2Q(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.value = code[0]

    def __repr__(self):
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition'] | None:
        positions = []

        for i in range(8):
            pos_list = pos_shift(board, self.pos, i)
            type_list = board.batch(pos_list, mode="type")
            if "F" in type_list:
                positions.append(pos_list[type_list.index("F")])
            else:
                positions.extend(pos_list)

        return positions

    @classmethod
    def type(cls) -> bytes:
        return Rule2Q.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        tmp_vars = []
        for index in range(8):
            tmp = model.NewBoolVar("tmp")
            var_list = board.batch(pos_shift(board, self.pos, index), mode="variable")
            model.AddBoolOr(var_list).OnlyEnforceIf(tmp)
            model.Add(sum(var_list) == 0).OnlyEnforceIf(tmp.Not())
            tmp_vars.append(tmp)
        model.Add(sum(tmp_vars) == self.value).OnlyEnforceIf(s)
