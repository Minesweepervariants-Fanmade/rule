#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/09 09:33
# @Author  : Wu_RH
# @FileName: 1N.py
"""
[4V1N] 负雷 (Negative)：线索表示数字是两个题板中相同位置的其中一个3x3范围内染色格与非染色格的雷数差
"""
from .....abs.Rrule import AbstractClueRule, AbstractClueValue
from .....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from .....utils.impl_obj import VALUE_QUESS, MINES_TAG
from .....utils.tool import get_random

from . import BOARD_NAME_4V


class Rule1N(AbstractClueRule):
    name = ["4V1N", "负雷映射"]
    doc = "线索表示数字是两个题板中相同位置的其中一个3x3范围内染色格与非染色格的雷数差"

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
        for pos, _ in board("N"):
            values = [-1, -1]
            pos.board_key = MASTER_BOARD
            values[0] = abs(sum(board.get_type(_pos) == "F" if
                            board.get_dyed(_pos)
                            else -(board.get_type(_pos) == "F")
                            for _pos in pos.neighbors(0, 2)))
            pos.board_key = BOARD_NAME_4V
            values[1] = abs(sum(board.get_type(_pos) == "F" if
                            board.get_dyed(_pos)
                            else -(board.get_type(_pos) == "F")
                            for _pos in pos.neighbors(0, 2)))
            r_value = 0 if random.random() > 0.7 else 1
            pos.board_key = MASTER_BOARD
            if board.get_type(pos) != "F":
                obj = Value1N(pos=pos, code=bytes([values[r_value]]))
                board.set_value(pos, obj)
            pos.board_key = BOARD_NAME_4V
            if board.get_type(pos) != "F":
                obj = Value1N(pos=pos, code=bytes([values[1 - r_value]]))
                board.set_value(pos, obj)

        return board


class Value1N(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.neighbors_list = []
        for key in [MASTER_BOARD, BOARD_NAME_4V]:
            _pos = pos.clone()
            _pos.board_key = key
            self.neighbors_list.append(_pos.neighbors(0, 2))
        self.value = code[0]
        self.pos = pos

    def __repr__(self) -> str:
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors_list[0] + self.neighbors_list[1]

    @classmethod
    def type(cls) -> bytes:
        return Rule1N.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        a = model.NewBoolVar("abs_diff")
        b = model.NewBoolVar("abs_diff")

        nei_a_d = [_pos for _pos in self.neighbors_list[0] if board.get_dyed(_pos)]
        nei_a_n = [_pos for _pos in self.neighbors_list[0] if not board.get_dyed(_pos)]
        nei_b_d = [_pos for _pos in self.neighbors_list[1] if board.get_dyed(_pos)]
        nei_b_n = [_pos for _pos in self.neighbors_list[1] if not board.get_dyed(_pos)]

        vars_a_d = board.batch(nei_a_d, mode="variable", drop_none=True)
        vars_a_n = board.batch(nei_a_n, mode="variable", drop_none=True)
        vars_b_d = board.batch(nei_b_d, mode="variable", drop_none=True)
        vars_b_n = board.batch(nei_b_n, mode="variable", drop_none=True)

        diff_a = sum(vars_a_d) - sum(vars_a_n)
        max_abs_a = len(vars_a_d) + len(vars_a_n)
        abs_diff_a = model.NewIntVar(0, max_abs_a, "abs_diff")

        diff_b = sum(vars_b_d) - sum(vars_b_n)
        max_abs_b = len(vars_b_d) + len(vars_b_n)
        abs_diff_b = model.NewIntVar(0, max_abs_b, "abs_diff")

        model.AddAbsEquality(abs_diff_a, diff_a)
        model.Add(abs_diff_a == self.value).OnlyEnforceIf([a, s])
        model.AddAbsEquality(abs_diff_b, diff_b)
        model.Add(abs_diff_b == self.value).OnlyEnforceIf([b, s])

        model.AddBoolOr([a, b]).OnlyEnforceIf(s)
