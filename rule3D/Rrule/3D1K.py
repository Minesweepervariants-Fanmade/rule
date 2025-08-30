#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/07 16:08
# @Author  : Wu_RH
# @FileName: 3D1K.py
from typing import List

from minesweepervariants.abs.Rrule import AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from .. import Abstract3DClueRule


class Rule3D1K(Abstract3DClueRule):
    name = ["3DK", "3D1K", "3D标准扫雷"]
    doc = "每个数字标明周围26格内雷的数量。"

    def __init__(self, board: AbstractBoard, data: str = None):
        super().__init__(board, data)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            positions = self.pos_neighbors(board, pos, 5, 5)
            value = board.batch(positions, mode="type").count("F")
            board.set_value(pos, ValueK(pos, code=bytes([value])))
        return board


class ValueK(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return f"{self.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule3D1K.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition'] | None:
        return Rule3D1K.pos_neighbors(board, self.pos, 5, 5)

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)

        neighbor = Rule3D1K.pos_neighbors(board, self.pos, 5, 5)

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.value).OnlyEnforceIf(s)
