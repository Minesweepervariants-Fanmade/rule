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
    doc.zh_CN = "所有雷构成若干条从左至右的链, 链是一组从题板左侧连接到右侧且只能斜向相连的雷"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            id_vars = {pos: model.new_bool_var(f"{pos}_id") for pos in board(mode="pos")}
            for pos, pos_var in board(mode="var", key=key):
                pos_id = id_vars[pos]
                col_pos = col(pos, board)
                col_id = [id_vars[_pos] for _pos in col_pos]
                col_var = [board.get_variable(_pos) for _pos in col_pos]
                right_pos = right(pos, board)
                right_id = [id_vars[_pos] for _pos in right_pos]
                right_var = [board.get_variable(_pos) for _pos in right_pos]
                left_pos = left(pos, board)
                left_id = [id_vars[_pos] for _pos in left_pos]
                left_var = [board.get_variable(_pos) for _pos in left_pos]
                for _col_id, _col_var in zip(col_id, col_var):
                    model.add(_col_id != pos_id).only_enforce_if(_col_var, pos_var, s)
                for side_id, side_var in [(right_id, right_var), (left_id, left_var)]:
                    if len(side_id) == 2:
                        model.add_bool_or(side_var).only_enforce_if(pos_var, s)
                        model.add(pos_id == side_id[0]).only_enforce_if(pos_var, side_var[0], side_var[1].Not(), s)
                        model.add(pos_id == side_id[1]).only_enforce_if(pos_var, side_var[0].Not(), side_var[1], s)
                        model.add(side_id[0] != side_id[1]).only_enforce_if([pos_var, s] + side_var)
                    if len(side_id) == 1:
                        model.add(side_var[0] == 1).only_enforce_if(pos_var, s)
                        model.add(side_id[0] == pos_id).only_enforce_if(pos_var, s)

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
