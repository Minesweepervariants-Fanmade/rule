#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/29 01:46
# @Author  : Wu_RH
# @FileName: 2B'.py
from typing import Optional, List

from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position import Position

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


def left(pos: Position, board: Board) -> List[Position]:
    return [
        _pos for _pos in [
            pos.left().up(),
            pos.left().down()
        ] if board.is_valid(_pos)
    ]

def right(pos: Position, board: Board) -> List[Position]:
    return [
        _pos for _pos in [
            pos.right().up(),
            pos.right().down()
        ] if board.is_valid(_pos)
    ]

def col(pos: Position, board: Board) -> List[Position]:
    return [
        _pos for _pos in [
            pos.up().up(),
            pos.down().down()
        ] if board.is_valid(_pos)
    ]


class Rule2B(AbstractMinesRule):
    id = "2B'"
    name = "Diagonally Bridge"
    name.zh_CN = "斜桥"
    doc = ("All the mines form several chains from left to right, with each chain connecting a group of mines "
           "diagonally from the left side of the board to the right.")
    doc.zh_CN = "所有雷构成若干条从左至右的链, 链式一组从题板左侧连接到右侧斜线相连的雷"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, var in board(mode="var", key=key):
                left_var = board.batch(left(pos, board), mode="var")
                right_var = board.batch(right(pos, board), mode="var")
                col_var = board.batch(col(pos, board), mode="var")
                if left_var:
                    model.add_bool_or(left_var).OnlyEnforceIf(s, var)
                if len(left_var) > 1:
                    model.add_bool_or(col_var).OnlyEnforceIf(
                        [s, var] + left_var
                    )
                if right_var:
                    model.add_bool_or(right_var).OnlyEnforceIf(s, var)
                if len(right_var) > 1:
                    model.add_bool_or(col_var).OnlyEnforceIf(
                        [s, var] + right_var
                    )
            main_col_sum = None
            for pos in board.get_row_pos(board.boundary(key)):
                col_sum_var = board.batch(board.get_col_pos(pos), mode="var")
                if main_col_sum:
                    model.add(sum(main_col_sum) == sum(col_sum_var)).OnlyEnforceIf(s)
                else:
                    main_col_sum = col_sum_var

    def suggest_total(self, info: dict):
        size_list = [info["size"][key] for key in info["interactive"]]

        def a(model, total):
            nonlocal size_list
            var_list = []
            for i, (height, width) in enumerate(size_list):
                n = model.NewIntVar(0, height * width, f"width_{i}")
                model.AddModuloEquality(0, n, width)
                var_list.append(n)
            model.Add(sum(var_list) == total)

        info["hard_fns"].append(a)
