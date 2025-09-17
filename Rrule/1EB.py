#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EB] 主教视野 (Bishop Eyesight)：线索表示斜向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1EX(AbstractEyesightClueRule):
    name = ["1EB", "主教视野", "Bishop Eyesight"]
    doc = "线索表示斜向上能看到的非雷格数量（包括自身），雷会阻挡视线"

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
        return Rule1EX.name[0].encode("ascii")
