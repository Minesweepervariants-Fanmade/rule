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
from ....abs.board import AbstractBoard, AbstractPosition

class Rule4Y(AbstractClueRule):
    name = ["4Y", "区域", "Area"]
    doc = "线索表示包含该格的最大无雷矩形区域的面积"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            max_area = 1
            rows = board.boundary(pos.board_key).x + 1
            cols = board.boundary(pos.board_key).y + 1
            for r1 in range(rows):
                for c1 in range(cols):
                    for r2 in range(r1, rows):
                        for c2 in range(c1, cols):
                            area = (r2 - r1 + 1) * (c2 - c1 + 1)
                            if area <= max_area:
                                continue
                            if r1 <= pos.x <= r2 and c1 <= pos.y <= c2:
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
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.value = code[0]
        else:
            self.value = area

    def __repr__(self):
        return f"{self.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule4Y.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])
    
    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        x0, y0 = self.pos.x, self.pos.y
        rows = board.boundary(self.pos.board_key).x + 1
        cols = board.boundary(self.pos.board_key).y + 1

        # O(m^2n^2) 优化是什么，开摆
        is_max_rect = []

        for x1 in range(rows):
            for y1 in range(cols):
                for x2 in range(x1, rows):
                    for y2 in range(y1, cols):

                        if not (x1 <= x0 <= x2 and y1 <= y0 <= y2):
                            continue

                        positions = board.get_pos_box(
                            board.get_pos(x1, y1, self.pos.board_key),
                            board.get_pos(x2, y2, self.pos.board_key)
                        )
                        area = (x2 - x1 + 1) * (y2 - y1 + 1)
                        if area > self.value:
                            model.AddBoolOr(board.batch(positions=positions, mode="variable", drop_none=True)).OnlyEnforceIf(s)
                        elif area == self.value:
                            r = model.NewBoolVar(f"rect_{x1}_{y1}_{x2}_{y2}_is_max_area_at_{x0}_{y0}")
                            model.Add(sum(board.batch(positions=positions, mode="variable", drop_none=True)) == 0).OnlyEnforceIf([s, r])
                            is_max_rect.append(r)

        if is_max_rect:
            model.AddBoolOr(list(is_max_rect)).OnlyEnforceIf(s)
