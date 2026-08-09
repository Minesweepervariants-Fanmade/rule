#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-10
# @Author  : NT (2201963934)
# @FileName: 1E_square.py
"""
[1E[]] 视野乘积 (Eyesight Square)：线索值表示竖直视野与水平视野的乘积。

规则语义:
- 右线规则(Rrule)，线索值为竖直视野与水平视野的乘积。
- 水平视野 = 左视野 + 右视野 + 1 (包括自身)
- 竖直视野 = 上视野 + 下视野 + 1 (包括自身)
- 视野定义：从线索格出发，沿某方向连续非雷格的数量（包括自身），遇雷或边界停止。
- 线索值 = 水平视野 × 竖直视野。

实现说明:
- fill 阶段：遍历所有非雷格，计算实际视野乘积，设置线索值。
- create_constraints 阶段：使用 eyesight_var 工具获取四个方向的视野变量，
  然后约束 (右+左+1) * (上+下+1) == 线索值。
"""

from typing import Dict, cast

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template


class Rule1E_Square(AbstractClueRule):
    """[1E[]] 视野乘积规则类"""

    id = "1E[]"
    aliases = ("E[]", "E_Square")
    name = "Eyesight Square"
    name.zh_CN = "视野乘积"
    doc = (
        "Clue value is the product of vertical and horizontal eyesight. "
        "Horizontal = left + right + 1 (including itself), Vertical = up + down + 1 (including itself)."
    )
    doc.zh_CN = "线索值表示竖直视野与水平视野的乘积。水平视野 = 左视野 + 右视野 + 1（包括自身），竖直视野 = 上视野 + 下视野 + 1（包括自身）。"
    tags = ["Original", "Local", "Number Clue", "Creative"]
    creation_time = "2026-08-10"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """
        填充所有非雷格为 [1E[]] 线索。
        计算实际水平视野和垂直视野（均包含自身），取乘积作为线索值。
        """
        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            # 四个方向的函数 (右, 左, 上, 下)
            # 直接使用 pos.shift 避免闭包问题
            horizontal = 1  # 包含自身
            vertical = 1    # 包含自身

            # 右方向
            n = 1
            while True:
                p = pos.shift(n, 0)
                if not board.in_bounds(p):
                    break
                if board.get_type(p, special='raw') == "F":
                    break
                horizontal += 1
                n += 1

            # 左方向
            n = 1
            while True:
                p = pos.shift(-n, 0)
                if not board.in_bounds(p):
                    break
                if board.get_type(p, special='raw') == "F":
                    break
                horizontal += 1
                n += 1

            # 上方向
            n = 1
            while True:
                p = pos.shift(0, -n)
                if not board.in_bounds(p):
                    break
                if board.get_type(p, special='raw') == "F":
                    break
                vertical += 1
                n += 1

            # 下方向
            n = 1
            while True:
                p = pos.shift(0, n)
                if not board.in_bounds(p):
                    break
                if board.get_type(p, special='raw') == "F":
                    break
                vertical += 1
                n += 1

            value = horizontal * vertical
            board.set_value(pos, Value1E_Square(pos, value))
            logger.trace(f"[1E[]] {pos}: horizontal={horizontal}, vertical={vertical}, product={value}")

        return board


class Value1E_Square(AbstractClueValue):
    """[1E[]] 视野乘积线索值类"""

    id = Rule1E_Square.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value = SingleIntValue(value)
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        """从 JSON 恢复线索值对象"""
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        """高亮显示四个方向上的所有可见格子（非雷格）"""
        positions = []
        directions = [(1, 0), (-1, 0), (0, -1), (0, 1)]
        for dx, dy in directions:
            n = 1
            while True:
                pos = self.pos.shift(dx * n, dy * n)
                if not board.in_bounds(pos):
                    break
                if board.get_type(pos, special='raw') == "F":
                    break
                positions.append(pos)
                n += 1
        # 包含自身
        positions.append(self.pos)
        return positions

    def create_constraints(self, board: 'Board', switch):
        """
        创建 CP-SAT 约束：使用 eyesight_var 工具获取四个方向的视野变量，
        然后约束 (右+左+1) * (上+下+1) == 线索值。
        """
        from .eyesight import eyesight_var
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 四个方向的函数 (右, 左, 上, 下)
        def right(n): return self.pos.shift(n, 0)
        def left(n): return self.pos.shift(-n, 0)
        def up(n): return self.pos.shift(0, -n)
        def down(n): return self.pos.shift(0, n)

        direction_funcs = [right, left, up, down]

        # 为每个方向单独获取视野变量
        dir_vars = []
        for fn in direction_funcs:
            vars_ = eyesight_var(board, s, [fn])
            if vars_:
                dir_vars.append(vars_[0])
            else:
                # 该方向没有有效位置，视野为0
                zero_var = model.NewIntVar(0, 0, f"zero_{len(dir_vars)}")
                dir_vars.append(zero_var)

        # 确保有4个变量
        while len(dir_vars) < 4:
            zero_var = model.NewIntVar(0, 0, f"zero_{len(dir_vars)}")
            dir_vars.append(zero_var)

        right_var, left_var, up_var, down_var = dir_vars[:4]

        # 水平视野 = 右 + 左 + 1 (包含自身)
        h_var = model.NewIntVar(1, board.boundary().col + 1, f"h_{self.pos}")
        model.Add(h_var == right_var + left_var + 1).OnlyEnforceIf(s)

        # 垂直视野 = 上 + 下 + 1 (包含自身)
        v_var = model.NewIntVar(1, board.boundary().row + 1, f"v_{self.pos}")
        model.Add(v_var == up_var + down_var + 1).OnlyEnforceIf(s)

        # 约束乘积等于线索值
        product_var = model.NewIntVar(1, (board.boundary().col + 1) * (board.boundary().row + 1), f"prod_{self.pos}")
        model.AddMultiplicationEquality(product_var, [h_var, v_var]).OnlyEnforceIf(s)
        model.Add(product_var == self.value.value).OnlyEnforceIf(s)

        logger.trace(f"[1E[]] {self.pos}: constrained h={h_var}, v={v_var}, product={self.value.value}")

    def web_component(self, board) -> Dict:
        """Web 渲染：只显示数字"""
        from minesweepervariants.utils.web_template import Number
        return Number(str(self.value.value))

    def compose(self, board):
        """图片渲染：只显示数字"""
        from minesweepervariants.utils.image_template import get_col, get_text, get_dummy
        return get_col(
            get_dummy(height=0.3),
            get_text(str(self.value.value)),
            get_dummy(height=0.3),
        )
