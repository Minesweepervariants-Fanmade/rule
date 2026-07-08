#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : DeepSeek Agent
# @FileName: DM.py
"""
[DM] Double Mine: Each mine counts as 2, clue number indicates total weight of neighboring mines.
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


class RuleDM(AbstractClueRule):
    id = "DM"
    name = "Double Mine"
    name.zh_CN = "多雷（双倍）"  # type: ignore[attr-defined]
    doc = "Each mine counts as 2, clue number indicates total weight (2 * number of adjacent mines)"
    doc.zh_CN = "每个雷计为2，线索数字表示周围雷的总权重（2倍雷数）"  # type: ignore[attr-defined]
    tags = ["Multi-Mine", "Weighted"]
    creation_time = "2026-07-09"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            neis = neighbors().deviation(pos)
            neis.to_board(pos.board_key)
            type_list = board.batch(positions=neis, mode="type")
            mine_count = type_list.count("F")
            # 每个雷计为2
            clue_value = mine_count * 2
            board.set_value(pos, ValueDM(pos, count=clue_value))
        return board


class ValueDM(AbstractClueValue):
    id = RuleDM.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        neis = neighbors().deviation(pos)
        neis.to_board(pos.board_key)
        self.neighbor = neis

        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        template_data = _data
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError()

        return cls(pos, count=value.value)

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
        # 已知雷的总权重为 2*f_num，未知雷的总权重为 2*未知雷数
        # 如果已知雷权重已经等于count，则所有未知格不是雷
        if f_num * 2 == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        # 如果所有未知格都必须是雷（即总雷数权重等于count），则全部标雷
        if (f_num + n_num) * 2 == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 周围雷的总权重（2倍雷数）等于count"""
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)
        if neighbor_vars:
            # 约束：2 * sum(neighbor_vars) == self.count
            model.add(sum(neighbor_vars) * 2 == self.count).OnlyEnforceIf(s)
            logger.trace(f"[DM] Value[{self.pos}: {self.count}] add: 2*sum({neighbor_vars}) == {self.count}")
