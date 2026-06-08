#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/06 02:11
# @Author  : QuirkyStorm7988
# @FileName: 1W.py
"""
[1W] 数墙 (Wall)：线索表示 3x3 范围内每组连续雷的长度
"""
from typing import Dict, Sequence

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, MultiIntValue
from minesweepervariants.board import JSONObject, Position, Board
from ....utils.image_template import get_text, get_row, get_col
from ....utils.image_template import get_dummy
from ....utils.tool import get_logger

from ....utils.web_template import MultiNumber


def MineStatus_1W(clue: list) -> list:
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


class Rule1W(AbstractClueRule):
    id = "1W"
    aliases = ("W",)
    name = "Wall"
    name.zh_CN = "数墙"
    doc = "Clue indicates the length of each continuous mine group in the 3x3 area"
    doc.zh_CN = "线索表示 3x3 范围内每组连续雷的长度"
    tags = ["Original", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            nei = [pos.right(), pos.right().down(), pos.down(), pos.left().down(),
                   pos.left(), pos.left().up(), pos.up(), pos.right().up()]
            values = []
            nei_type = board.batch(nei, mode="type")
            value = 0
            t = ""
            for t in nei_type:
                if t == "F":
                    value += 1
                elif value != 0:
                    values.append(value)
                    value = 0
            if value != 0 and t == nei_type[0] == "F":
                if values:
                    values[0] += value
                else:
                    values.append(value)
            elif value != 0:
                values.append(value)
            if len(values) == 0:
                values.append(0)
            values.sort()
            obj = Value1W(pos, values)
            board.set_value(pos, obj)
            logger.debug(f"[1W]set {obj} to {pos}")

        return board


class Value1W(AbstractClueValue):
    id = Rule1W.id

    def __init__(self, pos: 'Position', value: list[int], *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.value: MultiIntValue = MultiIntValue(value)
        self.values = value
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = MultiIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        return self.pos.neighbors(2)

    def web_component(self, board) -> Dict:
        if not self.values:
            return MultiNumber([0])
        return MultiNumber(self.values)

    def compose(self, board) -> Dict:
        if len(self.values) <= 1:
            value = 0
            if len(self.values) == 1:
                value = self.values[0]
            return get_col(
                get_dummy(height=0.175),
                get_text(str(value)),
                get_dummy(height=0.175),
            )
        if len(self.values) == 2:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            return get_col(
                get_dummy(height=0.175),
                get_row(
                    text_a,
                    text_b
                ),
                get_dummy(height=0.175),
            )
        elif len(self.values) == 3:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            text_c = get_text(str(self.values[2]))
            return get_col(
                get_row(
                    text_a,
                    text_b,
                    # spacing=0
                ),
                text_c,
            )
        elif len(self.values) == 4:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            text_c = get_text(str(self.values[2]))
            text_d = get_text(str(self.values[3]))
            return get_col(
                get_row(
                    text_a,
                    text_b,
                ),
                get_row(
                    text_c,
                    text_d
                )
            )
        else:
            # 我也不知道为什么会出现>5个数字的情况
            return get_text("")

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

        for value in MineStatus_1W(list(self.values)):
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

        if possible_list:
            model.AddAllowedAssignments(var_list, possible_list).OnlyEnforceIf(s)
        else:
            model.Add(sum(var_list) == 0).OnlyEnforceIf(s)
