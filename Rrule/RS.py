#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[RS] RedStone: 雷视为红石线，线索表示被红石连接的边数
"""

from typing import cast

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template

logger = get_logger(__name__)


class RuleRS(AbstractClueRule):
    id = "RS"
    name = "RedStone"
    name.zh_CN = "红石"
    doc = "Mines are redstone wires, clues are solid blocks, clue shows number of redstone connections on edges"
    doc.zh_CN = "雷视为红石线，线索视为实体方块，线索表示该格被红石连接的边数"
    author = ("雾", 3140864122)
    tags = ["Original", "Local", "Number Clue"]
    creation_time = "2026-06-26"

    @classmethod
    def clue_type(cls):
        return ValueRS

    def fill(self, board):
        for pos, _ in board("N", mode='obj'):
            count = self._compute_connections(board, pos)
            board.set_value(pos, ValueRS(pos, count))
        return board

    @staticmethod
    def _compute_connections(board, pos):
        directions = [
            ('up', 'left', 'right'),
            ('down', 'left', 'right'),
            ('left', 'up', 'down'),
            ('right', 'up', 'down')
        ]
        total = 0
        for dir_name, diag1_name, diag2_name in directions:
            neighbor = getattr(pos, dir_name)()
            if not board.in_bounds(neighbor):
                continue
            if board.get_type(neighbor) != 'F':
                continue
            diag1 = getattr(neighbor, diag1_name)()
            diag2 = getattr(neighbor, diag2_name)()
            diag1_mine = board.in_bounds(diag1) and board.get_type(diag1) == 'F'
            diag2_mine = board.in_bounds(diag2) and board.get_type(diag2) == 'F'
            if not diag1_mine and not diag2_mine:
                total += 1
        return total


class ValueRS(AbstractClueValue):
    id = RuleRS.id

    def __init__(self, pos: Position, value: int, *args, **kwargs):
        # 调用父类构造，但不依赖它设置 self.value
        super().__init__(pos, value, *args, **kwargs)
        self.pos = pos
        # 显式设置 value 属性为 SingleIntValue 对象，以便框架使用
        self.value = SingleIntValue(value)
        # 设置序列化必需的 code
        self.code = RuleRS.id.encode('ascii')
        self.var = None
        self.board = None

    @classmethod
    def from_json(cls, pos: Position, data):
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        value_obj = SingleIntValue.try_from(template_data)
        if value_obj is None:
            raise ValueError("value is empty")
        return cls(pos, value_obj.value)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)
        clue_var = model.NewIntVar(0, 4, f'clue_{self.pos.row}_{self.pos.col}')
        # 确保值等于计算值
        model.Add(clue_var == self.value.value).OnlyEnforceIf(s)
        self.var = clue_var
        self.board = board

    @classmethod
    def type(cls) -> bytes:
        return RuleRS.id.encode("ascii")

    def tag(self, board=None):
        return str(self.value.value)
