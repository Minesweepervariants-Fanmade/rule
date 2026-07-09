#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : 雾 (3140864122)
# @FileName: RL3.py
"""
[RL3] 误差线索：
如果一个数字的四格（上下左右）存在奇数个雷，那么它的线索数是周围八格总雷数的+1或者-1（不能是-1,9）；
如果是偶数个雷，那么它是周围八格的总雷数。
"""

from functools import cache
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def four_neighbors() -> PositionSet:
    """返回上下左右四个方向的位置（相对于原点(0,0)）"""
    return PositionSet([Position(0, -1), Position(0, 1), Position(-1, 0), Position(1, 0)])


@cache
def eight_neighbors() -> PositionSet:
    """返回周围八格的位置（相对于原点(0,0)）"""
    return PositionSet(Position(0, 0).neighbors(2))


class RuleRL3(AbstractClueRule):
    id = "RL3"
    name = "Error Clue"
    name.zh_CN = "误差线索"  # type: ignore[attr-defined]
    doc = (
        "If the four adjacent cells (up, down, left, right) contain an odd number of mines, "
        "the clue value is the total number of mines in the surrounding eight cells plus or minus 1 "
        "(but cannot be -1 or 9). If even, the clue value is the total number of mines in the surrounding eight cells."
    )
    doc.zh_CN = (
        "如果一个数字的四格（上下左右）存在奇数个雷，那么它的线索数是周围八格总雷数的+1或者-1（不能是-1,9）；"
        "如果是偶数个雷，那么它是周围八格的总雷数。"
    )  # type: ignore[attr-defined]
    tags = ["Creative", "Local", "Number Clue", "Light"]
    creation_time = "2026-06-24"
    author = ("雾", "3140864122")

    def fill(self, board: Board) -> Board:
        """填充所有未定义格为RL3线索"""
        for pos, _ in board("N", special='raw'):
            # 获取四格位置（上下左右）
            four_pos = four_neighbors().deviation(pos)
            four_pos.to_board(pos.board_key)
            # 获取八格位置（周围八格）
            eight_pos = eight_neighbors().deviation(pos)
            eight_pos.to_board(pos.board_key)

            # 计算四格雷数
            four_types = board.batch(positions=four_pos, mode="type", special='raw')
            four_mine_count = four_types.count("F")

            # 计算八格雷数
            eight_types = board.batch(positions=eight_pos, mode="type", special='raw')
            eight_mine_count = eight_types.count("F")

            # 根据四格奇偶性决定线索值
            if four_mine_count % 2 == 0:
                # 偶数：线索值 = 八格雷数
                clue_value = eight_mine_count
            else:
                # 奇数：线索值 = 八格雷数 ± 1，排除 -1 和 9
                candidates = [eight_mine_count - 1, eight_mine_count + 1]
                # 过滤掉 -1 和 9
                valid_candidates = [v for v in candidates if 0 <= v <= 8]
                if valid_candidates:
                    clue_value = valid_candidates[0]
                else:
                    # 理论上不会发生
                    clue_value = eight_mine_count

            board.set_value(pos, ValueRL3(pos, clue_value))
        return board


