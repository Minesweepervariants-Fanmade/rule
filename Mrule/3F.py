#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/03 04:58
# @Author  : Wu_RH
# @FileName: 4F.py
"""
[3F]测试内容: 雷线索表示附近八个格子内的非雷格数
"""
from typing import List, Dict

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.tool import get_logger


class Rule3F(AbstractMinesClueRule):
    name = ["3F", "不是V"]
    doc = "雷线索表示附近八个格子内的非雷格数"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("F"):
            nei_type = board.batch(pos.neighbors(2), mode="type", drop_none=True)
            value = len(nei_type) - nei_type.count("F")
            board.set_value(pos, MinesValue3F(pos, bytes([value])))
        return board


class MinesValue3F(AbstractMinesValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        self.nei = pos.neighbors(2)
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.nei

    @classmethod
    def type(cls) -> bytes:
        return Rule3F.name[0].encode("ascii")

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()
        var_list = board.batch(self.nei, mode="variable", drop_none=True)
        model.Add(sum(var_list) == (len(var_list) - self.value)).OnlyEnforceIf(s)
        logger.trace(f"[4F]{self.value}")

    def code(self) -> bytes:
        return bytes([self.value])
