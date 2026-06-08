#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/01 07:30
# @Author  : Wu_RH
# @FileName: 2E.py
"""
[2E]加密: 线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母
"""

from typing import List, Self

from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, SingleValue, is_value_template
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position, Size
from .....abs.Rrule import AbstractClueRule, AbstractClueValue
from .....utils.impl_obj import VALUE_QUESS, VALUE_CROSS, VALUE_CIRCLE
from .....utils.tool import get_random

NAME_2E = "2E"


class Rule2E(AbstractClueRule):
    id = "2E"
    name = "Encrypted"
    name.zh_CN = "加密"
    doc = "Clues are replaced by letters, each letter corresponds to one clue, and each clue corresponds to one letter"
    doc.zh_CN = "线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母"
    tags = ["Variant", "Local", "Cryptic", "Extensive Trial"]
    author = ("", 0)
    creation_time = ""

    def __init__(self, data=None, board: 'Board' = None):
        super().__init__(board, data)
        pos = board.boundary()
        size = min(pos.x + 1, 9)
        board.generate_board(NAME_2E, Size(size, size))
        board.set_config(NAME_2E, "pos_label", True)

    def fill(self, board: 'Board') -> 'Board':
        self.init_clear(board)
        random = get_random()
        shuffled_nums = [i for i in range(min(9, board.boundary().x + 1))]
        random.shuffle(shuffled_nums)

        for pos, _ in board("N"):
            count = board.batch(pos.neighbors(2), mode="type").count("F")
            if count not in shuffled_nums:
                board.set_value(pos, VALUE_QUESS)
            else:
                code = bytes([shuffled_nums[count]])
                board.set_value(pos, Value2E(pos, code))

        for x, y in enumerate(shuffled_nums):
            pos = board.get_pos(x, y, NAME_2E)
            board.set_value(pos, VALUE_CIRCLE)

        for pos, _ in board("N", key=NAME_2E):
            board.set_value(pos, VALUE_CROSS)

        return board

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        bound = board.boundary(key=NAME_2E)

        row = board.get_row_pos(bound)
        for pos in row:
            line = board.get_col_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s)

        col = board.get_col_pos(bound)
        for pos in col:
            line = board.get_row_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s)

    def init_clear(self, board: 'Board'):
        for pos, _ in board(key=NAME_2E):
            board.set_value(pos, None)


class Value2E(AbstractClueValue):
    id = Rule2E.id

    def __init__(self, pos: 'Position', code: bytes = b''):
        value = "ABCDEFGHI"[code[0]]
        self.value = SingleValue(value)
        self.pos = pos
        self.neighbors = pos.neighbors(2)


    def web_component(self, board):
        if not isinstance(self.value, SingleIntValue):
            assert isinstance(self.value, SingleValue) and isinstance(self.value.value, str)
            value = "ABCDEFGHI".index(self.value.value)
            line = board.batch(board.get_col_pos(
                board.get_pos(0, value, NAME_2E)
            ), mode="type")
            if "F" in line:
                self.value = SingleIntValue(line.index("F"))

        return self.value.web_component()

    def compose(self, board):
        if not isinstance(self.value, SingleIntValue):
            assert isinstance(self.value, SingleValue) and isinstance(self.value.value, str)
            value = "ABCDEFGHI".index(self.value.value)
            line = board.batch(board.get_col_pos(
                board.get_pos(0, value, NAME_2E)
            ), mode="type")
            if "F" in line:
                self.value = SingleIntValue(line.index("F"))

        return self.value.compose()

    def high_light(self, board: 'Board') -> List['Position']:
        return self.neighbors

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> Self:
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        if SingleIntValue.try_from(_data):
            raise ValueError()

        value = SingleValue.try_from(_data)

        if value is None:
            raise ValueError()

        assert isinstance(value.value, str) and value.value in "ABCDEFGHI"

        return cls(pos, code=bytes([ord(value.value) - ord("A")]))

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        assert isinstance(self.value, SingleValue) and not isinstance(self.value, SingleIntValue)

        value = self.value.value
        assert isinstance(value, str) and value in "ABCDEFGHI"
        value_index = "ABCDEFGHI".index(value)

        line = board.batch(board.get_col_pos(
            board.get_pos(0, value_index, NAME_2E)
        ), mode="variable")

        neighbors = board.batch(self.neighbors, mode="variable", drop_none=True)

        for index in range(len(line)):
            model.Add(sum(neighbors) == index).OnlyEnforceIf(line[index], s)
            model.Add(sum(neighbors) != index).OnlyEnforceIf(line[index].Not(), s)
