#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : NT (2201963934)
# @FileName: SG_.py
"""
[SG'] 井字棋线索：线索表示周围3x3横竖斜向三格相同的次数

该规则为右线规则，线索值表示在周围3x3区域内，所有8条线（3行、3列、2条对角线）
上三个格子全部为雷或全部为非雷的次数。线索格本身固定为非雷，因此全雷的线不可能，
实际只统计全非雷的线数。
"""
from functools import cache
from typing import List
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template


@cache
def direction_sets() -> List[PositionSet]:
    """
    返回所有8条井字棋线在3x3区域内的位置集合（相对中心）。
    每条线包含三个相对位置。
    """
    # 行：上、中、下
    row_top = PositionSet([Position(-1, -1), Position(-1, 0), Position(-1, 1)])
    row_mid = PositionSet([Position(0, -1), Position(0, 0), Position(0, 1)])
    row_bot = PositionSet([Position(1, -1), Position(1, 0), Position(1, 1)])
    # 列：左、中、右
    col_left = PositionSet([Position(-1, -1), Position(0, -1), Position(1, -1)])
    col_mid = PositionSet([Position(-1, 0), Position(0, 0), Position(1, 0)])
    col_right = PositionSet([Position(-1, 1), Position(0, 1), Position(1, 1)])
    # 对角线
    diag_main = PositionSet([Position(-1, -1), Position(0, 0), Position(1, 1)])
    diag_anti = PositionSet([Position(-1, 1), Position(0, 0), Position(1, -1)])
    return [row_top, row_mid, row_bot, col_left, col_mid, col_right, diag_main, diag_anti]


class RuleSGPrime(AbstractClueRule):
    id = "SG'"
    name = "Tic-Tac-Toe Clue"
    name.zh_CN = "井字棋线索"
    doc = "Clue indicates the number of horizontal, vertical, and diagonal lines of three in the surrounding 3x3 area that are all mines or all non-mines"
    doc.zh_CN = "线索表示周围3x3横竖斜向三格相同的次数"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Number Clue", "Variant"]
    creation_time = "2026-07-09"

    def fill(self, board: 'Board') -> 'Board':
        """
        为所有未定义位置生成线索值。
        对于每条线，获取三个位置的实际类型（'F'为雷，其他为非雷），
        统计全非雷的线数（中心非雷，全雷不可能）。
        """
        for pos, _ in board("N", special='raw'):
            count = 0
            for ds in direction_sets():
                # 获取三个绝对位置
                abs_positions = [p.deviation(pos) for p in ds]
                for p in abs_positions:
                    p.to_board(pos.board_key)
                # 检查是否所有位置都在板内
                if not all(board.in_bounds(p) for p in abs_positions):
                    continue
                # 获取三个位置的类型（'F'为雷，其他为非雷，包括'N'和'C'）
                types = board.batch(abs_positions, mode="type")
                if len(types) != 3:
                    continue
                # 统计雷的数量，将'N'视为非雷
                f_count = types.count('F')
                # 全非雷（即没有'F'）
                if f_count == 0:
                    count += 1
            board.set_value(pos, ValueSGPrime(pos, count=count))
        return board


class ValueSGPrime(AbstractClueValue):
    id = RuleSGPrime.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.value = SingleIntValue(self.count)
        # 存储8条线的位置集合（绝对位置）
        self.directions = []
        for ds in direction_sets():
            shifted = ds.deviation(pos)
            shifted.to_board(pos.board_key)
            self.directions.append(shifted)

    def __repr__(self) -> str:
        return str(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid value template")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Failed to parse count from JSON")
        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        all_pos = PositionSet()
        for d in self.directions:
            all_pos.update(d)
        return list(all_pos)

    def invalid(self, board: 'Board') -> bool:
        all_pos = PositionSet()
        for d in self.directions:
            all_pos.update(d)
        return board.batch(all_pos, mode="type", special='raw').count("N") == 0

    def deduce_cells(self, board: 'Board') -> bool:
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """
        创建CP-SAT约束：线索值等于8条线中全非雷的线数。
        对于每条线，三个位置都有变量，中心变量强制为0。
        """
        model = board.get_model()
        logger = get_logger()

        # 强制中心格变量为0（非雷）
        center_var = board.get_variable(self.pos)
        if center_var is not None:
            model.Add(center_var == 0)

        s = switch.get(model, self.pos)
        direction_vars: List[IntVar] = []

        for direction in self.directions:
            # 获取三个位置的变量
            vars_3 = []
            valid = True
            for p in direction:
                var = board.get_variable(p)
                if var is None:
                    valid = False
                    break
                vars_3.append(var)
            if not valid or len(vars_3) != 3:
                continue

            # 创建布尔变量表示该方向是否命中（全0）
            dir_var = model.NewBoolVar(f"SG'_dir_{self.pos}_{len(direction_vars)}")
            direction_vars.append(dir_var)

            # 辅助变量：z表示全0
            z = model.NewBoolVar(f"SG'_zero_{self.pos}_{len(direction_vars)}")
            # 因为中心强制为0，全雷不可能，所以只需检查全0
            model.Add(sum(vars_3) == 0).OnlyEnforceIf(z)
            model.Add(sum(vars_3) != 0).OnlyEnforceIf(z.Not())
            model.Add(dir_var == z)

        if direction_vars:
            # 约束：命中方向数等于线索值
            model.Add(sum(direction_vars) == self.count).OnlyEnforceIf(s)
            logger.trace(f"[SG'] {self.pos} count={self.count} dirs={direction_vars}")
        else:
            # 若无有效方向，强制线索值为0
            model.Add(self.count == 0).OnlyEnforceIf(s)
            logger.trace(f"[SG'] {self.pos} no valid directions, forced 0")
