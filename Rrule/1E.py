#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1E] 视野 (Eyesight)：线索表示四方向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1E(AbstractEyesightClueRule):
    name = ["1E", "E", "视野", "Eyesight"]
    doc = "线索表示四方向上能看到的非雷格数量（包括自身），雷会阻挡视"

    @staticmethod
    def direction_funcs(pos):
        return [pos.up, pos.down, pos.right, pos.left]
    
    @classmethod
    def clue_type(cls):
        return Value1E

class Value1E(AbstractEyesightClueValue):
    def direction_funcs(self):
        return Rule1E.direction_funcs(self.pos)
    
    @classmethod
    def type(cls) -> bytes:
        return Rule1E.name[0].encode("ascii")
