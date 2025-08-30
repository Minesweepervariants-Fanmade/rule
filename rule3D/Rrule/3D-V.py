#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
"""
[3DV]3D扫雷：每个数字标明周围26格内雷的数量。
"""
from typing import List

from .. import Abstract3DClueRule

from .....abs.Rrule import AbstractClueValue
from .....abs.board import AbstractBoard, AbstractPosition

from .....utils.tool import get_logger
from .....utils.impl_obj import VALUE_QUESS, MINES_TAG


class Rule3DV(Abstract3DClueRule):
    name = ["3DV", "3D标准扫雷"]
    doc = "每个数字标明周围26格内雷的数量。"

    def __init__(self, board: AbstractBoard, data: str = None):
        super().__init__(board, data)
        ValueV.rule = self

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        ValueV.rule = self
        logger = get_logger()
        for pos, _ in board("N"):
            positions = []
            for _pos in [pos, self.up(board, pos), self.down(board, pos)]:
                if _pos is None:
                    continue
                positions.extend(_pos.neighbors(0, 2))
            value = board.batch(positions, mode="type").count("F")
            board.set_value(pos, ValueV(pos, count=value))
            logger.debug(f"Set {pos} to 3D-V[{value}]")
        return board


class ValueV(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        self.neighbor = None
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count

    def __repr__(self):
        return f"{self.count}"

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition']:
        if self.neighbor:
            return self.neighbor
        self.neighbor = []
        for _pos in [self.pos, Rule3DV.up(board, self.pos), Rule3DV.down(board, self.pos)]:
            if _pos is None:
                continue
            self.neighbor.extend(_pos.neighbors(0, 2))
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return b'3DV'

    def code(self) -> bytes:
        return bytes([self.count])

    def invalid(self, board: 'AbstractBoard') -> bool:
        self.neighbor = []
        for _pos in [self.pos, Rule3DV.up(board, self.pos), Rule3DV.down(board, self.pos)]:
            if _pos is None:
                continue
            self.neighbor.extend(_pos.neighbors(0, 2))
        return board.batch(self.neighbor, mode="type").count("N") == 0

    def deduce_cells(self, board: 'AbstractBoard') -> bool:
        type_dict = {"N": [], "F": []}
        self.neighbor = []
        for _pos in [self.pos, Rule3DV.up(board, self.pos), Rule3DV.down(board, self.pos)]:
            if _pos is None:
                continue
            self.neighbor.extend(_pos.neighbors(0, 2))
        for pos in self.neighbor:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)
        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])
        if n_num == 0:
            return False
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)

        self.neighbor = []
        for _pos in [self.pos, Rule3DV.up(board, self.pos), Rule3DV.down(board, self.pos)]:
            if _pos is None:
                continue
            self.neighbor.extend(_pos.neighbors(0, 2))

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
            get_logger().trace(f"[V] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
