#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/01 07:30
# @Author  : Wu_RH
# @FileName: 2E.py
"""
[2E]加密: 线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母
"""
from typing import Self

from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.value_template import Template
from minesweepervariants.utils.value_template import SingleIntValue
from minesweepervariants.board import Board, Position
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.utils.impl_obj import VALUE_QUESS
from minesweepervariants.utils.tool import get_random


def alpha(n: int) -> str:
    alpha_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if n < 26:
        return alpha_map[n]
    return alpha_map[n // 26 - 1] + alpha_map[n % 26]


class Rule2E(AbstractClueRule):
    id = "2U'2E'"
    name = "失衡自指"
    doc = ("For column X, if the mine count is N, then position X=N must be a mine; "
           "for clue X, if there are N mines around it, then position X=N must be a mine.")
    doc.zh_CN = "对于列X, 若雷数=N那么X=N处必须为雷, 对于线索X, 若周围有N个雷那么X=N处必须为雷"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2026-08-02"
    author = ("", 0)

    def __init__(self, board: Board, data=None):
        super().__init__()
        for key in board.get_interactive_keys():
            board.set_config(key, "pos_label", True)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            for pos in board.get_row_pos(pos_bound):
                col = board.get_col_pos(pos)
                col_var = board.batch(col, mode="var")
                for index in range(len(col_var)):
                    model.add(
                        sum(col_var) != index
                    ).only_enforce_if(
                        col_var[index].Not(), s
                    )

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
                obj = Value2Ep(pos, pos_y)
                board.set_value(pos, obj)
        return board


class Value2Ep(AbstractClueValue):
    id = Rule2E.id

    def __init__(self, pos: 'Position', count: int):
        super().__init__(pos)
        self.value: SingleIntValue = SingleIntValue(count)  # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{alpha(self.value.value)}"

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> Self:
        return cls(pos, data["data"])

    def high_light(self, board: 'Board') -> list['Position']:
        return self.neighbors

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        pos = board.get_pos(0, self.value.value, key=self.pos.board_key)
        line = board.get_col_pos(pos)
        line = board.batch(line, mode="variable")
        neibor_list = board.batch(self.neighbors, mode="variable", drop_none=True)
        sum_vers = sum(neibor_list)
        for index in range(min(9, len(line))):
            var = board.get_variable(
                board.get_pos(index, self.value.value, key=self.pos.board_key)
            )
            model.add(sum_vers != index).OnlyEnforceIf(var.Not(), s)
