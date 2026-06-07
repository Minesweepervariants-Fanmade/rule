#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
"""
[V'']雷绝对值: 每个数字标明周围八格内雷值之和之绝对值
"""
from minesweepervariants.immutable_dict import ImmutableDict
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position_set import PositionSet
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import Mapping, cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG
# from ...impl_obj import add_rule


def encode_int_7bit(n: int) -> bytes:
    return n.to_bytes((n.bit_length() + 7) // 8 or 1, byteorder='big')


def decode_bytes_7bit(data: bytes) -> int:
    return int.from_bytes(data, byteorder='big')

class RuleV(AbstractClueRule):
    id = "V''"
    name = "Absolute"
    name.zh_CN = "雷绝对值"
    doc = "Each number shows the absolute value of the sum of mine values in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格内雷值之和之绝对值"
    tags = ["Variant", "Local", "Number Clue", "Mine-Value"]
    creation_time = "2025-10-26"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "V'"

        class ValueV(AbstractClueValue):
            id = "V''"

            def __init__(self, pos: Position, count: int = 0, rule=self.rule):
                self.rule = rule
                self.pos = pos
                self.neighbor = self.pos.neighbors(2)
                self.value = SingleIntValue(count)

            def json(self):
                return ImmutableDict({
                        'rule': self.rule,
                        'value': self.value.json()
                    })

            @classmethod
            def from_json(cls, pos: Position, data: JSONObject):
                assert isinstance(data, Mapping)
                assert 'rule' in data and 'value' in data
                rule = data['rule']
                assert isinstance(rule, str)
                assert is_value_template((_value := data['value']))

                value = SingleIntValue.try_from(_value)
                assert value is not None

                return cls(pos=pos, count=value.value, rule=rule)


            def __repr__(self):
                return f"{self.value}"

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
                    ge = model.NewBoolVar('ge')
                    le = model.NewBoolVar('le')

                    model.Add(sum(neighbor_vars) == self.value.value).OnlyEnforceIf(ge)
                    model.Add(sum(neighbor_vars) == -self.value.value).OnlyEnforceIf(le)

                    model.AddBoolOr([ge, le]).OnlyEnforceIf(s)
                    get_logger().trace(f"[V''] Value[{self.pos}: {self.value.value}] add: {neighbor_vars} == ±{self.value.value}")

        self.ValueV = ValueV


    def fill(self, board: 'Board') -> 'Board':
        # 如果没有注册过特殊类型，则进行初始化
        if not board.has_type_special(self.rule):
            add_rule(board, self.rule, add=False)

        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            ps = PositionSet(pos.neighbors(2)).in_bounds(board.boundary())
            value = board.batch(ps, "type", special=self.rule)
            value = sum(v or 0 for v in value)
            board.set_value(pos, self.ValueV(pos, count=value, rule=self.rule))
        return board
