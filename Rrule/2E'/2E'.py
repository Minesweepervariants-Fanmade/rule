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
from .....utils.tool import get_random, get_logger

from .....abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.board import Board, Position, MASTER_BOARD_KEY


def alpha(n: int) -> str:
    alpha_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if n < 26:
        return alpha_map[n]
    return alpha_map[n // 26 - 1] + alpha_map[n % 26]


class Rule2Ep(AbstractClueRule):
    id = "2E'"
    name = "Self-Referential"
    name.zh_CN = "自指"
    doc = "If letter X has N mines in its 3x3 area, then the cell with X=N must be a mine"
    doc.zh_CN = "如果字母 X 的 3x3 范围内有 N 个雷，则 X=N 所在的格子为雷"
    tags = ["Original", "Local", "Cryptic"]
    author = ("", 0)
    creation_time = ""

    def __init__(self, board: Board, data=None):
        super().__init__()
        board.set_config(MASTER_BOARD_KEY, "pos_label", True)

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()
        for board_key in board.get_interactive_keys():
            letter_map = {i: [] for i in range(9)}
            for pos, _ in board("F", key=board_key):
                if pos.row not in letter_map:
                    letter_map[pos.row] = []
                letter_map[pos.row].append(pos.col)

            for pos, _ in board("N", key=board_key):
                positions = pos.neighbors(2)
                value = board.batch(positions, mode="type").count("F")
                if not letter_map[value]:
                    board.set_value(pos, VALUE_QUESS)
                    continue
                pos_y = random.choice(letter_map[value])
                obj = Value2Ep(pos, bytes([pos_y]))
                board.set_value(pos, obj)
        return board


class Value2Ep(AbstractClueValue):
    def __init__(self, pos: 'Position', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]  # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{alpha(self.value)}"

    def high_light(self, board: 'Board') -> list['Position']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule2Ep.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        pos = board.get_pos(0, self.value, key=self.pos.board_key)
        line = board.get_col_pos(pos)
        line = board.batch(line, mode="variable")
        neibor_list = board.batch(self.neighbors, mode="variable", drop_none=True)
        # print(line, neibor_list, self.pos)
        sum_vers = sum(neibor_list)
        for index in range(min(9, len(line))):
            var = board.get_variable(
                board.get_pos(index, self.value, key=self.pos.board_key)
            )
            model.add(sum_vers != index).OnlyEnforceIf(var.Not(), s)
