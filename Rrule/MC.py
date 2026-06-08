#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 18:58
# @Author  : Wu_RH
# @FileName: MC.py
"""
[MC]染色格合并（Mine-Combination）:线索表示周围八格的雷数，染色格中如有雷就同一算为一雷（剩余雷数不受影响）
"""
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from minesweepervariants.impl.summon.solver import Switch


class RuleMC(AbstractClueRule):
    id = "MC"
    name = "Mine-Combination"
    name.zh_CN = "染色格合并"
    doc = "Clue indicates the number of mines in surrounding eight cells; if there is a mine in a dyed cell, it counts as one mine (total mine count unaffected)"
    doc.zh_CN = "线索表示周围八格的雷数，染色格中如有雷就同一算为一雷（剩余雷数不受影响）"
    tags = ["Variant", "Local", "Number Clue", "Dyed"]
    creation_time = "2025-08-13"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            nei = pos.neighbors(2)
            type_list = board.batch(nei, mode="type")
            dye_list = board.batch(nei, mode="dye")
            value = [t for t, d in zip(type_list, dye_list) if not d].count("F")
            value += [t for t, d in zip(type_list, dye_list) if d].count("F") > 0
            obj = ValueMC(pos, bytes([value]))
            board[pos] = obj
        return board


class ValueMC(AbstractClueValue):
    id = RuleMC.id
    def __init__(self, pos: 'Position', code: bytes = b''):
        super().__init__(pos, code)
        self.value = code[0]

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return RuleMC.id.encode()

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        nei = [_pos for _pos in self.pos.neighbors(2) if board.is_valid(_pos)]
        var_list = board.batch(nei, mode="var")
        dye_list = board.batch(nei, mode="dye")

        var1_list = [v for v, d in zip(var_list, dye_list) if not d]
        var2_list = [v for v, d in zip(var_list, dye_list) if d]

        tmp = model.NewBoolVar("tmp")
        model.Add(sum(var1_list + [tmp]) == self.value).OnlyEnforceIf(s)
        # model.AddBoolOr(var2_list).OnlyEnforceIf(tmp)
        # model.AddBoolAnd([v.Not() for v in var2_list]).OnlyEnforceIf(tmp.Not())
        model.Add(sum(var2_list) > 0).OnlyEnforceIf(tmp)
        model.Add(sum(var2_list) == 0).OnlyEnforceIf(tmp.Not())
