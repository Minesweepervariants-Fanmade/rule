#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/06 02:11
# @Author  : QuirkyStorm7988
# @FileName: 1W.py
"""
[1P] 分组 (Partition)：线索表示 3x3 范围内连续雷的组数
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue

from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from ....utils.tool import get_logger


def MineStatus_1P(clue: int) -> list[int]:
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
            if len(test) != clue: return None
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


class Rule1P(AbstractClueRule):
    id = "1P"
    aliases = ("P",)
    name = "Partition"
    name.zh_CN = "分组"
    doc = "Clue indicates the number of continuous mine groups in the 3x3 area"
    doc.zh_CN = "线索表示 3x3 范围内连续雷的组数"
    tags = ["Original", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            nei = [pos.right(), pos.right().down(), pos.down(), pos.left().down(),
                   pos.left(), pos.left().up(), pos.up(), pos.right().up()]
            nei_type = board.batch(nei, mode="type")
            value = 0
            _t = ""
            for t in nei_type:
                if t != "F" and _t == "F":
                    value += 1
                _t = t
            if nei_type[-1] == "F" and nei_type[0] != "F":
                value += 1
            obj = Value1P(pos, value)
            board.set_value(pos, obj)
            logger.debug(f"[1P]set {obj} to {pos}")

        return board


class Value1P(AbstractClueValue):
    id = Rule1P.id

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
        model = board.get_model()
        s = switch.get(model, self)

        var_list = board.batch([
            self.pos.right(), self.pos.right().down(),
            self.pos.down(), self.pos.left().down(),
            self.pos.left(), self.pos.left().up(),
            self.pos.up(), self.pos.right().up()
        ], mode="variable")

        possible_list = [[]]

        for value in MineStatus_1P(self.value.value):
            bool_list = [(value >> i) & 1 == 1 for i in reversed(range(8))]
            flag = False
            for index, var in enumerate(var_list):
                if var is None and bool_list[index]:
                    flag = True
                    break
                if var is None:
                    continue
                possible_list[-1].append(bool_list[index])
            if flag:
                possible_list.pop(-1)
            possible_list.append([])

        if any(v is None for v in var_list):
            var_list = [var for var in var_list if var is not None]
        possible_list.pop(-1)

        model.AddAllowedAssignments(var_list, possible_list).OnlyEnforceIf(s)
