#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/21 05:57
# @Author  : Wu_RH
# @FileName: CCB.py
"""
[CB]连击（Combo）: 雷线索指示四方向的连击总值和，同方向相邻的n个雷连击值为1-n.例：FXFFFXX这一支连击总值为7
"""
from minesweepervariants.abs.Mrule import AbstractMinesValue, AbstractMinesClueRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch


class RuleCB(AbstractMinesClueRule):
    name = ["CB", "CCB", "连击"]
    doc = "雷线索指示四方向的连击总值和，同方向相邻的n个雷连击值为1-n"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, obj in board("F"):
            col = board.get_col_pos(pos)
            row = board.get_row_pos(pos)
            col1, col2 = col[:col.index(pos)][::-1], col[col.index(pos)+1:]
            row1, row2 = row[:row.index(pos)][::-1], row[row.index(pos)+1:]
            value = 0
            for line in [row1, row2, col1, col2]:
                line = [t == "F" for t in board.batch(line, mode="type")]
                tmp = 0
                for b in line:
                    if b:
                        tmp += 1
                        value += tmp
                    else:
                        tmp = 0
            obj = ValueCB(pos, bytes([value]))
            board[pos] = obj
        return board


class ValueCB(AbstractMinesValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        self.pos = pos
        self.value = code[0]

    def __repr__(self):
        return str(self.value)

    def code(self) -> bytes:
        return bytes([self.value])

    @classmethod
    def type(cls) -> bytes:
        return RuleCB.name[0].encode()

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        col = board.get_col_pos(self.pos)
        row = board.get_row_pos(self.pos)

        col1, col2 = col[:col.index(self.pos)], col[col.index(self.pos) + 1:]
        row1, row2 = row[:row.index(self.pos)], row[row.index(self.pos) + 1:]

        var_list = []
        for pos_line in [col1, col2, row1, row2]:
            if not pos_line:
                continue
            var_line = board.batch(pos_line, mode="var")
            type_line = board.batch(pos_line, mode="type")
            for i in range(1, len(pos_line)+1):
                for index in range(len(pos_line) - i + 1):
                    tmp_var_line = var_line[index:index+i]
                    tmp_type_line = type_line[index:index+i]
                    if any(v is None for v in tmp_var_line):
                        continue
                    if "C" in tmp_type_line:
                        continue
                    tmp_bool_var = model.NewBoolVar(f"{pos_line[index]}:{pos_line[index+i-1]}")
                    for v in tmp_var_line:
                        model.Add(tmp_bool_var == 0).OnlyEnforceIf(v.Not())
                    model.Add(tmp_bool_var == 1).OnlyEnforceIf(tmp_var_line)
                    var_list.append(tmp_bool_var)
        model.Add(sum(var_list) == self.value).OnlyEnforceIf(s)
