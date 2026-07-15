#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/15
# @Author  : NT (2201963934)
# @FileName: 7SD.py
"""
[7SD] 七段数码管：雷显示数字，表示周围八格雷数
"""
from typing import List

from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger


class Rule7SD(AbstractMinesClueRule):
    """七段数码管规则：每个雷格显示0-9的数字，表示其周围八格内的雷数"""
    id = "7SD"
    name = "Seven-Segment Display"
    name.zh_CN = "七段数码管"
    doc = "Mines display digits (0-9) representing the number of mines in the surrounding 8 cells"
    doc.zh_CN = "雷显示0-9的数字，表示周围八格内的雷数"
    tags = ["Creative", "Local"]
    creation_time = "2026-07-15"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """为所有雷格填充数码管线索"""
        for pos, _ in board("F"):
            # 获取周围八格的状态
            nei = pos.neighbors(2)
            nei_types = board.batch(nei, mode="type", drop_none=True)
            # 计算雷数
            mine_count = nei_types.count("F")
            # 创建线索值对象，保存为单字节
            board.set_value(pos, MinesValue7SD(pos, bytes([mine_count])))
        return board


class MinesValue7SD(AbstractMinesValue):
    """七段数码管线索值：存储显示的数字"""
    id = Rule7SD.id

    def __init__(self, pos: 'Position', code: bytes = None):
        """
        初始化数码管线索
        :param pos: 所在位置
        :param code: 单字节，表示显示的数字（0-9）
        """
        if code is None or len(code) != 1:
            raise ValueError("7SD value must be a single byte")
        value = code[0]
        if not (0 <= value <= 9):
            raise ValueError("7SD value must be between 0 and 9")
        self.pos = pos
        self.nei = pos.neighbors(2)
        self.value = SingleIntValue(value, is_mine=True)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractMinesValue':
        """从JSON数据恢复线索对象"""
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid data format for 7SD value")

        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Could not parse 7SD value from data")

        # 验证范围
        if not (0 <= value.value <= 9):
            raise ValueError(f"7SD value out of range: {value.value}")

        return cls(pos, code=bytes([value.value]))

    def high_light(self, board: 'Board') -> list['Position']:
        """高亮周围八格"""
        return self.nei

    def create_constraints(self, board: 'Board', switch):
        """添加约束：显示数字等于周围雷数"""
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 获取周围八格的雷变量
        var_list = board.batch(self.nei, mode="variable", drop_none=True)
        # 约束：周围雷数之和 = 显示的数字
        model.Add(sum(var_list) == self.value.value).OnlyEnforceIf(s)
        logger.trace(f"[7SD] pos={self.pos}, value={self.value.value}")
