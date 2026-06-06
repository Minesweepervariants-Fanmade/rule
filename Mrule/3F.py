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

from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger


class Rule3F(AbstractMinesClueRule):
    id = "3F"
    name = "Not-V"
    name.zh_CN = "不是V"
    doc = "Mines clue indicates the number of non-mine cells in the surrounding 8 cells"
    doc.zh_CN = "雷线索表示附近八个格子内的非雷格数"
    tags = ["Creative", "Local"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("F"):
            nei_type = board.batch(pos.neighbors(2), mode="type", drop_none=True)
            value = len(nei_type) - nei_type.count("F")
            board.set_value(pos, MinesValue3F(pos, bytes([value])))
        return board


class MinesValue3F(AbstractMinesValue):
    id = "3F"
    def __init__(self, pos: 'Position', code: bytes = None):
        self.nei = pos.neighbors(2)
        self.pos = pos
        self.value = SingleIntValue(code[0], is_mine=True)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        value = SingleIntValue.try_from(_data)

        if value is None:
            raise ValueError()

        return cls(pos, code=bytes([value.value]))

    def high_light(self, board: 'Board') -> list['Position']:
        return self.nei

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()
        var_list = board.batch(self.nei, mode="variable", drop_none=True)
        model.Add(sum(var_list) == (len(var_list) - self.value.value)).OnlyEnforceIf(s)
        logger.trace(f"[4F]{self.value}")
