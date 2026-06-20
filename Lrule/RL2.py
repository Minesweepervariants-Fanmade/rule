#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/06/20 19:37
# @Author  : Wu_RH
# @FileName: RL2.py
from typing import List, Optional

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position import Position
from minesweepervariants.size import Size

NAME_RL2 = "RL2"


def get_block(pos: Position, board: Board) -> Optional[List[Position]]:
    positions = [
        board.get_pos(pos.row + i, pos.col + j, pos.board_key)
        for i, j in [(0, 0), (0, 1), (1, 0), (1, 1)]
    ]
    if None in positions:
        return None
    return positions


class RuleRL2(AbstractMinesRule):
    id = "RL2"
    name = "Rule2"
    name.zh_CN = "规则2"
    doc = ("For every 2x2 sub-board, the arrangement of mines inside it is uniquely determined by the total number of "
           "mines in that sub-board; hence any two 2x2 areas with the same mine count must have identical mine "
           "patterns.")
    doc.zh_CN = "对于任意2x2区域，其内部雷的排布仅由该区域雷总数决定；因此，雷总数相同的所有2x2区域内部雷分布必须相同。"
    tags = ["Local", "Strict Shape", "Mine-Counting"]
    creation_time = "2026-06-20"
    author = ("雾", 3140864122)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        self.num = 1
        self.flag = False
        if data is None:
            data = "1"
        if "!" in data:
            data = data.replace("!", "")
            self.flag = True
            if not data:
                data = "1"
        if data.isdigit():
            self.num = int(data)
        else:
            raise ValueError("参数输入为数字(!),代表允许的可能性数量(不排除可能性为相同的情况), +!代表禁止0/4")
        if self.num == 0:
            raise ValueError("不应该为0个可能性")
        board.generate_board(NAME_RL2, size=Size(self.num * 2, 6))

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        blocks_var = []
        for index in range(3):
            blocks_var.append([
                board.batch(
                    get_block(board.get_pos(
                        index * 2, n * 2, NAME_RL2
                    ), board),
                    mode="var"
                )
                for n in range(self.num)
            ])
        for pos, _ in board():
            pos_block = get_block(pos, board)
            if pos_block is None:
                continue
            pos_block_var = board.batch(pos_block, mode="var")
            sum_var = sum(pos_block_var)
            switch_sums = [model.new_bool_var("") for _ in range(3)]
            if self.flag:
                model.add(sum_var != 0).only_enforce_if(s)
                model.add(sum_var != 4).only_enforce_if(s)
            for index in range(1, 4):
                switch_sum = switch_sums[index - 1]
                model.add(sum_var == index).only_enforce_if(switch_sum, s)
                model.add(sum_var != index).only_enforce_if(switch_sum.Not(), s)
                block_vars = blocks_var[index - 1]
                tmps_var = [model.new_bool_var("") for _ in range(self.num)]
                for n in range(self.num):
                    for var_a, var_b in zip(block_vars[n], pos_block_var):
                        model.add(var_a == var_b).only_enforce_if(switch_sum, s, tmps_var[n])
                model.add_bool_or(tmps_var).only_enforce_if(s)

    def init_clear(self, board: 'Board') -> None:
        for pos, _ in board(key=NAME_RL2):
            board[pos] = None
