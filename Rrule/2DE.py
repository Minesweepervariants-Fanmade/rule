#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/30 18:26
# @Author  : Wu_RH
# @FileName: 2DE.py
from typing import List, Callable, Optional

from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.board import Board, Position, JSONObject, ImmutableDict
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger


class Rule2DE(AbstractClueRule):
    id = "2DE"
    name = "spread"
    name.zh_CN = "扩散"
    doc = ("The clue indicates that the area within its rectangular grid expands in four directions until it "
           "encounters a mine within the mine's range.")
    doc.zh_CN = "线索表示其所在格矩形范围向四方向扩展直到遇到雷范围内的雷数"
    tags = ['Variant', 'Number Clue', 'Mine-Counting']
    author = ("NT", 2201963934)
    creation_time = "2026-04-29 23:33:04"

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            indexs = []
            for fc in [pos.up, pos.down, pos.right, pos.left]:
                fc: Callable[[int], Optional[Position]]
                index = 1
                _pos = fc(index)
                while _pos is not None and board.is_valid(_pos):
                    if board.get_type(_pos) == "F":
                        break
                    index += 1
                    _pos = fc(index)
                indexs.append(index)
            value = 0
            nei = []
            for dx in range(1 - indexs[0], indexs[1]):
                for dy in range(1 - indexs[3], indexs[2]):
                    nei.append((dy, dx))
            nei = [pos.shift(*s) for s in nei]
            value = board.batch(nei, mode='type').count('F')
            board[pos] = Value2DE(pos, value)
        return board


class Value2DE(AbstractClueValue):
    id = Rule2DE.id
    def __init__(self, pos: 'Position', value: int, *args, **kwargs) -> None:
        super().__init__(pos, *args, **kwargs)
        self.value = value

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        return cls(pos, value=data["value"])

    def json(self) -> 'JSONObject':
        return ImmutableDict({"value": self.value})

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        col = board.get_col_pos(self.pos)
        row = board.get_row_pos(self.pos)

        map_var_list = []
        for pos, var in board(mode="var"):
            if pos in col + row:
                continue
            map_var = model.new_bool_var("")
            map_var_list.append(map_var)
            pos_list = list(set(
                col[pos.row:self.pos.row + 1] +
                col[self.pos.row:pos.row + 1] +
                row[pos.col:self.pos.col + 1] +
                row[self.pos.col:pos.col + 1]
            ))
            var_list = board.batch(pos_list, "var")
            model.add(map_var == var).OnlyEnforceIf([_var.Not() for _var in var_list] + [s])
            for _var in var_list:
                model.add(map_var == 0).OnlyEnforceIf(_var)
        model.add(self.value == sum(map_var_list)).OnlyEnforceIf(s)
