#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/15 11:28
# @Author  : Wu_RH
# @FileName: RuleC.py
"""
[RULE-012]没想好: 每个雷的雷值等于它周围八格（包括自身）的总雷数，总雷数不受此规则影响。
"""
from ortools.sat.python.cp_model import IntVar, CpModel

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


class RuleC(AbstractClueRule):
    name = ["Rule-012", "没想好", "τC", "RULE-012"]
    doc = "每个雷的雷值等于它周围八格（包括自身）的总雷数，总雷数不受此规则影响。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        mines_map = {}
        for pos, _ in board("F"):
            mines_map[pos] = board.batch(pos.neighbors(0, 2), "type").count("F")
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
            intVar = model.NewIntVar(0, 9, f"int[{pos}]")
            model.Add(intVar == sum(board.batch(pos.neighbors(0, 2), "var", drop_none=True))).OnlyEnforceIf(var)
            model.Add(intVar == 0).OnlyEnforceIf(var.Not())
            var_map[pos] = intVar
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
