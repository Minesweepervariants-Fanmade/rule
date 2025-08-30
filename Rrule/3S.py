#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 3S.py
"""
[3S] 贝壳：线索代表相邻的8个格子中， 中间偏上5格范围和中间偏下5格范围里的雷数(顺序不确定)
"""
from typing import Dict

from minesweepervariants.utils.web_template import MultiNumber
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.image_create import get_text, get_row

from ....utils.tool import get_logger


class Rule3S(AbstractClueRule):
    name = ["3S", "贝壳"]
    doc = "线索代表相邻的8个格子中， 中间偏上5格范围和中间偏下5格范围里的雷数(顺序不确定)"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            value1 = 0
            value2 = 0
            # 方向判断
            if board.get_type(pos.left(1)) == "F":
                value1 += 1
                value2 += 1
            if board.get_type(pos.right(1)) == "F":
                value1 += 1
                value2 += 1
            if board.get_type(pos.up(1)) == "F":
                value1 += 1
            if board.get_type(pos.up(1).left(1)) == "F":
                value1 += 1
            if board.get_type(pos.up(1).right(1)) == "F":
                value1 += 1
            if board.get_type(pos.down(1)) == "F":
                value2 += 1
            if board.get_type(pos.down(1).left(1)) == "F":
                value2 += 1
            if board.get_type(pos.down(1).right(1)) == "F":
                value2 += 1

            if value1 > value2: value1, value2 = value2, value1
            board.set_value(pos, Value3S(pos, count=value1 * 10 + value2))
            logger.debug(f"Set {pos} to 3S[{value1 * 10 + value2}]")
        return board


class Value3S(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.count = code[0]
        else:
            self.count = count
        self.neighbor = ([pos.left(1), pos.right(1), pos.up(1), pos.up(1).left(1), pos.up(1).right(1)],
                         [pos.left(1), pos.right(1), pos.down(1), pos.down(1).left(1), pos.down(1).right(1)])

    def __repr__(self) -> str:
        return f"{self.count // 10} {self.count % 10}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbor[0] + self.neighbor[1]

    def web_component(self, board) -> Dict:
        value = [self.count // 10, self.count % 10]
        value.sort()
        return MultiNumber(value)

    def compose(self, board) -> Dict:
        value = [self.count // 10, self.count % 10]
        value.sort()
        text_a = get_text(str(value[0]))
        text_b = get_text(str(value[1]))
        return get_row(
            text_a,
            text_b
        )

    @classmethod
    def type(cls) -> bytes:
        return Rule3S.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束: 符合Shell"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集周围格子的布尔变量
        neighbor_vars1 = []
        neighbor_vars2 = []
        for neighbor in self.neighbor[0]:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars1.append(var)
        for neighbor in self.neighbor[1]:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars2.append(var)

        if neighbor_vars1 or neighbor_vars2:
            # 定义变量
            t = model.NewBoolVar('t')
            model.Add(sum(neighbor_vars1) == self.count // 10).OnlyEnforceIf([t, s])
            model.Add(sum(neighbor_vars2) == self.count % 10).OnlyEnforceIf([t, s])
            model.Add(sum(neighbor_vars1) == self.count % 10).OnlyEnforceIf([t.Not(), s])
            model.Add(sum(neighbor_vars2) == self.count // 10).OnlyEnforceIf([t.Not(), s])
