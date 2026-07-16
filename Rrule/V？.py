#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/17
# @Author  : DeepSeek Agent
# @FileName: V？.py
"""
[V?]经典扫雷？：数字线索取周围八格中雷数和安全格数中较小的那个。玩家需要推理数字代表的是雷数还是安全格数。
"""
from functools import cache
from ortools.sat.python.cp_model import IntVar
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def neighbors() -> PositionSet:
    return PositionSet(Position(0, 0).neighbors(2))


class RuleV(AbstractClueRule):
    id = "V?"
    name = "Vanilla?"
    name.zh_CN = "经典扫雷？"
    doc = "The clue is the smaller of the mine count and safe cell count among the 8 neighbors; the player must deduce which it represents"
    doc.zh_CN = "线索取周围八格中雷数和安全格数中较小的值，玩家需要推理这个数代表的是雷数还是安全格数"
    tags = ["Variant", "Local", "Number Clue"]
    creation_time = "2026-07-16"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            neis = neighbors().deviation(pos)
            neis.to_board(pos.board_key)
            value_list: list[str] = board.batch(positions=neis, mode="type")
            mine_count = value_list.count("F")
            safe_count = value_list.count("N") + value_list.count("C")
            count = min(mine_count, safe_count)
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
    def from_json(cls, pos: 'Position', data) -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError()
        value = SingleIntValue.try_from(_data)
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
        c = self.count
        # count = min(mines, non-mines)
        # 实际雷数可能是 c 或 total - c
        if f_num == c or f_num == total - c:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == c or f_num + n_num == total - c:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)
        if neighbor_vars:
            total = len(neighbor_vars)
            c = self.count
            if c == total - c:
                model.add(sum(neighbor_vars) == c).OnlyEnforceIf(s)
            else:
                is_mine = model.NewBoolVar(f'vm_{self.pos}')
                model.add(sum(neighbor_vars) == c).OnlyEnforceIf([is_mine, s])
                model.add(sum(neighbor_vars) == total - c).OnlyEnforceIf([is_mine.Not(), s])
