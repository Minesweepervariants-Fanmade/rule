#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EB] 主教视野 (Bishop Eyesight)：线索表示斜向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1EX(AbstractEyesightClueRule):
    id = "1EB"
    name = "Bishop Eyesight"
    name.zh_CN = "主教视野"
    doc = "Clue shows the number of non-mine cells visible in the four diagonal directions (including the cell itself); mines block the line of sight"
    doc.zh_CN = "线索表示斜向上能看到的非雷格数量（包括自身），雷会阻挡视线"

    @staticmethod
    def direction_funcs(pos):
        return [
            lambda n:pos.clone().shift(n, n),
            lambda n:pos.clone().shift(n, -n),
            lambda n:pos.clone().shift(-n, n),
            lambda n:pos.clone().shift(-n, -n),
        ]

    @classmethod
    def clue_type(cls):
        return Value1EX

class Value1EX(AbstractEyesightClueValue):
    def direction_funcs(self):
        return Rule1EX.direction_funcs(self.pos)

    @classmethod
    def type(cls) -> bytes:
        return Rule1EX.id.encode("ascii")
