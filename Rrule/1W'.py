#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/09 15:57
# @Author  : QuirkyStorm7988
# @FileName: 1W'.py
"""
[1W'] 最长数墙 (Longest Wall)：线索表示 3x3 范围内最长的连续雷的长度
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue

from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue


def MineStatus_1W(clue: list) -> list[int]:
    """
    返回值：一个int列表，其中存的每一个int表示：
        一个二进制数，第i位（从低到高）表示从左上角开始顺时针旋转，第i个格子的雷情况（是雷->1，非雷->0）
        将这个二进制数转化为十进制存储到元素当中，如42(10) == 00101010(2)，即这个线索格的右上、右下、左下有雷
    """
    ans = []
    a = [0 for _ in range(8)]  # 决策列表

    def dfs(step: int):
        if step >= 8:  # 最终处理
            # 先写没有剪枝的
            test = []
            last = 0
            for i in range(8):
                if a[i]:
                    last += 1
                else:
                    if last != 0: test.append(last)
                    last = 0
            if last != 0: test.append(last)
            if a[-1] and a[0] and len(test) != 1:
                test[0] += test[-1]
                del test[-1]
            if not test: test = [0]
            test.sort()
            if test != clue: return None
            #
            status = 0
            for i in range(8):
                status += 2 ** i * a[i]
            if status not in ans:
                ans.append(status)
            # if a[:] not in ans:
            #     ans.append(a[:])
            return None
        a[step] = 0
        dfs(step + 1)
        a[step] = 1
        dfs(step + 1)
        return None

    dfs(0)
    return ans


class Rule1Wp(AbstractClueRule):
    id = "1W'"
    aliases = ("W'",)
    name = "Longest Wall"
    name.zh_CN = "最长数墙"
    doc = "Clue shows the longest continuous mine length in a 3x3 range"
    doc.zh_CN = "线索表示 3x3 范围内最长的连续雷的长度"
    tags = ["Local", "Number Clue", "Extensive Trial", "Creative"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            pos_list = [pos.right(), pos.right().down(), pos.down(), pos.left().down(),
                        pos.left(), pos.left().up(), pos.up(), pos.right().up()] * 2
            value = 0
            tmp = 0
            for _pos in pos_list:
                if board.get_type(_pos) == "F":
                    tmp += 1
                elif tmp != 0:
                    value = max(value, tmp)
                    tmp = 0
            if tmp > 8:
                value = 8
            obj = Value1Wp(pos, value)
            board[pos] = obj
        return board


class Value1Wp(AbstractClueValue):
    id = Rule1Wp.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        return self.pos.neighbors(2)

    def create_constraints(self, board: 'Board', switch):
        from ._wall_linear import add_longest_window

        model = board.get_model()
        s = switch.get(model, self)

        var_list = board.batch([
            self.pos.right(), self.pos.right().down(),
            self.pos.down(), self.pos.left().down(),
            self.pos.left(), self.pos.left().up(),
            self.pos.up(), self.pos.right().up()
        ], mode="variable")

        # 最长段 = 窗口布尔组合（线性上界 + 存在性析取，替代 256 布局表约束）
        add_longest_window(model, var_list, self.value.value, s)
