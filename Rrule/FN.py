#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/26 16:44
# @Author  : Wu_RH
# @FileName: FN.py
from typing import Union

from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.abs.board import AbstractBoard, JSONObject, ImmutableDict, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import VALUE_QUESS


class RuleFN(AbstractClueRule):
    id = "FN"
    name = "FloatNumber"
    name.zh_CN = "浮数"
    doc = "For each cell, displayed +N/-N = (8-neighbor mines) − (unfixed global standard value (range: [0-8]))."
    doc.zh_CN = "周围八格的雷数被一个全局的标准值进行做差 标准值不固定(范围0-8) 所显示的数字表示为+N或-N 与标准值运算后得到实际雷值"
    tags = ['Creative', 'Global', 'Mine-Counting']
    author = ("雾", 3140864122)
    creation_time = "2026-05-26 16:37:56"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        sum_num = 0
        len_num = 0
        for pos, _ in board("N", mode="none"):
            if None in board.batch(pos.neighbors(1), "dye"):
                continue
            sum_num += board.batch(pos.neighbors(2), "type").count("F")
            len_num += 1
        avg_num = int(sum_num / len_num)
        for pos, _ in board("N", mode="none"):
            if None in board.batch(pos.neighbors(1), "dye"):
                # board[pos] = VALUE_QUESS
                continue
            value = board.batch(pos.neighbors(2), "type").count("F") - avg_num
            obj = ValueFN.from_json(pos, {"value": value})
            board[pos] = obj
        return board

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        global_var = model.new_int_var(0, 8, "global")
        for pos, obj in board(mode="obj"):
            if not isinstance(obj, ValueFN):
                continue
            s = switch.get(model, obj)
            model.add(
                sum(
                    board.batch(pos.neighbors(2), "var", drop_none=True)
                ) == global_var + obj.value
            ).only_enforce_if(s)


class ValueFN(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', value: int) -> None:
        super().__init__(pos)
        self.value = value

    def __repr__(self) -> str:
        return ("+" + str(self.value)) if self.value > 0 else str(self.value)

    @classmethod
    def from_json(cls, pos: 'AbstractPosition', data: Union['JSONObject', dict]) -> 'ValueFN':
        return ValueFN(pos, data["value"])

    def json(self) -> 'JSONObject':
        return ImmutableDict({"value": self.value})

    @classmethod
    def type(cls) -> bytes:
        return RuleFN.id.encode("ascii")
