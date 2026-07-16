#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/17
# @Author  : DeepSeek Agent
# @FileName: V？.py
"""
[V?]经典扫雷？：数字线索表示周围八格中的雷或非雷数。两个数字分别表示雷数和安全格数，但哪个是哪个不确定。
"""
from functools import cache
from ortools.sat.python.cp_model import IntVar
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.value_template import is_value_template, Template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger, get_random
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG
from ....utils.image_template import get_text, get_row
from ....utils.web_template import MultiNumber
from typing import cast

MISSING_VALUE = 250


@cache
def neighbors() -> PositionSet:
    return PositionSet(Position(0, 0).neighbors(2))


class RuleV(AbstractClueRule):
    id = "V?"
    name = "Vanilla?"
    name.zh_CN = "经典扫雷？"
    doc = "Two numbers indicate the mine count and safe cell count in the surrounding eight cells, but which is which is unknown"
    doc.zh_CN = "两个数字分别表示周围八格中的雷数和非雷数，但哪个是哪个不确定"
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
            board.set_value(pos, ValueV(pos, [mine_count, total - mine_count]))
        return board


class ValueV(AbstractClueValue):
    id = RuleV.id

    def __init__(self, pos: Position, values: list[int] | None = None, code: bytes | None = None):
        super().__init__(pos, code if code else b'')
        if code is not None:
            self.values: list[int] = list(code)
        else:
            self.values = values if values is not None else [MISSING_VALUE, MISSING_VALUE]
        neis = neighbors().deviation(pos)
        neis.to_board(pos.board_key)
        self.neighbor = neis

    def __repr__(self):
        return "/".join([str(v) if v != MISSING_VALUE else "?" for v in self.values])

    def compose(self, board) -> dict:
        a, b = self.values
        return get_row(
            get_text(str(a) if a != MISSING_VALUE else "?"),
            get_text(str(b) if b != MISSING_VALUE else "?"),
            spacing=0
        )

    def web_component(self, board) -> dict:
        a, b = self.values
        return MultiNumber([
            str(a) if a != MISSING_VALUE else "?",
            "",
            str(b) if b != MISSING_VALUE else "?",
            ""
        ])

    @classmethod
    def type(cls) -> bytes:
        return RuleV.id.encode("ascii")

    def code(self) -> bytes:
        return bytes(self.values)

    def high_light(self, board: 'Board') -> list['Position']:
        return list(self.neighbor)

    def invalid(self, board: 'Board') -> bool:
        return board.batch(self.neighbor, mode="type", special='raw').count("N") == 0

    def weaker_times(self) -> int:
        return sum(1 for v in self.values if v != MISSING_VALUE)

    def weaker(self, board: 'Board') -> 'AbstractValue':
        if self.weaker_times() == 1:
            return VALUE_QUESS
        valid_idx = [i for i, v in enumerate(self.values) if v != MISSING_VALUE]
        new_values = self.values[:]
        new_values[get_random().choice(valid_idx)] = MISSING_VALUE
        return ValueV(self.pos, new_values)

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
        a, b = self.values
        total = len([p for p in self.neighbor if board.in_bounds(p)])
        if a == MISSING_VALUE and b == MISSING_VALUE:
            return False
        if a == MISSING_VALUE:
            valid_counts = {b, total - b}
        elif b == MISSING_VALUE:
            valid_counts = {a, total - a}
        else:
            valid_counts = {a, b, total - a, total - b}
        if f_num in valid_counts:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num in valid_counts:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 周围雷数等于两个值之一"""
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)
        if neighbor_vars:
            a, b = self.values
            if a != MISSING_VALUE and b != MISSING_VALUE:
                is_a = model.NewBoolVar(f'vma_{self.pos}')
                model.add(sum(neighbor_vars) == a).OnlyEnforceIf([is_a, s])
                model.add(sum(neighbor_vars) == b).OnlyEnforceIf([is_a.Not(), s])
            elif a != MISSING_VALUE:
                model.add(sum(neighbor_vars) == a).OnlyEnforceIf(s)
            elif b != MISSING_VALUE:
                model.add(sum(neighbor_vars) == b).OnlyEnforceIf(s)
