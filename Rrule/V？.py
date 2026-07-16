#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/17
# @Author  : DeepSeek Agent
# @FileName: V？.py
"""
[V?]经典扫雷？：数字线索表示周围八格中的雷或非雷数。即数字可能是雷数也可能是安全格数，玩家需要自行推理。
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

from ....utils.tool import get_logger, get_random
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def neighbors() -> PositionSet:
    return PositionSet(Position(0, 0).neighbors(2))


class RuleV(AbstractClueRule):
    id = "V?"
    name = "Vanilla?"
    name.zh_CN = "经典扫雷？"
    doc = "Each number indicates either the mine count or safe cell count in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格中雷或非雷的数量，玩家需要自行推理是雷数还是安全格数"
    tags = ["Variant", "Local", "Number Clue"]
    creation_time = "2026-07-16"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            neis = neighbors().deviation(pos)
            neis.to_board(pos.board_key)
            value_list: list[str] = board.batch(positions=neis, mode="type")
            mine_count = value_list.count("F")
            total = len(neis)
            # 随机选雷数或非雷数作为显示值
            count = get_random().choice([mine_count, total - mine_count])
            board.set_value(pos, ValueV(pos, count=count))
        return board


class ValueV(AbstractClueValue):
    id = RuleV.id

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

    def weaker_times(self) -> int:
        return 1

    def weaker(self, board: 'Board') -> 'AbstractValue':
        return VALUE_QUESS

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
        total = len([p for p in self.neighbor if board.in_bounds(p)])
        if f_num == self.count or f_num == total - self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count or f_num + n_num == total - self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 周围雷数等于count或总邻格数-count"""
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)
        if neighbor_vars:
            total = len(neighbor_vars)
            is_mine_count = model.NewBoolVar(f'vmc_{self.pos}')
            model.add(sum(neighbor_vars) == self.count).OnlyEnforceIf([is_mine_count, s])
            model.add(sum(neighbor_vars) == total - self.count).OnlyEnforceIf([is_mine_count.Not(), s])
            logger.trace(f"[V?] Value[{self.pos}: {self.count}] add: sum=={self.count} or sum=={total-self.count}")
