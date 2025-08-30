#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/15 11:28
# @Author  : Wu_RH
# @FileName: RuleC.py
"""
[RULE-013]没想好: 如果一个雷的周围八格有四个及以上的雷，那么这个雷的雷值是0，总雷数不受此规则影响。
"""
from ortools.sat.python.cp_model import IntVar, CpModel

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


class RuleC(AbstractClueRule):
    name = ["Rule-013", "没想好", "τD", "RULE-013"]
    doc = "如果一个雷的周围八格有四个及以上的雷，那么这个雷的雷值是0，总雷数不受此规则影响。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        mines_map = {}
        for pos, _ in board("F"):
            mines_map[pos] = board.batch(pos.neighbors(1, 2), "type").count("F") < 4
        for pos, _ in board("N"):
            value = 0
            for _pos in pos.neighbors(2):
                if _pos not in mines_map:
                    continue
                value += mines_map[_pos]
            board[pos] = ValueC(pos, bytes([value]))
        return board

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()

        var_map = {}
        for pos, var in board(mode="var"):
            boolVar = model.NewBoolVar(f"bool[{pos}]")
            sum_var = sum(board.batch(pos.neighbors(1, 2), "var", drop_none=True))
            model.Add(sum_var < 4).OnlyEnforceIf([boolVar, var])
            model.Add(sum_var > 3).OnlyEnforceIf([boolVar.Not(), var])
            model.Add(boolVar == 0).OnlyEnforceIf(var.Not())
            var_map[pos] = boolVar
        for pos, obj in board():
            if not isinstance(obj, ValueC):
                continue
            var_list = [var_map[_pos] for _pos in pos.neighbors(2) if _pos in var_map]
            obj.create_constraints_(model, var_list, switch.get(model, pos))


class ValueC(AbstractClueValue):

    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.value = code[0]

    def __repr__(self) -> str:
        return str(self.value)

    def code(self) -> bytes:
        return bytes([self.value])

    @classmethod
    def type(cls) -> bytes:
        return RuleC.name[0].encode()

    def create_constraints_(self, model: CpModel, var_list: list, switch: 'IntVar'):
        model.Add(sum(var_list) == self.value).OnlyEnforceIf(switch)
