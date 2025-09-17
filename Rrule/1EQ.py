#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EQ] 皇后视野 (Queen Eyesight)：线索表示八个方向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue


class Rule1EQ(AbstractEyesightClueRule):
    name = ["1EQ", "皇后视野", "Queen Eyesight"]
    doc = "线索表示八个方向上能看到的非雷格数量（包括自身），雷会阻挡视线"

    @staticmethod
    def direction_funcs(pos):
        return [
            lambda n:pos.clone().shift(n, n),
            lambda n:pos.clone().shift(n, -n),
            lambda n:pos.clone().shift(-n, n),
            lambda n:pos.clone().shift(-n, -n),
            lambda n:pos.clone().shift(0, n),
            lambda n:pos.clone().shift(0, -n),
            lambda n:pos.clone().shift(n, 0),
            lambda n:pos.clone().shift(-n, 0),
        ]
    
    @classmethod
    def clue_type(cls):
        return Value1EQ

class Value1EQ(AbstractEyesightClueValue):
    def direction_funcs(self):
        return Rule1EQ.direction_funcs(self.pos)
    
    @classmethod
    def type(cls) -> bytes:
        return Rule1EQ.name[0].encode("ascii")