class ValueRL3(AbstractClueValue):
    id = RuleRL3.id

    def __init__(self, pos: Position, clue_value: int = 0, four_even: bool = True):
        """
        :param pos: 线索所在位置
        :param clue_value: 线索值（0-8）
        :param four_even: 四格雷数是否为偶数
        """
        super().__init__(pos, b'')
        self.clue_value = clue_value
        self.four_even = four_even

        # 存储四格位置
        four_pos = four_neighbors().deviation(pos)
        four_pos.to_board(pos.board_key)
        self.four_neighbor = four_pos

        # 存储八格位置
        eight_pos = eight_neighbors().deviation(pos)
        eight_pos.to_board(pos.board_key)
        self.eight_neighbor = eight_pos

        self.value = SingleIntValue(self.clue_value)

    def __repr__(self) -> str:
        return str(self.clue_value)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractClueValue':
        _data = deep_unwrap(data)
        if not isinstance(_data, dict):
            raise TypeError("Expected dict")
        if "type" not in _data or "data" not in _data:
            raise ValueError("Missing type or data")
        clue_value = _data["data"]
        if not isinstance(clue_value, int):
            raise ValueError("data must be int")
        four_even = _data.get("four_even", True)
        return cls(pos, clue_value=clue_value, four_even=four_even)

    def json(self) -> dict:
        """序列化为JSON，保存four_even信息"""
        # 获取标准模板JSON并转换为普通字典
        data = dict(self.value.json())
        data["four_even"] = self.four_even
        return data

    def high_light(self, board: Board) -> list[Position]:
        """高亮显示周围八格"""
        return list(self.eight_neighbor)

    def invalid(self, board: Board) -> bool:
        """如果所有八格都已翻开（非'N'）则线索可验证"""
        types = board.batch(positions=self.eight_neighbor, mode="type", special='raw')
        return types.count("N") == 0

    def create_constraints(self, board: Board, switch: Switch):
        """创建CP-SAT约束"""
        model = board.get_model()
        logger = get_logger()

        # 获取四格变量（上下左右）
        four_vars: list[IntVar] = []
        for pos in self.four_neighbor:
            var = board.get_variable(pos)
            if var is not None:
                four_vars.append(var)

        # 获取八格变量（周围八格）
        eight_vars: list[IntVar] = []
        for pos in self.eight_neighbor:
            var = board.get_variable(pos)
            if var is not None:
                eight_vars.append(var)

        if not eight_vars:
            return

        s = switch.get(model, self.pos)

        # 计算八格雷数之和
        eight_sum = sum(eight_vars)

        # 如果没有四格变量，只要求 eight_sum == clue_value
        if not four_vars:
            model.Add(eight_sum == self.clue_value).OnlyEnforceIf(s)
            logger.trace(f"[RL3] Value[{self.pos}: {self.clue_value}] no four vars, eight_sum == {self.clue_value}")
            return

        # 计算四格雷数之和
        four_sum = sum(four_vars)

        # 奇偶性变量: 0=偶数, 1=奇数
        parity = model.NewIntVar(0, 1, f"rl3_parity_{id(self)}")
        # four_sum = 2*k + parity
        max_k = len(four_vars) // 2 + 1
        k = model.NewIntVar(0, max_k, f"rl3_k_{id(self)}")
        model.Add(four_sum == 2 * k + parity)

        # 创建 even/odd 布尔变量，用于 OnlyEnforceIf
        even = model.NewBoolVar(f"rl3_even_{id(self)}")
        odd = model.NewBoolVar(f"rl3_odd_{id(self)}")
        model.Add(even + odd == 1)
        model.Add(parity == 0).OnlyEnforceIf(even)
        model.Add(parity == 1).OnlyEnforceIf(odd)

        # 偶数情况：eight_sum == clue_value
        model.Add(eight_sum == self.clue_value).OnlyEnforceIf([s, even])

        # 奇数情况：eight_sum == clue_value ± 1（在0-8范围内）
        possible_values = [self.clue_value - 1, self.clue_value + 1]
        possible_values = [v for v in possible_values if 0 <= v <= 8]

        if possible_values:
            if len(possible_values) == 1:
                model.Add(eight_sum == possible_values[0]).OnlyEnforceIf([s, odd])
                logger.trace(
                    f"[RL3] Value[{self.pos}: {self.clue_value}] odd: eight_sum == {possible_values[0]}"
                )
            else:
                # 两个可能值
                b1 = model.NewBoolVar(f"rl3_choice_{id(self)}_1")
                b2 = model.NewBoolVar(f"rl3_choice_{id(self)}_2")
                model.Add(eight_sum == possible_values[0]).OnlyEnforceIf([s, odd, b1])
                model.Add(eight_sum == possible_values[1]).OnlyEnforceIf([s, odd, b2])
                # 当odd为真时，必须恰好选择一个
                model.Add(b1 + b2 == 1).OnlyEnforceIf([s, odd])
                # 当even为真时，两个都不选（保持一致性）
                model.Add(b1 + b2 == 0).OnlyEnforceIf([s, even])
                logger.trace(
                    f"[RL3] Value[{self.pos}: {self.clue_value}] odd: eight_sum in {possible_values}"
                )
        else:
            # 没有有效奇数值，禁止奇数情况
            model.Add(odd == 0).OnlyEnforceIf(s)
            logger.warning(f"[RL3] No valid odd choices for clue {self.clue_value} at {self.pos}")
