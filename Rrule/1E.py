#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1E] 视野 (Eyesight)：线索表示四方向上能看到的非雷格数量（包括自身），雷会阻挡视线
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue

class Rule1E(AbstractEyesightClueRule):
    id = "1E"
    aliases = ("E",)
    name = "Eyesight"
    name.zh_CN = "视野"
    doc = "Clue shows the number of non-mine cells visible in the four orthogonal directions (including the cell itself); mines block the line of sight"
    doc.zh_CN = "线索表示四方向上能看到的非雷格数量（包括自身），雷会阻挡视"
    tags = ["Original", "Local", "Number Clue"]

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
        return Rule1E.id.encode("ascii")
