#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/04 07:39
# @Author  : Wu_RH
# @FileName: 4V.py
"""
[4V1L]2X'plus: 线索表示数字是两个题板中相同位置的其中一个范围中心3*3区域的雷总数 线索均比真实值大1或小1
"""

from .....abs.Rrule import AbstractClueRule, AbstractClueValue
from .....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from .....utils.impl_obj import VALUE_QUESS, MINES_TAG
from .....utils.tool import get_random

from . import BOARD_NAME_4V


class Rule4V(AbstractClueRule):
    name = ["4V1L", "误差映射"]
    doc = "线索表示数字是两个题板中相同位置的其中一个范围中心3*3区域的雷总数 线索均比真实值大1或小1"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        size = (board.boundary().x + 1, board.boundary().y + 1)
        board.generate_board(BOARD_NAME_4V, size)
        board.set_config(BOARD_NAME_4V, "interactive", True)
        board.set_config(BOARD_NAME_4V, "row_col", True)
        board.set_config(BOARD_NAME_4V, "VALUE", VALUE_QUESS)
        board.set_config(BOARD_NAME_4V, "MINES", MINES_TAG)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()

        for pos, _ in board():
            neighbors_list = []
            for _key in [MASTER_BOARD, BOARD_NAME_4V]:
                _pos = pos.clone()
                _pos.board_key = _key
                neighbors_list.append(_pos.neighbors(0, 2))
            values = [board.batch(positions, mode="type").count("F") for positions in neighbors_list]
            if values[0] == 0:
                values[0] = 1
            elif values[0] == 8:
                values[0] = 7
            else:
                values[0] += 1 if random.random() > 0.5 else -1
            if values[1] == 0:
                values[1] = 1
            elif values[1] == 8:
                values[1] = 7
            else:
                values[1] += 1 if random.random() > 0.5 else -1
            r_value = 0 if random.random() > 0.7 else 1
            _pos.board_key = MASTER_BOARD
            if board.get_type(_pos) != "F":
                obj = Value4V(pos=_pos, code=bytes([values[r_value]]))
                board.set_value(_pos, obj)
            _pos.board_key = BOARD_NAME_4V
            if board.get_type(_pos) != "F":
                obj = Value4V(pos=_pos, code=bytes([values[1 - r_value]]))
                board.set_value(_pos, obj)

        return board

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            size = info["size"][key]
            ub += size[0] * size[1]
        info["soft_fn"](ub * 0.4)


class Value4V(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.neighbors_list = []
        for key in [MASTER_BOARD, BOARD_NAME_4V]:
            _pos = pos.clone()
            _pos.board_key = key
            self.neighbors_list.append(_pos.neighbors(0, 2))
        self.value = code[0]
        self.pos = pos

    @classmethod
    def type(cls) -> bytes:
        return Rule4V.name[0].encode("ascii")

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors_list[0] + self.neighbors_list[1]

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        sum_var = []
        a = model.NewBoolVar(f"[{Rule4V.name}]tmp")
        b = model.NewBoolVar(f"[{Rule4V.name}]tmp")
        for neighbor in self.neighbors_list:
            var_list = board.batch(neighbor, mode="variable", drop_none=True)
            if var_list:
                t = model.NewBoolVar(f"[{Rule4V.name}]tmp")
                model.Add(sum(var_list) == self.value + 1).OnlyEnforceIf([t, a, s])
                model.Add(sum(var_list) != self.value + 1).OnlyEnforceIf([t.Not(), a, s])

                model.Add(sum(var_list) == self.value - 1).OnlyEnforceIf([t, b, s])
                model.Add(sum(var_list) != self.value - 1).OnlyEnforceIf([t.Not(), b, s])
                sum_var.append(t)
        model.AddBoolOr(sum_var).OnlyEnforceIf(s)
        model.AddBoolOr([a, b]).OnlyEnforceIf(s)

    def code(self) -> bytes:
        return bytes([self.value])
