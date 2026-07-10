#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/10
# @Author  : NT (2201963934)
# @FileName: Masyu.py
"""
[Masyu] 珍珠：SL简单回路，雷线索分为白珍珠：直线通过本格且相邻两格至少有一个转弯，黑珍珠：拐弯通过本格且相邻两格均不转弯，非珍珠：不满足以上两种。
"""
from typing import Optional

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.json_object import JSONObject, deep_unwrap


class RuleMasyu(AbstractMinesClueRule):
    id = "Masyu"
    name = "Masyu"
    name.zh_CN = "珍珠"
    doc = "Masyu: White pearl means straight through with at least one turn in adjacent cells, black pearl means turn through with no turns in adjacent cells, non-pearl otherwise."
    doc.zh_CN = "珍珠：SL简单回路，雷线索分为白珍珠：直线通过本格且相邻两格至少有一个转弯，黑珍珠：拐弯通过本格且相邻两格均不转弯，非珍珠：不满足以上两种。"
    tags = ["Original", "Local", "Mine-Value", "Creative"]
    creation_time = "2026-07-10"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """为每个雷格生成线索值（珍珠类型）。
        白珍珠：直线通过（一对相反方向为雷）且有且仅有一个转弯（另一对方向恰好一个雷），总雷数=3。
        黑珍珠：拐弯（两个相邻方向为雷，即一对垂直方向），总雷数=2。
        非珍珠：其他情况。
        """
        for pos, _ in board("F"):
            # 获取四个邻居的雷状态
            up = board.in_bounds(pos.up()) and board.get_type(pos.up()) == "F"
            down = board.in_bounds(pos.down()) and board.get_type(pos.down()) == "F"
            left = board.in_bounds(pos.left()) and board.get_type(pos.left()) == "F"
            right = board.in_bounds(pos.right()) and board.get_type(pos.right()) == "F"
            
            ud_count = int(up) + int(down)
            lr_count = int(left) + int(right)
            total = ud_count + lr_count
            
            # 判断类型
            if total == 3 and ((ud_count == 2 and lr_count == 1) or (lr_count == 2 and ud_count == 1)):
                # 白珍珠：一对相反方向为雷，另一对方向恰好一个雷
                pearl_type = 0  # 白珍珠
            elif total == 2 and ud_count == 1 and lr_count == 1:
                # 黑珍珠：两个相邻方向为雷（拐弯）
                pearl_type = 1  # 黑珍珠
            else:
                pearl_type = 2  # 非珍珠
            
            value_obj = ValueMasyu(pos, code=bytes([pearl_type]))
            board.set_value(pos, value_obj)
        return board


class ValueMasyu(AbstractMinesValue):
    id = RuleMasyu.id

    def __init__(self, pos: 'Position', code: Optional[bytes] = None):
        super().__init__(pos, b'')
        self.pos = pos
        if code is None:
            self.type = 2  # 默认为非珍珠
        else:
            self.type = code[0] & 0x03
        self.value = SingleIntValue(self.type)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractMinesValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Expected value template")
        int_val = SingleIntValue.try_from(_data)
        if int_val is None:
            raise ValueError("Invalid value template")
        return cls(pos, code=bytes([int_val.value & 0x03]))

    def __repr__(self):
        return ["白", "黑", "非"][self.type] + "珍珠"

    def code(self) -> bytes:
        return bytes([self.type & 0x03])

    @classmethod
    def type(cls) -> bytes:
        return RuleMasyu.id.encode("ascii")

    def weaker(self, board: 'Board'):
        return self

    def weaker_times(self):
        return 0

    def create_constraints(self, board: 'Board', switch):
        """添加约束：该雷格为雷，且其邻居雷的分布符合珍珠类型。"""
        model = board.get_model()
        s = switch.get(model, self)
        # 自身必须为雷
        self_var = board.get_variable(self.pos)
        if self_var is not None:
            model.Add(self_var == 1).OnlyEnforceIf(s)

        # 获取四个邻居的变量，边界外设为0
        neighbor_vars = {}
        for name, n_pos in [("up", self.pos.up()), ("down", self.pos.down()),
                            ("left", self.pos.left()), ("right", self.pos.right())]:
            if board.in_bounds(n_pos):
                v = board.get_variable(n_pos)
                if v is not None:
                    neighbor_vars[name] = v
                else:
                    zero = model.NewBoolVar(f"zero_{name}_{self.pos}")
                    model.Add(zero == 0)
                    neighbor_vars[name] = zero
            else:
                zero = model.NewBoolVar(f"zero_{name}_{self.pos}")
                model.Add(zero == 0)
                neighbor_vars[name] = zero

        up = neighbor_vars["up"]
        down = neighbor_vars["down"]
        left = neighbor_vars["left"]
        right = neighbor_vars["right"]

        if self.type == 0:
            # 白珍珠：直线通过（存在相反方向雷）且至少一个转弯（另一方向至少一个雷）
            # 条件：(up+down>=2 and left+right>=1) or (left+right>=2 and up+down>=1)
            cond1 = model.NewBoolVar("white_cond1")
            # cond1 => (up+down>=2 and left+right>=1)
            model.Add(up + down >= 2).OnlyEnforceIf(cond1)
            model.Add(left + right >= 1).OnlyEnforceIf(cond1)

            cond2 = model.NewBoolVar("white_cond2")
            model.Add(left + right >= 2).OnlyEnforceIf(cond2)
            model.Add(up + down >= 1).OnlyEnforceIf(cond2)

            # 至少一个条件成立
            model.AddBoolOr([cond1, cond2]).OnlyEnforceIf(s)

        elif self.type == 1:
            # 黑珍珠：恰好两个相邻方向雷（即一个垂直一个水平），无相反方向
            # 约束：total==2, up+down==1, left+right==1
            model.Add(up + down + left + right == 2).OnlyEnforceIf(s)
            model.Add(up + down == 1).OnlyEnforceIf(s)
            model.Add(left + right == 1).OnlyEnforceIf(s)

        else:  # 非珍珠
            # 非珍珠：不满足白珍珠和黑珍珠条件
            # 白珍珠条件
            cond1 = model.NewBoolVar("non_white_cond1")
            model.Add(up + down >= 2).OnlyEnforceIf(cond1)
            model.Add(left + right >= 1).OnlyEnforceIf(cond1)

            cond2 = model.NewBoolVar("non_white_cond2")
            model.Add(left + right >= 2).OnlyEnforceIf(cond2)
            model.Add(up + down >= 1).OnlyEnforceIf(cond2)

            white = model.NewBoolVar("white_flag")
            model.AddBoolOr([cond1, cond2]).OnlyEnforceIf(white)
            model.AddBoolAnd([cond1.Not(), cond2.Not()]).OnlyEnforceIf(white.Not())

            # 黑珍珠条件
            black = model.NewBoolVar("black_flag")
            model.Add(up + down + left + right == 2).OnlyEnforceIf(black)
            model.Add(up + down == 1).OnlyEnforceIf(black)
            model.Add(left + right == 1).OnlyEnforceIf(black)
            # 约束 black 为 False
            model.Add(black == 0).OnlyEnforceIf(s)
            # 约束 white 为 False
            model.Add(white == 0).OnlyEnforceIf(s)
