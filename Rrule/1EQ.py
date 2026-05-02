#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EQ] 皇后视野 (Queen Eyesight)：线索表示八个方向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue


class Rule1EQ(AbstractEyesightClueRule):
    id = "1EQ"
    name = "Queen Eyesight"
    name.zh_CN = "皇后视野"
    doc = "Clue shows the number of non-mine cells visible in all eight directions (including the cell itself); mines block the line of sight"
    doc.zh_CN = "线索表示八个方向上能看到的非雷格数量（包括自身），雷会阻挡视线"

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
        return Rule1EQ.id.encode("ascii")
