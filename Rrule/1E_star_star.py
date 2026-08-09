#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1E**] 视野幂：线索值表示竖直视野的水平视野次方（视野包含自身）。
例如：竖直视野为 3，水平视野为 2，则线索值为 3^2 = 9。
"""

from typing import List, Callable, Optional, cast

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template
from .eyesight import eyesight_var


class Rule1EStarStar(AbstractClueRule):
    """[1E**] 视野幂规则"""

    id = "1E**"
    aliases = ("E**", "EStarStar")
    name = "Eyesight Power"
    name.zh_CN = "视野幂"
    doc = "Clue value equals vertical eyesight raised to the power of horizontal eyesight (eyesight includes the cell itself)."
    doc.zh_CN = "线索值表示竖直视野的水平视野次方（视野包含自身）。"
    tags = ["Original", "Local", "Number Clue", "Creative"]
    creation_time = "2026-08-10"
    author = ("Gat", 992600401)

    def fill(self, board: Board) -> Board:
        """为所有非雷格填充线索值。"""
        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            # 计算水平视野（左右方向，包含自身）
            horizontal = self._calc_eyesight(board, pos, [pos.left, pos.right])
            # 计算竖直视野（上下方向，包含自身）
            vertical = self._calc_eyesight(board, pos, [pos.up, pos.down])
            # 线索值 = vertical ^ horizontal
            try:
                value = vertical ** horizontal
            except OverflowError:
                # 如果数值过大，截断到合理范围
                logger.warning(f"Power overflow at {pos}: {vertical}^{horizontal}, clamping to 9999")
                value = 9999
            board.set_value(pos, Value1EStarStar(pos, value))
            logger.trace(f"[1E**] {pos}: vertical={vertical}, horizontal={horizontal}, value={value}")
        return board

    @staticmethod
    def _calc_eyesight(board: Board, pos: Position, direction_funcs: List[Callable[[int], Position]]) -> int:
        """计算某个方向组合的视野（包含自身）"""
        count = 1  # 包含自身
        for fn in direction_funcs:
            n = 1
            while True:
                next_pos = fn(n)
                if not board.in_bounds(next_pos):
                    break
                if board.get_type(next_pos, special='raw') == "F":
                    break
                count += 1
                n += 1
        return count

    def create_constraints(self, board: Board, switch: Switch) -> None:
        """规则级无额外约束，由线索类自行实现。"""
        pass


class Value1EStarStar(AbstractClueValue):
    """[1E**] 线索值类"""

    id = Rule1EStarStar.id

    def __init__(self, pos: Position, value: int, *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.pos = pos
        # 存储计算后的线索值
        self._value = value
        self.value = SingleIntValue(value)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)
        if value is None:
            raise ValueError("value is empty")
        return cls(pos, value.value)

    def __repr__(self) -> str:
        return str(self._value)

    def direction_funcs(self) -> List[Callable[[int], Position]]:
        """返回四个方向的函数，用于视野计算。"""
        return [self.pos.up, self.pos.down, self.pos.left, self.pos.right]

    def high_light(self, board: 'Board') -> List['Position']:
        """高亮所有可见格子（包含自身）。"""
        positions = [self.pos]
        for direction_func in self.direction_funcs():
            n = 1
            while True:
                pos = direction_func(n)
                if not board.in_bounds(pos):
                    break
                if board.get_type(pos, special='raw') == "F":
                    break
                positions.append(pos)
                n += 1
        return positions

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        创建 CP-SAT 约束：
        1. 计算竖直视野 vertical（上下方向，包含自身）
        2. 计算水平视野 horizontal（左右方向，包含自身）
        3. 约束 vertical ^ horizontal == self._value
        """
        model = board.get_model()
        logger = get_logger()

        s = switch.get(model, self.pos)

        # 分别获取四个方向的视野变量（不包含自身）
        # 对于边界方向，eyesight_var 可能返回空列表，我们手动补0
        def get_direction_var(move_func: Callable[[int], Position]) -> IntVar:
            vars_ = eyesight_var(board, s, [move_func])
            if vars_:
                return vars_[0]
            else:
                return model.NewIntVar(0, 0, f"zero_{self.pos}_{move_func.__name__}")

        up_var = get_direction_var(self.pos.up)
        down_var = get_direction_var(self.pos.down)
        left_var = get_direction_var(self.pos.left)
        right_var = get_direction_var(self.pos.right)

        # 竖直视野 = up + down + 1（包含自身）
        vertical = model.NewIntVar(1, board.boundary().row + 1, f"vertical_{self.pos}")
        model.Add(vertical == up_var + down_var + 1).OnlyEnforceIf(s)

        # 水平视野 = left + right + 1（包含自身）
        horizontal = model.NewIntVar(1, board.boundary().col + 1, f"horizontal_{self.pos}")
        model.Add(horizontal == left_var + right_var + 1).OnlyEnforceIf(s)

        # 计算 vertical ^ horizontal
        # 由于 CP-SAT 不支持直接乘方，使用循环乘法实现
        # 但 horizontal 是变量，不能直接作为循环次数，需要枚举水平视野的可能值
        max_horizontal = board.boundary().col + 1
        max_vertical = board.boundary().row + 1
        # 计算最大可能值：max_vertical ^ max_horizontal
        max_power = max_vertical ** max_horizontal
        # 如果值太大，需要限制上限，否则求解器会爆炸
        # 对于 10x10 棋盘，10^10 = 10,000,000,000 太大了，我们限制为 10^6
        max_allowed = 10 ** 6
        if max_power > max_allowed:
            max_power = max_allowed

        # 创建乘方结果变量
        power_result = model.NewIntVar(0, max_power, f"power_{self.pos}")

        # 使用枚举法：对每个可能的水平视野值 h，创建条件分支
        # 当 horizontal == h 时，power_result == vertical ^ h
        # 注意：horizontal 至少为 1（包含自身）
        # 由于水平视野最大可能值为棋盘宽度，枚举所有可能性
        branches = []
        for h in range(1, max_horizontal + 1):
            # 创建条件变量：horizontal == h
            is_h = model.NewBoolVar(f"is_h_{self.pos}_{h}")
            model.Add(horizontal == h).OnlyEnforceIf([is_h, s])
            model.Add(horizontal != h).OnlyEnforceIf([is_h.Not(), s])

            # 计算 vertical ^ h
            # 使用连续乘法：result = vertical * vertical * ... (h 次)
            # 对于 h=1，result = vertical
            if h == 1:
                # 直接约束 power_result == vertical
                model.Add(power_result == vertical).OnlyEnforceIf([is_h, s])
            else:
                # 创建中间变量进行连乘
                # result_1 = vertical
                # result_2 = result_1 * vertical = vertical^2
                # ...
                # result_h = result_{h-1} * vertical = vertical^h
                prev_var = vertical
                for step in range(2, h + 1):
                    cur_var = model.NewIntVar(0, max_power, f"pow_{self.pos}_{h}_{step}")
                    model.AddMultiplicationEquality(cur_var, [prev_var, vertical]).OnlyEnforceIf([is_h, s])
                    prev_var = cur_var
                # 最终结果赋给 power_result
                model.Add(power_result == prev_var).OnlyEnforceIf([is_h, s])

            branches.append(is_h)

        # 确保至少有一个分支被选中（horizontal 必定在 1..max_horizontal 之间）
        # 但实际上 horizontal 已经在 1..max_horizontal 范围内，所以这个条件是自动满足的
        # 但我们仍需要确保 power_result 被正确赋值
        # 由于 horizontal 变量只能取一个值，且我们为每个值都添加了约束，所以 power_result 自然被唯一确定

        # 最终约束：power_result == self._value
        model.Add(power_result == self._value).OnlyEnforceIf(s)

        logger.trace(f"[1E**] {self.pos}: value={self._value}, horizontal={horizontal}, vertical={vertical}")
