#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1EK] 马步视野 (Knight Eyesight)：线索表示沿着马步方向能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1EK(AbstractEyesightClueRule):
    id = "1EK"
    name = "Knight Eyesight"
    name.zh_CN = "马步视野"
    doc = "Clue shows the number of non-mine cells visible in the knight's move directions (including the cell itself); mines block the line of sight"
    doc.zh_CN = "线索表示沿着马步方向能看到的非雷格数量（包括自身），雷会阻挡视线"

    tags = ["Variant", "Local", "Arrow Clue", "Aux Board"]

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
        return Rule1EK.id.encode("ascii")
