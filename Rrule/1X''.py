#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 19:14
# @Author  : Wu_RH
# @FileName: 1X'.py
"""
[1X'']双十字 (Double Cross)：线索表示距离为1和距离为2√2区域的总雷数
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


class Rule1Xp(AbstractClueRule):
    id = "1X''"
    aliases = ("X''",)
    name = "X''"
    name.zh_CN = "双十字"
    doc = "Clue shows the total mines in distance 1 and distance 2√2 regions"
    doc.zh_CN = "线索表示距离为1和距离为2√2区域的总雷数"
    tags = ["Local", "Number Clue", "Vanilla Variant", "Fun"]
    creation_time = "2025-08-07"
    author = ("波常未来", 81500378)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            value = len([_pos for _pos in pos.neighbors(1)+pos.neighbors(8, 8) if board.get_type(_pos) == "F"])
            board.set_value(pos, Value1X(pos, value))
            logger.debug(f"Set {pos} to 1X[{value}]")
        return board

class Value1X(AbstractClueValue):
    id = Rule1Xp.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos
        self.neighbor = pos.neighbors(1)+pos.neighbors(8, 8)

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
        return self.neighbor

    def deduce_cells(self, board: 'Board') -> bool:
        type_dict = {"N": [], "F": []}
        for pos in self.neighbor:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)
        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])
        if n_num == 0:
            return False
        if f_num == self.value.value:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.value.value:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch):
        """创建CP-SAT约束：周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.value.value).OnlyEnforceIf(s)
