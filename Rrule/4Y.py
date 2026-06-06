#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/21 15:32
# @Author  : Wu_RH
# @FileName: 4Y.py
"""
[4Y] 区域：线索表示包含该格的最大无雷矩形区域的面积
"""

from minesweepervariants.impl.summon.solver import Switch
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

class Rule4Y(AbstractClueRule):
    id = "4Y"
    name = "Area"
    name.zh_CN = "区域"
    doc = "Clue indicates the area of the largest mine-free rectangle containing this cell"
    doc.zh_CN = "线索表示包含该格的最大无雷矩形区域的面积"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2025-08-21"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            max_area = 1
            rows = board.boundary(pos.board_key).row + 1
            cols = board.boundary(pos.board_key).col + 1
            for r1 in range(rows):
                for c1 in range(cols):
                    for r2 in range(r1, rows):
                        for c2 in range(c1, cols):
                            area = (r2 - r1 + 1) * (c2 - c1 + 1)
                            if area <= max_area:
                                continue
                            if r1 <= pos.row <= r2 and c1 <= pos.col <= c2:
                                box = board.get_pos_box(
                                    board.get_pos(r1, c1, pos.board_key),
                                    board.get_pos(r2, c2, pos.board_key)
                                )
                                if any(board.get_type(p) == "F" for p in box):
                                    continue
                                max_area = area
            board.set_value(pos, Value4Y(pos, code=bytes([max_area])))
        return board

class Value4Y(AbstractClueValue):
    id = "4Y"
    def __init__(self, pos: 'Position', code: bytes):
        super().__init__(pos, code)
        self.value = code[0]

    def __repr__(self):
        return f"{self.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule4Y.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: Board, switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        row0, col0 = self.pos.row, self.pos.col
        rows = board.boundary(self.pos.board_key).row + 1
        cols = board.boundary(self.pos.board_key).col + 1

        # O(m^2n^2) 优化是什么，开摆
        is_max_rect = []

        for row in range(0, row0 + 1):
            for row2 in range(row0, rows):
                for col1 in range(0, col0 + 1):
                    for col2 in range(col0, cols):
                        positions = board.get_pos_box(
                            board.get_pos(row, col1, self.pos.board_key),
                            board.get_pos(row2, col2, self.pos.board_key)
                        )
                        area = (row2 - row + 1) * (col2 - col1 + 1)
                        if area > self.value:
                            model.AddBoolOr(board.batch(positions=positions, mode="variable", drop_none=True)).OnlyEnforceIf(s)
                        elif area == self.value:
                            r = model.NewBoolVar(f"rect_{row}_{col1}_{row2}_{col2}_is_max_area_at_{row0}_{col0}")
                            model.Add(sum(board.batch(positions=positions, mode="variable", drop_none=True)) == 0).OnlyEnforceIf([s, r])
                            is_max_rect.append(r)

        if is_max_rect:
            model.AddBoolOr(list(is_max_rect)).OnlyEnforceIf(s)
