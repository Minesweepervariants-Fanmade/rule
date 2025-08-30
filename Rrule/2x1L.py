#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/28 21:26
# @Author  : Wu_RH
# @FileName: 1L^.py
"""
[2*1L]2倍误差：所有线索均比真实值大2或小2或者不变
"""


from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger, get_random


class Rule1Lo(AbstractClueRule):
    name = ["2*1L", "2倍误差"]
    doc = "所有线索均比真实值大2或小2或者不变"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        logger = get_logger()
        for pos, _ in board("N"):
            value = len([_pos for _pos in pos.neighbors(2) if board.get_type(_pos) == "F"])
            random_number = random.random()
            if value == 0:
                value = 0 if random_number < 0.5 else 2
            elif value == 1:
                value = 1 if random_number < 0.5 else 3
            elif value == 7:
                value = 7 if random_number < 0.5 else 5
            elif value == 8:
                value = 8 if random_number < 0.5 else 6
            else:
                value += 2 if random_number > 0.6 else (0 if random_number < 0.3 else -2)
            board.set_value(pos, Value1Lo(pos, count=value))
            logger.debug(f"Set {pos} to 1L^[{value}]")
        return board


class Value1Lo(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self):
        return f"{self.count}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return Rule1Lo.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束：周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count+-1
        if neighbor_vars:
            neighbor_sum = sum(neighbor_vars)
            # 两个布尔变量表示加和为 count + 1 或 count - 1
            b1 = model.NewBoolVar("sum_eq_count_plus_2")
            b2 = model.NewBoolVar("sum_eq_count")
            b3 = model.NewBoolVar("sum_eq_count_minus_2")

            # 将布尔变量与表达式绑定
            model.Add(neighbor_sum == self.count + 2).OnlyEnforceIf([b1, s])
            model.Add(neighbor_sum != self.count + 2).OnlyEnforceIf([b1.Not(), s])

            model.Add(neighbor_sum == self.count).OnlyEnforceIf([b2, s])
            model.Add(neighbor_sum != self.count).OnlyEnforceIf([b2.Not(), s])

            model.Add(neighbor_sum == self.count - 2).OnlyEnforceIf([b3, s])
            model.Add(neighbor_sum != self.count - 2).OnlyEnforceIf([b3.Not(), s])

            model.AddBoolOr([b1, b2, b3]).OnlyEnforceIf(s)
