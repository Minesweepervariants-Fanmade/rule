#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
"""
[V]标准扫雷：每个数字标明周围八格内雷的数量。
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from typing import Any, cast, List

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


class RuleV(AbstractClueRule):
    id = "V"
    name = "Vanilla"
    name.zh_CN = "标准扫雷"  # type: ignore[attr-defined]
    doc = "Each number indicates the number of mines in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格内雷的数量。"  # type: ignore[attr-defined]
    tags = ["Original", "Local", "Vanilla Variant", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            # `batch` has a dynamic return type; cast to the expected runtime type here
            value_list = cast(List[str], board.batch(pos.neighbors(2), "type"))
            count_val = value_list.count("F")
            board.set_value(pos, ValueV(pos, count=count_val))
        return board


class ValueV(AbstractClueValue):
    def __init__(self, pos: Position, count: int = 0, code: bytes | None = None):
        # AbstractValue expects bytes for `code`; normalize None -> b'' when delegating
        super().__init__(pos, code or b'')
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self):
        return f"{self.count}"

    def high_light(self, board: 'Board') -> list['Position']:
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return b'V'

    def code(self) -> bytes:
        return bytes([self.count])

    def invalid(self, board: 'Board') -> bool:
        return cast(List[str], board.batch(self.neighbor, mode="type", special='raw')).count("N") == 0

    def deduce_cells(self, board: 'Board') -> bool:
        type_dict: dict[str, list[Position]] = {"N": [], "F": []}
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

    def create_constraints(self, board: 'Board', switch: Any):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = cast(Any, board.get_model())
        logger = get_logger()

        # 收集周围格子的布尔变量
        neighbor_vars: list[Any] = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        s = cast(Any, switch).get(model, self.pos)
        if neighbor_vars:
            # model and neighbor variables are dynamically typed (ortools objects)
            model.Add(cast(Any, sum(neighbor_vars)) == self.count).OnlyEnforceIf(s)
            cast(Any, logger).trace(f"[V] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
