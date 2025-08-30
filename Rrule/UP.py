#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/07 22:21
# @Author  : Wu_RH
# @FileName: UP.py
"""
[UP]唯一路径(Unique Path): 线索格表示从这个格开始只能往右或下走，到达右下角的方法数。
"""
import math
from typing import List

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


class RuleUP(AbstractClueRule):
    name = ["UP", "唯一路径", "Unique Path"]
    doc = "线索格表示从这个格开始只能往右或下走，到达右下角的方法数。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for key in board.get_interactive_keys():
            root_pos = board.boundary(key)
            for col_pos in board.get_col_pos(root_pos)[::-1]:
                for pos in board.get_row_pos(col_pos)[::-1]:
                    if board.get_type(pos) != "N":
                        continue
                    value = 0
                    if board.get_type(pos.down()) == "C":
                        value += board[pos.down()].value
                    if board.get_type(pos.right()) == "C":
                        value += board[pos.right()].value
                    if (
                        board.get_type(pos.down()) == "" and
                        board.get_type(pos.right()) == ""
                    ):
                        value = 1
                    obj = ValueUP(pos, bytes([value]))
                    board[pos] = obj
        return board

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        pos_var_map = {}
        for key in board.get_interactive_keys():
            ub_x = board.boundary(key).x
            ub_y = board.boundary(key).y
            for pos, var in board(mode="variable", key=key):
                x, y = pos.x, pos.y
                ub = math.comb(ub_x - x + ub_y - y, ub_y - y)
                pos_var_map[pos] = model.NewIntVar(0, ub, f"{pos}:dp")
                model.Add(pos_var_map[pos] == 0).OnlyEnforceIf(var)

            for pos, var in board(mode="variable", key=key):
                var_d = 0
                var_r = 0
                if board.in_bounds(pos.down()):
                    var_d = pos_var_map[pos.down()]
                if board.in_bounds(pos.right()):
                    var_r = pos_var_map[pos.right()]
                if board.boundary(key) == pos:
                    model.Add(pos_var_map[pos] == 1).OnlyEnforceIf(var.Not())
                else:
                    model.Add(pos_var_map[pos] == var_d + var_r).OnlyEnforceIf(var.Not())
                obj = board[pos]
                if isinstance(obj, ValueUP):
                    obj.create_constraints_(board, pos_var_map[pos], switch)


class ValueUP(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.pos = pos
        self.value = code[0]

    def __repr__(self):
        return str(self.value)

    def high_light(self, board: 'AbstractBoard', pos=None) -> List['AbstractPosition'] | None:
        if pos is None:
            pos = self.pos
        if board.get_type(pos) != "C":
            return [pos]
        positions = {pos}
        for _pos in self.high_light(board, pos.down()):
            positions.add(_pos)
        for _pos in self.high_light(board, pos.right()):
            positions.add(_pos)
        return list(positions)

    @classmethod
    def type(cls) -> bytes:
        return RuleUP.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints_(self, board: 'AbstractBoard', var, switch: 'Switch'):
        model = board.get_model()
        model.Add(var == self.value).OnlyEnforceIf(switch.get(model, self))
