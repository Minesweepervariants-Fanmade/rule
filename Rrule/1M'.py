#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 18:09
# @Author  : Wu_RH
# @FileName: 1M.py
"""
[1M']多雷': 每个线索的多雷位置相对于线索固定 且位置全盘共享(总雷数不受限制)
"""

from minesweepervariants.board import Position, Board, JSONObject, Size
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_random
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS

BOARD_NAME = "1M'"


class Rule1M(AbstractClueRule):
    id = "1M'"
    aliases = ("M'",)
    name = "Multi-Mine'"
    name.zh_CN = "多雷'"
    doc = "Each clue's multi-mine positions are fixed relative to the clue and shared across the board"
    doc.zh_CN = "每个线索的多雷位置相对于线索固定 且位置全盘共享（不影响总雷数）"

    tags = ["Variant", "Local", "Number Clue", "Aux Board", "Mine-Position"]
    creation_time = "2025-08-13"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        board.generate_board(BOARD_NAME, Size(3, 3))
        if data is None:
            self.value = 4
        else:
            self.value = data

    def fill(self, board: 'Board'):
        self.init_clear(board)
        def apply_offsets(_pos: Position):
            nonlocal offsets
            result = []
            for dpos in offsets:
                result.append(_pos.deviation(dpos))
            return result
        random = get_random()
        pos = board.get_pos(1, 1, BOARD_NAME)

        if self.value is None:
            board[pos] = Value2I_7(pos, 4)
        elif self.value == "":
            board[pos] = Value2I_7(pos, 9)
        else:
            board[pos] = Value2I_7(pos, int(self.value))

        pos_list = [pos for pos, _ in board(key=BOARD_NAME)]

        if self.value == "":
            pos_list = random.sample(pos_list, int(random.random() * 9))
        else:
            pos_list = random.sample(pos_list, int(self.value))
        offsets = []
        for pos in pos_list:
            board[pos] = VALUE_CIRCLE
            offsets.append(pos.up().left())
        for pos, _ in board("N", key=BOARD_NAME):
            board[pos] = VALUE_CROSS

        for pos, _ in board("N"):
            positions = pos.neighbors(2)
            offset_poses = apply_offsets(pos)
            value = board.batch(positions, mode="type").count("F")
            value += board.batch(offset_poses, mode="type").count("F")
            obj = Value1M(pos, value)
            board.set_value(pos, obj)
        return board

    def init_clear(self, board: 'Board'):
        for pos, obj in board(mode="object", key=BOARD_NAME):
            if isinstance(obj, Value2I_7):
                continue
            board[pos] = None


class Value1M(AbstractClueValue):
    id = Rule1M.id

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
        positions = self.pos.neighbors(2)
        neighbors = []
        for pos2, obj in board(key=BOARD_NAME, mode="obj"):
            if isinstance(obj, Value2I_7):
                continue
            neighbors.append([self.pos.deviation(pos2).up().left(), pos2])
        for pos, pos2 in neighbors:
            if board.get_type(pos) == "F":
                positions.append(pos2)
        return positions

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        var_list = board.batch(self.pos.neighbors(2), mode="variable", drop_none=True)

        # 初始化对照表
        neighbors = []
        for pos2, obj in board(key=BOARD_NAME, mode="obj"):
            if isinstance(obj, Value2I_7):
                continue
            # 题板上的位置和共享的偏移位置
            _positions = [self.pos.deviation(pos2).up().left(), pos2]
            # 第一个为题板对应的变量 第二个为偏移的变量
            neighbors.append(board.batch(_positions, mode="variable"))

        # 初始化和值
        for var_to_sum, cond in neighbors:
            if var_to_sum is None or cond is None:
                continue
            # 初始化临时变量
            tmp = model.NewBoolVar(f"included_if_{self.pos}_{var_to_sum}")
            # 如果偏移变量为真 那么tmp为题板的值
            model.Add(tmp == var_to_sum).OnlyEnforceIf([cond, s])
            # 如果偏移变量为假 那么tmp为0
            model.Add(tmp == 0).OnlyEnforceIf([cond.Not(), s])
            var_list.append(tmp)

        model.Add(sum(var_list) == self.value.value).OnlyEnforceIf(s)


class Value2I_7(AbstractClueValue):
    id = Rule1M.id + "_n"

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

    def create_constraints(self, board: 'Board', switch):
        if self.value.value > 8:
            return
        model = board.get_model()
        s = switch.get(model, self)
        model.Add(sum(board.batch(self.pos.neighbors(2), mode="variable")) == self.value.value).OnlyEnforceIf(s)
