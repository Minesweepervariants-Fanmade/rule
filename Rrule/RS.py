#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[RS] RedStone: 雷视为红石线，线索表示被红石连接的边数
"""

from typing import cast, List

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
        self.value: SingleIntValue = SingleIntValue(value)

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

    def high_light(self, board: 'Board') -> List['Position'] | None:
        positions = self.pos.neighbors(1, 1)
        nei2 = self.pos.neighbors(2, 2)
        for pos in positions:
            if board.get_type(pos) != "F":
                continue
            for _pos in pos.neighbors(1, 1):
                if _pos not in nei2:
                    continue
                if board.get_type(_pos) == "C":
                    continue
                positions.append(_pos)
        return positions

    def create_constraints(self, board, switch):
        # 四格相邻的任意一侧雷 若该侧为雷且该侧的两格对角均不为雷才被计入雷数
        model = board.get_model()
        switch_var = switch.get(model, self)
        adjacent_positions = [pos for pos in self.pos.neighbors(1, 1) if board.in_bounds(pos)]
        distance2_positions = self.pos.neighbors(1, 2)
        side_vars = []
        for pos in adjacent_positions:
            overlapping_positions = [_pos for _pos in pos.neighbors(1, 1) if _pos in distance2_positions]
            negated_overlap_vars = [var.Not() for var in board.batch(overlapping_positions, mode="var", drop_none=True)]
            condition_var = model.new_bool_var("")
            model.add(condition_var == board.get_variable(pos)).OnlyEnforceIf(negated_overlap_vars)
            for neg_var in negated_overlap_vars:
                model.add(condition_var == 0).OnlyEnforceIf(neg_var.Not())
            side_vars.append(condition_var)
        model.add(sum(side_vars) == self.value.value).OnlyEnforceIf(switch_var)