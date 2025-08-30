#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 3A'.py
"""
[3A']兰顿蚂蚁: 数字表示兰顿蚂蚁从线索格出发直至走出题板外所经过的格子总数(不重复计数)。
箭头表示兰顿蚂蚁的初始方向，经过非雷格顺时针旋转90度(右转)，经过雷格逆时针旋转90度(左转)。
"""
from minesweepervariants.impl.summon.solver import Switch
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition


def put(pos: 'AbstractPosition', board: 'AbstractBoard'):
    clue = board.get_value(pos)


class Rule3Ap(AbstractClueRule):
    name = ""

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        pass


class Value3Ap(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)

    def __repr__(self) -> str:
        pass

    @classmethod
    def type(cls) -> bytes:
        return Rule3Ap.name.encode("ascii")

    def code(self) -> bytes:
        pass

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        pass

    def deduce_cells(self, board: 'AbstractBoard') -> bool:
        pass

    def check(self, board: 'AbstractBoard') -> bool:
        pass

    @classmethod
    def method_choose(cls) -> int:
        return 1
