#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/03 05:26
# @Author  : Wu_RH
# @FileName: V.py
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

from typing import Any, cast, List

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def get_nei(pos : Position, board: Board):
    directions = [
        (1, 1), (1, 0), (1, -1),
        (0, 1),         (0, -1),
        (-1, 1), (-1, 0), (-1, -1)
    ]

    neighbors = []
    for dr, dc in directions:
        nr = (pos.row + dr) % (board.boundary(pos.board_key).row + 1)
        nc = (pos.col + dc) % (board.boundary(pos.board_key).col + 1)
        neighbors.append(board.get_pos(nr, nc, pos.board_key))

    return neighbors

class RuleURBV(AbstractClueRule):
    id = "URB-V"
    name = "Torus Vanilla"
    name.zh_CN = "环面扫雷"  # type: ignore[attr-defined]
    doc = "Each number indicates the number of mines in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格内雷的数量。（题板于边界循环）"  # type: ignore[attr-defined]
    tags = ["Local", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            value_list = cast(List[str], board.batch(get_nei(pos, board), "type"))
            count_val = value_list.count("F")
            board.set_value(pos, ValueURBV(pos, count=count_val))
        return board


class ValueURBV(AbstractClueValue):
    id = "URBV"
    def __init__(self, pos: Position, count: int = 0, code: bytes | None = None):
        # AbstractValue expects bytes for `code`; normalize None -> b'' when delegating
        super().__init__(pos, code or b'')
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count

    def __repr__(self):
        return f"{self.count}"

    def high_light(self, board: 'Board') -> list['Position']:
        return get_nei(self.pos, board)

    @classmethod
    def type(cls) -> bytes:
        return b'URB-V'

    def code(self) -> bytes:
        return bytes([self.count])

    def invalid(self, board: 'Board') -> bool:
        return cast(List[str], board.batch(get_nei(self.pos, board), mode="type", special='raw')).count("N") == 0

    def deduce_cells(self, board: 'Board') -> bool:
        type_dict: dict[str, list[Position]] = {"N": [], "F": []}
        for pos in get_nei(self.pos, board):
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

    def create_constraints(self, board: 'Board', switch: Any):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = cast(Any, board.get_model())
        logger = get_logger()

        # 收集周围格子的布尔变量
        neighbor_vars: list[Any] = []
        for neighbor in get_nei(self.pos, board):  # 8方向相邻格子
            if not board.in_bounds(neighbor):
                continue
            var = board.get_variable(neighbor)
            neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        s = cast(Any, switch).get(model, self.pos)
        if neighbor_vars:
            # model and neighbor variables are dynamically typed (ortools objects)
            model.Add(cast(Any, sum(neighbor_vars)) == self.count).OnlyEnforceIf(s)
            cast(Any, logger).trace(f"[V] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
