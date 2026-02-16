#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1E'] 视差 (Eyesight')：线索表示纵向和横向的视野之差，箭头指示视野更长的方向
"""
from typing import Dict

from minesweepervariants.utils.web_template import Number, StrWithArrow
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.image_create import get_image, get_text, get_row, get_col, get_dummy


class Rule1E(AbstractClueRule):
    name = ["1E'", "E'", "视差", "Eyesight'"]
    doc = "线索表示纵向和横向的视野之差，箭头指示视野更长的方向"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            value = 0
            # 四方向的函数
            direction_funcs = [
                lambda _n: type(pos)(pos.x + _n, pos.y, pos.board_key),  # 右
                lambda _n: type(pos)(pos.x - _n, pos.y, pos.board_key),  # 左
                lambda _n: type(pos)(pos.x, pos.y + _n, pos.board_key),  # 上
                lambda _n: type(pos)(pos.x, pos.y - _n, pos.board_key)   # 下
            ]

            for fn in direction_funcs[:2]:  # 只计算横向
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos) == "F":  # 遇到雷，视线被阻挡
                        break
                    value += 1
                    n += 1

            for fn in direction_funcs[2:]:  # 只计算纵向
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos) == "F":  # 遇到雷，视线被阻挡
                        break
                    value -= 1
                    n += 1

            obj = Value1E(pos, bytes([value + 128]))
            board.set_value(pos, obj)
        return board


class Value1E(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.value = self.value - 128
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = []
        for i in [
            (1, 0), (-1, 0),
            (0, 1), (0, -1),
        ]:
            n = 0
            while board.get_type(pos := self.pos.shift(i[0] * n, i[1] * n)) not in "F":
                n += 1
                positions.append(pos)
        return positions

    @classmethod
    def type(cls) -> bytes:
        return Rule1E.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value+128])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        n = max(board.boundary().x, board.boundary().y)
        sight_vars = [
            model.NewIntVar(0, n + 1, f"up_{self.pos}"),
            model.NewIntVar(0, n + 1, f"down_{self.pos}"),
            model.NewIntVar(0, n + 1, f"left_{self.pos}"),
            model.NewIntVar(0, n + 1, f"right_{self.pos}"),
        ]
        moves = [
            lambda p: p.up(),
            lambda p: p.down(),
            lambda p: p.left(),
            lambda p: p.right()
        ]
        for sight_var, move in zip(sight_vars, moves):
            prev_cont_var = None
            curr = move(self.pos)
            cont_vars = []
            while board.in_bounds(curr):
                cont_var = model.NewBoolVar(f"cont_{curr}")
                if (prev_cont_var is None):
                    # 连续非雷段的起始：当前位置是非雷
                    model.Add(cont_var == 1).OnlyEnforceIf([board.get_variable(curr).Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), s])
                else:
                    # 连续非雷段的延续：前一个位置在连续非雷段，且当前位置是非雷
                    model.Add(cont_var == 1).OnlyEnforceIf([prev_cont_var, board.get_variable(curr).Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([prev_cont_var.Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), s])
                cont_vars.append(cont_var)
                prev_cont_var = cont_var
                curr = move(curr)
            model.Add(sum(cont_vars) == sight_var).OnlyEnforceIf(s)
        
        model.Add(sight_vars[0] + sight_vars[1] - sight_vars[2] - sight_vars[3] == self.value).OnlyEnforceIf(s)

    def web_component(self, board) -> Dict:
        if self.value == 0:
            return Number(0)
        if self.value < 0:
            return get_col(
                get_image(
                    "double_arrow",
                    image_height=0.4,
                ),
                get_dummy(height=-0.1),
                get_text(str(-self.value))
            )
        if self.value > 0:
            return get_row(
                get_dummy(width=0.15),
                get_image(
                    "double_arrow",
                    style="transform: rotate(90deg);"
                ),
                get_dummy(width=-0.15),
                get_text(str(self.value)),
                get_dummy(width=0.15),
            )
    def web_component(self, board) -> Dict:
        if self.value == 0:
            return Number(0)
        if self.value < 0:
            return StrWithArrow(str(-self.value), "left_right")
        if self.value > 0:
            return StrWithArrow(str(self.value), "up_down")


    def compose(self, board):
        if self.value == 0:
            return super().compose(board)
        if self.value < 0:
            return get_col(
                get_image(
                    "double_horizontal_arrow",
                    image_height=0.4,
                ),
                get_dummy(height=-0.1),
                get_text(str(-self.value))
            )
        if self.value > 0:
            return get_row(
                    get_dummy(width=0.15),
                    get_image("double_vertical_arrow", ),
                    get_dummy(width=-0.15),
                    get_text(str(self.value)),
                    get_dummy(width=0.15),
            )
