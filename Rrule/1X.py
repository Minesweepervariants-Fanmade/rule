#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 18:26
# @Author  : Wu_RH
# @FileName: 1X.py
"""
[1X] 十字 (Cross)：线索表示半径为 2 的十字范围内的雷数
"""
from typing import Self, cast

from minesweepervariants.json_object import deep_unwrap
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.utils.value_template import SingleIntValue, Template, is_value_template
from minesweepervariants.board import JSONObject, Board, Position, ImmutableDict

from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

from typing import TypedDict


class IntValueTemplate(TypedDict):
    _SingleIntValue: bool
    data: int
    bool_list: list[bool]


class SingleIntValue1X(SingleIntValue):
    def __init__(self, bool_list: list[bool], value: int, is_mine: bool = False):
        super().__init__(value, is_mine=is_mine)
        self.value = value
        self.bool_list = bool_list

    def _template(self) -> Template:
        result = super()._template()
        result["_SingleIntValue"] = True
        result["data"] = self.value
        result["bool_list"] = self.bool_list

        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        if not data.get("_SingleIntValue", False):
            return None

        # 告诉类型检查器 data 实际符合 IntValueTemplate 结构
        concrete = cast(IntValueTemplate, data)
        value: int = concrete["data"]
        bool_list: list[bool] = concrete["bool_list"]

        match value:
            case int():
                return cls(bool_list=bool_list, value=value)
            case _:
                return None


def get_neighbors(pos, bool_list: list[bool]) -> list[Position]:
    neighbor = []
    for n, b in enumerate(bool_list[::-1]):
        if not b:
            continue
        neighbor.extend(pos.neighbors(n + 1, n + 1))
    return neighbor


class Rule1X(AbstractClueRule):
    id = "1X"
    aliases = ("X",)
    name = "Cross"
    name.zh_CN = "十字"
    doc = "Clue indicates the number of mines in a cross pattern with radius 2"
    doc.zh_CN = "线索表示半径为 2 的十字范围内的雷数"
    tags = ["Original", "Local", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        if data is None:
            self.neibor_bool = []
            return
        datas = data.split(";")
        nei_values: list[int] = []
        for nei_value in datas:
            if ":" in nei_value:
                nei_values.extend(tuple([
                    i for i in range(
                        int(nei_value.split(":")[0]),
                        int(nei_value.split(":")[1])+1
                    )
                ]))
            else:
                nei_values.append(int(nei_value))
        if not nei_values:
            return
        max_value = max(nei_values)
        self.neibor_bool = [False for _ in range(max_value)]
        for i in nei_values:
            if i == 0:
                continue
            self.neibor_bool[max_value-i] = True

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            value = len([_pos for _pos in get_neighbors(pos, self.neibor_bool) if board.get_type(_pos) == "F"])
            obj = Value1X(pos, self.neibor_bool, value)
            board.set_value(pos, obj)
        return board


class Value1X(AbstractClueValue):
    id = Rule1X.id

    def __init__(self, pos: Position, bool_list: list[bool], value: int, *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.value = SingleIntValue1X(bool_list, value)
        self.bool_list = bool_list
        self.neighbor = get_neighbors(pos, bool_list)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue1X.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.bool_list, value.value)

    def __repr__(self):
        return f"{self.value}"

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
        if f_num == self.value:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.value:
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
            model.Add(sum(neighbor_vars) == self.value).OnlyEnforceIf(s)
