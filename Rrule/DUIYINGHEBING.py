#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/03/04 23:39
# @Author  : Wu_RH
# @FileName: DUIYINGHEBING.py
"""
[DUIYINGHEBING]对映合并: 周围八格相对的两个雷视为一个
作者:NT (2201963934)
最后编辑时间:2026-03-04 23:18:53
"""
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition


OPPSITE_PAIRS = [
    [(-1, -1), (1, 1)],  # 对角线1
    [(-1, 1), (1, -1)],  # 对角线2
    [(-1, 0), (1, 0)],  # 水平
    [(0, -1), (0, 1)]  # 垂直
]


class RuleDUIYINGHEBING(AbstractClueRule):
    name = ["DUIYINGHEBING", "对映合并"]
    doc = "每个数字标明周围八格内雷的数量。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N", special='raw'):
            value = 0
            for opposite in OPPSITE_PAIRS:
                pos0 = pos.shift(*opposite[0])
                pos1 = pos.shift(*opposite[1])
                if "F" in board.batch([pos0, pos1], "type"):
                    value += 1
            board.set_value(pos, ValueDUIYINGHEBING(pos, code=bytes([value])))
        return board


class ValueDUIYINGHEBING(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, code: bytes = None):
        super().__init__(pos, code)
        self.count = code[0]
        self.neighbor = self.pos.neighbors(2)

    @classmethod
    def type(cls) -> bytes:
        return b'4D\''

    def code(self) -> bytes:
        return bytes([self.count])

    def __repr__(self):
        return f"{self.count}"

    def invalid(self, board: 'AbstractBoard') -> bool:
        return board.batch(self.neighbor, mode="type", special='raw').count("N") == 0

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbor

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            var_list = []
            for opposite in OPPSITE_PAIRS:
                temp_var = model.NewBoolVar("tmp")
                pos0 = self.pos.shift(*opposite[0])
                pos1 = self.pos.shift(*opposite[1])
                tmp_vars = board.batch([pos0, pos1], "var", drop_none=True)
                model.AddBoolOr(tmp_vars).OnlyEnforceIf(temp_var)
                model.Add(sum(tmp_vars) == 0).OnlyEnforceIf(temp_var.Not())
                var_list.append(temp_var)
            model.Add(sum(var_list) == self.count).OnlyEnforceIf(switch.get(model, self))

