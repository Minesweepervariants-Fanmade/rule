#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/28 12:39
# @Author  : Wu_RH
# @FileName: 4T.py
"""
[*3T]:雷线索指示包含自身的雷三连数量。雷三连允许部分重合
"""
from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractPosition, AbstractBoard

COUNT = 0


class Rule4T(AbstractMinesClueRule):
    name = ["*3T", "雷三连"]
    doc = "雷线索指示包含自身的雷三连数量。雷三连允许部分重合"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
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
                    board[pos].value += 1
        return board

    def create_constraints(self, board: 'AbstractBoard', switch):
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

        for _pos, obj in board("F"):
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
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        self.value = code[0] if code else 0
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    def code(self) -> bytes:
        return bytes([self.value])

    @classmethod
    def type(cls) -> bytes:
        return Rule4T.name[0].encode("ascii")

    def create_constraints_(self, model, var_list: list, s):
        model.Add(sum(var_list) == self.value).OnlyEnforceIf(s)
