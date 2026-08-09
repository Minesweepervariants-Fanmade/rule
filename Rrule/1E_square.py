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
- 水平视野 = 左视野 + 右视野，竖直视野 = 上视野 + 下视野。
- 视野定义：从线索格出发，沿某方向连续非雷格的数量（不包括自身），遇雷或边界停止。
- 线索值 = 水平视野 × 竖直视野。

实现说明:
- fill 阶段：遍历所有非雷格，计算实际视野乘积，设置线索值。
- create_constraints 阶段：枚举四个方向的所有可能步数组合，约束乘积等于线索值。
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
        "Horizontal = left + right, Vertical = up + down."
    )
    doc.zh_CN = "线索值表示竖直视野与水平视野的乘积。水平视野 = 左视野 + 右视野，竖直视野 = 上视野 + 下视野。"
    tags = ["Original", "Local", "Number Clue", "Creative"]
    creation_time = "2026-08-10"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """
        填充所有非雷格为 [1E[]] 线索。
        计算实际水平视野和垂直视野，取乘积作为线索值。
        """
        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            # 四个方向的函数 (右, 左, 上, 下)
            direction_funcs = [
                lambda _n, p=pos: p.right(_n),
                lambda _n, p=pos: p.left(_n),
                lambda _n, p=pos: p.up(_n),
                lambda _n, p=pos: p.down(_n),
            ]

            horizontal = 0  # 左视野 + 右视野
            vertical = 0    # 上视野 + 下视野

            # 计算横向视野 (右 + 左)
            for fn in direction_funcs[:2]:
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos, special='raw') == "F":
                        break
                    horizontal += 1
                    n += 1

            # 计算纵向视野 (上 + 下)
            for fn in direction_funcs[2:]:
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos, special='raw') == "F":
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
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
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
        return positions

    def create_constraints(self, board: 'Board', switch):
        """
        创建 CP-SAT 约束：枚举四个方向的所有可能步数组合，约束乘积等于线索值。
        """
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 四个方向的函数 (右, 左, 上, 下)
        direction_funcs = [
            lambda n, p=self.pos: p.right(n),
            lambda n, p=self.pos: p.left(n),
            lambda n, p=self.pos: p.up(n),
            lambda n, p=self.pos: p.down(n),
        ]

        def max_steps(fn):
            """计算某方向的最大步数（到边界或无法获取变量为止）"""
            n = 1
            while True:
                p = fn(n)
                if not board.in_bounds(p):
                    return n - 1
                if board.get_variable(p) is None:
                    return n - 1
                n += 1

        def collect_dir(fn, steps):
            """
            收集某方向的 T 位置（非雷格）和 F 变量（阻挡雷格）。
            返回: (t_positions, f_var, ok)
            """
            t_positions = []
            if steps == 0:
                p_block = fn(1)
                f_var = board.get_variable(p_block) if board.in_bounds(p_block) else None
                return t_positions, f_var, True

            for k in range(1, steps + 1):
                p = fn(k)
                if not board.in_bounds(p):
                    return [], None, False
                var = board.get_variable(p)
                if var is None:
                    return [], None, False
                t_positions.append(p)

            p_block = fn(steps + 1)
            f_var = board.get_variable(p_block) if board.in_bounds(p_block) else None
            return t_positions, f_var, True

        # 计算每个方向的最大步数
        max_steps_list = [max_steps(fn) for fn in direction_funcs]

        possible_list = []  # 每项 (set_of_T_positions, list_of_F_vars_or_None)

        def enum_counts(idx: int, counts: list[int], accum_T: list, accum_F: list):
            """递归枚举四个方向的步数组合"""
            # 计算当前已确定的水平视野和垂直视野
            horizontal = counts[0] + counts[1]
            vertical = counts[2] + counts[3]

            # 计算剩余方向的最大可能增量
            horiz_remain = 0
            vert_remain = 0
            for j in range(idx, 4):
                if j < 2:
                    horiz_remain += max_steps_list[j]
                else:
                    vert_remain += max_steps_list[j]

            # 剪枝：检查是否存在 h in [horizontal, horizontal + horiz_remain]
            # 和 v in [vertical, vertical + vert_remain] 使得 h * v == self.value.value
            max_h = horizontal + horiz_remain
            max_v = vertical + vert_remain
            possible = False
            for h in range(horizontal, max_h + 1):
                for v in range(vertical, max_v + 1):
                    if h * v == self.value.value:
                        possible = True
                        break
                if possible:
                    break
            if not possible:
                return

            if idx == 4:
                # 检查乘积是否匹配
                if horizontal * vertical == self.value.value:
                    possible_list.append((set(accum_T), list(accum_F)))
                return

            fn = direction_funcs[idx]
            max_n = max_steps_list[idx]
            for steps in range(0, max_n + 1):
                t_pos, f_var, ok = collect_dir(fn, steps)
                if not ok:
                    continue

                # push
                added = len(t_pos)
                accum_T.extend(t_pos)
                accum_F.append(f_var)
                counts[idx] = steps

                enum_counts(idx + 1, counts, accum_T, accum_F)

                # pop
                for _ in range(added):
                    accum_T.pop()
                accum_F.pop()
                counts[idx] = 0

        enum_counts(0, [0, 0, 0, 0], [], [])

        tmp_list = []
        for t_positions, f_vars in possible_list:
            vars_t = board.batch(t_positions, mode="variable") if t_positions else []
            vars_f = [v for v in f_vars if v is not None]

            tmp = model.NewBoolVar(f"tmp_1E_square_{self.pos.x}_{self.pos.y}_{len(tmp_list)}")
            # 当 tmp 和线索开关 s 同时成立时，T 位置均为非雷（sum == 0）
            model.Add(sum(vars_t) == 0).OnlyEnforceIf([tmp, s])
            # 阻挡位置（若有变量）全部为雷
            if vars_f:
                model.AddBoolAnd(vars_f).OnlyEnforceIf([tmp, s])
            tmp_list.append(tmp)

        if tmp_list:
            model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
        else:
            # 没有有效组合，约束不可满足
            model.Add(False).OnlyEnforceIf(s)
            logger.warning(f"[1E[]] {self.pos}: no valid combinations for value {self.value.value}")

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
