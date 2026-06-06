#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/28 12:39
# @Author  : Wu_RH
# @FileName: 4T.py
"""
[*3T]:雷线索指示包含自身的雷三连数量。雷三连允许部分重合
"""
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Position, Board

COUNT = 0


class Rule4T(AbstractMinesClueRule):
    id = "*3T"
    name = "Triple-Mine"
    name.zh_CN = "雷三连"
    doc = "Mines clue indicates the number of mine triples containing it; mine triples can overlap partially"
    doc.zh_CN = "雷线索指示包含自身的雷三连数量。雷三连允许部分重合"
    tags = ["Creative", "Local", "Extensive Trial"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for _pos, _ in board("F"):
            board.set_value(_pos, Value4T(_pos))
        for _pos, _ in board("F"):
            positions = [
                [_pos, _pos.left(), _pos.left(2)],
                [_pos, _pos.down(), _pos.down(2)],
                [_pos, _pos.left().down(), _pos.left(2).down(2)],
                [_pos, _pos.right().down(), _pos.right(2).down(2)],
            ]
            for poses in positions:
                if board.batch(poses, "type").count("F") != 3:
                    continue
                for pos in poses:
                    board[pos].value.value += 1
        return board

    def create_constraints(self, board: 'Board', switch):
        global COUNT
        COUNT += 1
        model = board.get_model()
        c_map = {}
        r_map = {}
        d1_map = {}
        d2_map = {}
        map_list = [c_map, r_map, d1_map, d2_map]
        for _pos, _ in board():
            positions = [
                [_pos, _pos.left(), _pos.left(2)],
                [_pos, _pos.down(), _pos.down(2)],
                [_pos, _pos.left().down(), _pos.left(2).down(2)],
                [_pos, _pos.right().down(), _pos.right(2).down(2)],
            ]
            for i in range(4):
                var_list = board.batch(positions[i], "variable")
                if any(v is None for v in var_list):
                    continue
                t = model.NewBoolVar("[*3T]")
                model.Add(sum(var_list) == 3).OnlyEnforceIf(t)
                model.Add(sum(var_list) < 3).OnlyEnforceIf(t.Not())
                map_list[i][_pos] = t

        for _pos, obj in board("F", mode="obj"):
            if type(obj) is not Value4T:
                continue
            positions = [
                [_pos, _pos.right(), _pos.right(2)],
                [_pos, _pos.up(), _pos.up(2)],
                [_pos, _pos.right().up(), _pos.right(2).up(2)],
                [_pos, _pos.left().up(), _pos.left(2).up(2)],
            ]
            var_list = []
            for i in range(4):
                for pos in positions[i]:
                    if pos not in map_list[i]:
                        continue
                    var_list.append(map_list[i][pos])
            obj.create_constraints_(model, var_list, switch.get(model, obj))


class Value4T(AbstractMinesValue):
    id = "4T"
    def __init__(self, pos: 'Position', code: bytes = None):
        self.pos = pos

        self.value = SingleIntValue(code[0] if code else 0, is_mine=True)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        value = SingleIntValue.try_from(_data)

        if value is None:
            raise ValueError()

        return cls(pos, code=bytes([value.value]))

    def create_constraints_(self, model, var_list: list, s):
        model.Add(sum(var_list) == self.value.value).OnlyEnforceIf(s)
