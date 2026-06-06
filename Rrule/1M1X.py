#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 18:09
# @Author  : Wu_RH
# @FileName: 1M.py
"""
[1M1X]多雷 + 十字
"""


from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def cross_neighbors(pos : Position) -> list[Position]:
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
    id = "1M1X"
    name = "Multiple + Cross"
    name.zh_CN = "多雷 + 十字"
    doc = ""

    tags = ["Meta", "Local", "Number Clue"]
    creation_time = "2025-08-23"
    author = ("", 0)

    def fill(self, board: 'Board'):
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
            obj = Value1M1X(pos, value)
            board.set_value(pos, obj)
            logger.debug(f"[1M1X]: put {value} to {pos}")
        return board

    def clue_class(self):
        return Value1M1X


class Value1M1X(AbstractClueValue):
    id = Rule1M1X.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        return cross_neighbors(self.pos)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        vals = []
        offset = 0
        dyes = board.batch(cross_neighbors(self.pos), "dye")
        for pos, dye in zip(cross_neighbors(self.pos), dyes):
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
            model.Add(sum(vals) == (self.value.value - offset)).OnlyEnforceIf(s)
