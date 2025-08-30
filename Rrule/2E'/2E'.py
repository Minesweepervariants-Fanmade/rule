#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/11 16:38
# @Author  : Wu_RH
# @FileName: 2E'.py
"""
[2E']自指:如果字母X周围8格内有N个雷，则标有X=N的格子必定是雷。
"""
from .....utils.impl_obj import VALUE_QUESS
from .....utils.tool import get_random

from .....abs.Rrule import AbstractClueValue, AbstractClueRule
from .....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD


def alpha(n: int) -> str:
    alpha_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if n < 26:
        return alpha_map[n]
    return alpha_map[n // 26 - 1] + alpha_map[n % 26]


class Rule2Ep(AbstractClueRule):
    name = ["2E'", "自指"]
    doc = "如果字母X周围8格内有N个雷，则标有X=N的格子必定是雷。"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__()
        board.set_config(MASTER_BOARD, "pos_label", True)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        letter_map = {i: [] for i in range(9)}
        for pos, _ in board("F"):
            if pos.x not in letter_map:
                letter_map[pos.x] = []
            letter_map[pos.x].append(pos.y)

        for pos, _ in board("N"):
            positions = pos.neighbors(2)
            value = board.batch(positions, mode="type", drop_none=True).count("F")
            if not letter_map[value]:
                board.set_value(pos, VALUE_QUESS)
                continue
            pos_y = random.choice(letter_map[value])
            obj = Value2Ep(pos, bytes([pos_y]))
            board.set_value(pos, obj)
        return board


class Value2Ep(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]  # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{alpha(self.value)}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule2Ep.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        pos = board.get_pos(0, self.value)
        line = board.get_col_pos(pos)
        line = board.batch(line, mode="variable")
        sum_vers = sum(board.batch(self.neighbors, mode="variable", drop_none=True))
        for index in range(min(9, len(line))):
            var = board.get_variable(board.get_pos(index, self.value))
            model.Add(sum_vers != index).OnlyEnforceIf(var.Not()).OnlyEnforceIf(s)
