#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/11 15:22
# @Author  : 雾 (3140864122)
# @FileName: UC.py
"""
[UC] UnCross: 题板上不允许出现一颗雷的上下左右均为雷的构造（边界外视为0）
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
def cross_neighbors() -> PositionSet:
    """返回上下左右四个方向的位置（不包括自身）"""
    return PositionSet(Position(0, 0).neighbors(1, 1))


class RuleUC(AbstractClueRule):
    id = "UC"
    name = "UnCross"
    name.zh_CN = "无十字雷"  # type: ignore[attr-defined]
    doc = "No cell can be a mine if all four orthogonal neighbors are mines (edges count as 0)"
    doc.zh_CN = "题板上不允许出现一颗雷的上下左右均为雷的构造（边界外视为0）"  # type: ignore[attr-defined]
    tags = ["Variant", "Local", "Number Clue", "Construction"]
    creation_time = "2026-07-11"
    author = ("雾", 3140864122)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            neis = cross_neighbors().deviation(pos)
            neis.to_board(pos.board_key)
            value_list: list[str] = board.batch(positions=neis, mode="type")
            count_val = value_list.count("F")
            board.set_value(pos, ValueUC(pos, count=count_val))
        return board

    def create_constraints(self, board: 'Board', switch: Switch):
        """全局约束：不允许一颗雷的上下左右均为雷"""
        model = board.get_model()
        logger = get_logger()
        # 遍历所有题板
        for board_key in board.get_board_keys():
            # 获取题板尺寸
            size = board.get_config(board_key, "size")
            if size is None:
                continue
            cols = size.cols
            rows = size.rows
            # 遍历所有位置（不仅仅是 N 类型），确保约束覆盖所有格子
            for r in range(rows):
                for c in range(cols):
                    pos = Position(c, r, board_key)
                    # 获取当前格子的变量
                    var = board.get_variable(pos)
                    if var is None:
                        continue
                    # 收集上下左右邻居的变量（仅限在边界内的）
                    neighbor_vars = []
                    for neighbor in cross_neighbors().deviation(pos):
                        neighbor.to_board(pos.board_key)
                        if board.in_bounds(neighbor):
                            nv = board.get_variable(neighbor)
                            if nv is not None:
                                neighbor_vars.append(nv)
                    # 约束：如果当前位置是雷，则邻居雷数不超过3（即不能全为雷）
                    # 等价于：var + sum(neighbor_vars) <= 4
                    if neighbor_vars:
                        model.add(var + sum(neighbor_vars) <= 4)
                        logger.trace(f"[UC] Global constraint at {pos}: {var} + sum({neighbor_vars}) <= 4")
                    else:
                        # 没有邻居（单格题板），孤立雷允许
                        pass


class ValueUC(AbstractClueValue):
    id = RuleUC.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        neis = cross_neighbors().deviation(pos)
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
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 上下左右四个方向雷的数量等于count"""
        model = board.get_model()
        logger = get_logger()

        neighbor_vars: list[IntVar] = []
        for neighbor in self.neighbor:
            if (var := board.get_variable(neighbor)) is not None:
                neighbor_vars.append(var)

        s = switch.get(model, self.pos)

        # 约束: 上下左右雷数量等于count
        if neighbor_vars:
            model.add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
            logger.trace(f"[UC] Value[{self.pos}: {self.count}] add: {neighbor_vars} == {self.count}")
