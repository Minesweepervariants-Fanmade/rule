#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/01 07:30
# @Author  : Wu_RH
# @FileName: 2E.py
"""
[2E]加密: 线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母
"""

from typing import List, Self, Optional

from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.value_template import SingleValue
from minesweepervariants.utils.value_template import SingleIntValue
from minesweepervariants.board import Board, Position, Size, MASTER_BOARD_KEY
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.utils.impl_obj import VALUE_QUESS, VALUE_CROSS, VALUE_CIRCLE
from minesweepervariants.utils.tool import get_random

NAME_2E = "2U'2E"


class Rule2E(AbstractClueRule):
    id = "2U'2E"
    name = "失衡加密"
    doc = "The number of mines in each col is different."
    doc.zh_CN = "每列的雷数不相同, 一个字母代表一个数字, 一个数字代表一个字母"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        pos_bound = board.boundary()
        size = Size(pos_bound.row + 1, pos_bound.col + 1)
        board.generate_board(NAME_2E, size=size)
        board.set_config(NAME_2E, "pos_label", True)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for pos in board.get_col_pos(board.boundary(NAME_2E)):
            model.add(sum(board.batch(board.get_row_pos(pos), mode="var")) == 1).OnlyEnforceIf(s)
        for pos in board.get_row_pos(board.boundary(NAME_2E)):
            model.add(sum(board.batch(board.get_col_pos(pos), mode="var")) == 1).OnlyEnforceIf(s)

        for pos, pos_2u in zip(
            board.get_row_pos(board.boundary(MASTER_BOARD_KEY)),
            board.get_row_pos(board.boundary(NAME_2E)),
        ):
            col = board.get_col_pos(pos)
            col_2u = board.get_col_pos(pos_2u)
            col_var = board.batch(col, mode="var")
            col_2u_var = board.batch(col_2u, mode="var")
            for index in range(len(col_2u_var)):
                model.add(sum(col_var) == index).only_enforce_if(col_2u_var[index], s)

    def fill(self, board: 'Board') -> 'Board':
        e_nums = []

        for pos in board.get_col_pos(board.boundary(NAME_2E)):
            e_nums.append(board.batch(board.get_row_pos(pos), mode="type").index("F"))

        for pos, _ in board("N"):
            count = board.batch(pos.neighbors(2), mode="type").count("F")
            if count not in e_nums:
                board.set_value(pos, VALUE_QUESS)
            else:
                board.set_value(pos, Value2E(pos, e_nums[count]))

        return board

    def init_clear(self, board: 'Board'):
        for pos, _ in board(key=NAME_2E):
            board.set_value(pos, None)


class Value2E(AbstractClueValue):
    id = Rule2E.id

    def __init__(self, pos: 'Position', value: int):
        super(Value2E, self).__init__(pos)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos
        self.neighbors = pos.neighbors(2)
        self.repr: Optional[int] = None

    def __repr__(self):
        if self.repr:
            return str(self.repr)
        return "ABCDEFGHI"[self.value.value]

    def web_component(self, board):
        if self.repr:
            return super().web_component(board)
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value.value, NAME_2E)
        ), mode="type")
        if "F" in line:
            self.repr = line.index("F")
        return super().web_component(board)

    def compose(self, board):
        if self.repr:
            return super().compose(board)
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value.value, NAME_2E)
        ), mode="type")
        if "F" in line:
            self.repr = line.index("F")
        return super().compose(board)

    @classmethod
    def from_json(cls, pos: 'Position', data) -> Self:
        return cls(pos, data["data"])

    def high_light(self, board: 'Board') -> List['Position']:
        return self.neighbors

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        value_index = self.value.value

        line = board.batch(board.get_col_pos(
            board.get_pos(0, value_index, NAME_2E)
        ), mode="variable")

        neighbors = board.batch(self.neighbors, mode="variable", drop_none=True)

        for index in range(len(line)):
            model.Add(sum(neighbors) == index).OnlyEnforceIf(line[index], s)
            model.Add(sum(neighbors) != index).OnlyEnforceIf(line[index].Not(), s)
