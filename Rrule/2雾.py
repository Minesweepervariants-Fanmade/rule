#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[2雾] 雾的头像
作者: Indiebard (Alith) (2513946475)
最后编辑时间: 2026-08-04 22:10:05

规则语义:
- 右线规则(Rrule), 每个非雷格显示"雾"的头像 (🌫️)。
- 线索值为周围八格内的雷数 (与标准扫雷 V 规则相同)。
- fill 阶段为所有非雷格设置 Value2Fog 对象，存储周围雷数。
- create_constraints 阶段添加约束：周围八格雷数 == 存储值。
"""

from functools import cache
from ortools.sat.python.cp_model import IntVar
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def neighbors() -> PositionSet:
    return PositionSet(Position(0, 0).neighbors(2))


class Rule2Fog(AbstractClueRule):
    """[2雾] 规则：每个非雷格显示雾的头像，实际为周围八格雷数"""
    id = "2雾"
    name = "Fog"
    name.zh_CN = "雾的头像"
    doc = "Fill each non-mine cell with the avatar of Fog (QQ: 3140864122), value is the number of surrounding mines"
    doc.zh_CN = "在每个非雷格里填入雾的头像（QQ: 3140864122），数值为周围八格雷数"
    author = ("Indiebard (Alith)", 2513946475)
    tags = ["Creative", "Local", "Vanilla Variant", "Fun"]
    creation_time = "2026-08-04"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)

    def fill(self, board: 'Board') -> 'Board':
        """
        为所有非雷格设置 Value2Fog 对象，其值为周围八格雷数。
        """
        for pos, _ in board("N", special='raw'):
            neis = neighbors().deviation(pos)
            neis.to_board(pos.board_key)
            value_list: list[str] = board.batch(positions=neis, mode="type")
            count_val = value_list.count("F")
            board.set_value(pos, Value2Fog(pos, count=count_val))
        return board


class Value2Fog(AbstractClueValue):
    """[2雾] 线索值：显示雾的头像，实际为周围八格雷数"""
    id = Rule2Fog.id

    def __init__(self, pos: Position, count: int = 0, code: bytes = b'') -> None:
        super().__init__(pos, code)
        self.count = count
        neis = neighbors().deviation(pos)
        neis.to_board(pos.board_key)
        self.neighbor = neis
        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = _data
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, count=value.value)

    def __repr__(self) -> str:
        return "🌫️"

    def high_light(self, board: 'Board') -> list['Position']:
        return list(self.neighbor)

    def invalid(self, board: 'Board') -> bool:
        return board.batch(self.neighbor, mode="type", special='raw').count("N") == 0

    def deduce_cells(self, board: 'Board') -> bool:
        type_dict: dict[str, list[Position]] = {"N": [], "F": []}
        for pos in self.neighbor:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)
        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])
        if n_num == 0:
            return False
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def weaker(self, board: Board) -> AbstractValue:
        return self

    def weaker_times(self) -> int:
        return 0

    def tag(self, board: 'Board') -> bytes:
        return b""

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()
        logger = get_logger()

        # 收集周围格子的布尔变量
        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        s = switch.get(model, self.pos)
        if neighbor_vars:
            model.add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
            logger.trace(f"[2雾] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
