#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EK] 马步视野 (Knight Eyesight)：线索表示沿着马步方向能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1EK(AbstractEyesightClueRule):
    name = ["1EK", "EK", "马步视野", "Knight Eyesight"]
    doc = "线索表示沿着马步方向能看到的非雷格数量（包括自身），雷会阻挡视线"

    @staticmethod
    def direction_funcs(pos):
        # 马步8个方向，支持n参数，jump改为shift
        return [
            lambda n: pos.clone().shift(2 * n, 1 * n),
            lambda n: pos.clone().shift(2 * n, -1 * n),
            lambda n: pos.clone().shift(-2 * n, 1 * n),
            lambda n: pos.clone().shift(-2 * n, -1 * n),
            lambda n: pos.clone().shift(1 * n, 2 * n),
            lambda n: pos.clone().shift(1 * n, -2 * n),
            lambda n: pos.clone().shift(-1 * n, 2 * n),
            lambda n: pos.clone().shift(-1 * n, -2 * n),
        ]
    
    @classmethod
    def clue_type(cls):
        return Value1EK

class Value1EK(AbstractEyesightClueValue):
    def direction_funcs(self):
        return Rule1EK.direction_funcs(self.pos)
    
    @classmethod
    def type(cls) -> bytes:
        return Rule1EK.name[0].encode("ascii")
