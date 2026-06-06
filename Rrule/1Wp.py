#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/19
# @Author  : Assistant
# @FileName: 1Wp.py
"""
[1Wp] 1Wplus: 线索是两个十六进制数字，表示周围8格顺时针方向的雷分布二进制转为十六进制
"""

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from minesweepervariants.utils.tool import get_random


class Rule1Wp(AbstractClueRule):
    id = "1Wp"
    aliases = ("Wp",)
    name = "1Wplus"
    name.zh_CN = "十六进制线索"
    doc = "Clue shows two hex digits representing mine pattern in 8 neighbors clockwise"
    doc.zh_CN = "数字线索是两个十六进制数字，代表从某个格子顺时针旋转后雷代表1非雷代表0的8位二进制数字转为十六进制"
    tags = ["Local", "Number Clue", "Creative"]
    creation_time = "2026-05-19"
    author = ("雾", 3140864122)

    def fill(self, board: 'Board') -> 'Board':
        """为每个有完整8个邻居的格子设置十六进制线索"""
        RANDOM = get_random()
        for pos, _ in board("N"):
            # 顺序: 上, 右上, 右, 右下, 下, 左下, 左, 左上
            index = RANDOM.randint(0, 7)
            neighbors = ([
                pos.up(), pos.right().up(), pos.right(),
                pos.right().down(), pos.down(), pos.left().down(),
                pos.left(), pos.left().up()
            ] * 2)[index: index + 8]
            # 计算8位二进制值
            value = 0
            for p in neighbors:
                value <<= 1
                value += (board.get_type(p) == "F")
            # 存储线索对象
            obj = Value1Wp(pos, bytes([value >> 4, value & 0xf]))
            board[pos] = obj
        return board


class Value1Wp(AbstractClueValue):
    id = "1Wp"
    def __init__(self, pos: 'Position', code: bytes = b''):
        self.high = code[0]     # 0-15
        self.low = code[1]      # 0-15
        self.pos = pos

    def __repr__(self) -> str:
        return f"{self.high:01X}{self.low:01X}"

    def code(self) -> bytes:
        return bytes([self.high, self.low])

    def high_light(self, board: 'Board') -> list['Position']:
        return self.pos.neighbors(2)

    @classmethod
    def type(cls) -> bytes:
        return Rule1Wp.id.encode("ascii")

    def create_constraints(self, board: 'Board', switch):
        """添加约束：周围8个格子的雷状态必须与线索值一致"""
        model = board.get_model()
        s = switch.get(model, self)

        bits = []
        v = (self.high << 4) | self.low  # 0-255
        for i in range(8):
            bits.append(bool((v >> (7 - i)) & 1))

        # 顺序必须与 fill 中一致
        neighbors = [
            self.pos.up(), self.pos.right().up(), self.pos.right(),
            self.pos.right().down(), self.pos.down(), self.pos.left().down(),
            self.pos.left(), self.pos.left().up()
        ]
        var_list = board.batch(neighbors, mode="variable")
        allowed = []
        for i in range(8):
            allowed.append([])
            for j in range(8):
                j -= i
                if var_list[j + i] is None:
                    if bits[j]:
                        allowed.pop(-1)
                        break
                    continue
                allowed[-1].append(bits[j])
        var_list = [var for var in var_list if var is not None]
        # 根据线索值生成唯一的允许组合
        model.add_allowed_assignments(var_list, allowed).OnlyEnforceIf(s)
