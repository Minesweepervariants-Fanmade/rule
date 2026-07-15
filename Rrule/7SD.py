#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/15 06:50
# @Author  : NT
# @FileName: 7SD.py
"""
[7SD]雷由若干组7段数码管合法数位(3x5的结构, 0-9)构成。数位表示与该数码管相接触的格中的雷数。
"""
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.position_set import PositionSet


class Rule7SD(AbstractClueRule):
    id = "7SD"
    name = "Seven Segment Display"
    name.zh_CN = "七段数码管"  # type: ignore[attr-defined]
    doc = "Mines consist of several groups of seven-segment display legal digits (3x5 structure, 0-9). The digit indicates the number of mines in the cells that touch that display."
    doc.zh_CN = "雷由若干组7段数码管合法数位(3x5的结构, 0-9)构成。数位表示与该数码管相接触的格中的雷数。"  # type: ignore[attr-defined]
    tags = ["Number Clue", "Local"]
    creation_time = "2026-05-15"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            neis = PositionSet(pos.neighbors(2))
            neis.to_board(pos.board_key)
            types = board.batch(positions=neis, mode="type")
            count_val = types.count("F")
            board.set_value(pos, Value7SD(pos, count=count_val))
        return board


class Value7SD(AbstractClueValue):
    id = Rule7SD.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.neighbor = PositionSet(pos.neighbors(2))
        self.neighbor.to_board(pos.board_key)
        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'Value7SD':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError()

        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        return list(self.neighbor)

    def invalid(self, board: 'Board') -> bool:
        return board.batch(self.neighbor, mode="type", special='raw').count("N") == 0

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)
        if neighbor_vars:
            model.add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
            logger.trace(f"[7SD] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
