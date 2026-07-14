#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
"""
[V']雷值：每个数字标明周围八格内雷值之和。
"""
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast, Self
from minesweepervariants.utils.value_template import Template, SingleIntValue, is_value_template
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger


class DataVp(SingleIntValue):
    def __init__(self, value: int, rule: str):
        super().__init__(value, False)
        self.rule: str = rule

    def _template(self) -> Template:
        result = super()._template()
        result["_SingleIntValue"] = True
        result["data"] = self.value
        result["rule"] = self.rule
        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        if not data.get("_SingleIntValue", False):
            return None

        value = cast(int, data["data"])
        rule = cast(str, data["rule"])

        return cls(value, rule)


class RuleV(AbstractClueRule):
    id = "V'"
    name = "Value"
    name.zh_CN = "雷值"
    doc = "Each number indicates the sum of mine values in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格内雷值之和"
    tags = ["Variant", "Local", "Number Clue", "Mine-Value"]
    creation_time = "2025-10-26"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "V'"

    def fill(self, board: 'Board') -> 'Board':
        # 如果没有注册过特殊类型，则进行初始化
        logger = get_logger()
        if not board.has_type_special(self.rule):
            logger.error(f"未找到{self.rule}的命名域")
            raise ValueError(f"未在命名空间中找到[{self.rule}]")
        for pos, _ in board("N", special='raw'):
            value = board.batch(pos.neighbors(2), "type", special=self.rule)
            value = sum(v or 0 for v in value)
            board.set_value(pos, ValueV(pos, count=value, rule=self.rule))
        return board


class ValueV(AbstractClueValue):
    id = RuleV.id

    def __init__(self, pos: Position, count: int = 0, rule: str = "raw", *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.rule = rule
        self.count = count
        self.pos = pos
        self.neighbor = self.pos.neighbors(2)
        self.value: DataVp = DataVp(count, rule)

    @classmethod
    def from_json(cls, pos: Position, data):
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        value_obj = DataVp.try_from(template_data)
        if value_obj is None:
            raise ValueError("value is empty")
        return cls(pos, value_obj.value, value_obj.rule)

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self.pos)

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor, special=self.rule)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
            get_logger().trace(f"[V'] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")

