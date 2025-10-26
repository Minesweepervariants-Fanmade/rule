#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
"""
[V']雷值：每个数字标明周围八格内雷值之和。
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


class RuleV(AbstractClueRule):
    name = ["V'", "雷值", "Value"]
    doc = "每个数字标明周围八格内雷值之和"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "V'"

        class ValueV(AbstractClueValue):
            def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None, rule=self.rule):
                super().__init__(pos, code)
                self.rule = rule
                if code is not None:
                    # 从字节码解码
                    self.count = code[0]
                else:
                    # 直接初始化
                    self.count = count
                self.neighbor = self.pos.neighbors(2)

            def __repr__(self):
                return f"{self.count}"

            @classmethod
            def type(cls) -> bytes:
                return self.rule.encode()

            def code(self) -> bytes:
                return bytes([self.count])

            def create_constraints(self, board: 'AbstractBoard', switch):
                """创建CP-SAT约束: 周围雷数等于count"""
                model = board.get_model()

                # 收集周围格子的布尔变量
                neighbor_vars = []
                for neighbor in self.neighbor:  # 8方向相邻格子
                    if board.in_bounds(neighbor):
                        var = board.get_variable(neighbor, special=self.rule)
                        neighbor_vars.append(var)

                # 添加约束：周围雷数等于count
                if neighbor_vars:
                    model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(switch.get(model, self.pos))
                    get_logger().trace(f"[V'] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")

        self.ValueV = ValueV


    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            value = board.batch(pos.neighbors(2), "type", special=self.rule)
            value = sum(v or 0 for v in value)
            board.set_value(pos, self.ValueV(pos, count=value, rule=self.rule))
        return board
