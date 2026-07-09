#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/08 06:30
# @Author  : Wu_RH
# @FileName: 1O.py
"""
[1O] 外部 (Outside)：非雷区域四连通；每个雷区域以四连通连接到题版边界
"""
from typing import List, Tuple, Dict

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.board import Board
from .connect import connect_legacy as connect


def pos2edge(pos: Position, face: int, board: Board) -> Tuple[int, int]:
    """
    获取pos的指定面朝情况下的两个格点id
    face: 0up, 1left, 2right, 3down
    """
    row, col = pos.row, pos.col
    col_count = board.boundary(pos.board_key).col + 2
    offset_a = (1 - face % 2) * 2 + face // 2
    offset_b = offset_a if offset_a < face else face
    offset_a = offset_a if offset_a > face else face
    point_a = (col + (offset_a // 2)) + (row + (offset_a % 2)) * col_count
    point_b = (col + (offset_b // 2)) + (row + (offset_b % 2)) * col_count
    return (point_a, point_b) if point_a < point_b else (point_b, point_a)


class Rule1O(AbstractMinesRule):
    id = "1O"
    aliases = ("O",)
    name = "Outside"
    name.zh_CN = "外部"
    doc = "Non-mine areas are four-connected; each mine area is connected to the board boundary via four-connection."
    doc.zh_CN = "非雷区域四连通；每个雷区域以四连通连接到题版边界"
    tags = ["Original", "Connectivity", "Global", "Construction"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch(model, self)

        def get_var(input_pos: Position):
            pos_bound = board.boundary(key)
            row, col = input_pos.row, input_pos.col
            if row == -1 or row == pos_bound.row + 1:
                return 1
            if col == -1 or col == pos_bound.col + 1:
                return 1
            return board.get_variable(input_pos)

        for key in board.get_board_keys():
            arcs: Dict[Tuple[int, int], IntVar] = {}
            for pos, _ in board(key=key):
                for face in range(4):
                    edge = pos2edge(pos, face, board)
                    if edge in arcs:
                        continue
                    side = ['up', 'left', 'right', 'down'][face]
                    side_pos = getattr(pos, side)(1)
                    side_var = get_var(side_pos)
                    edge0_var = model.new_bool_var(f"{pos} {side} 0")
                    edge1_var = model.new_bool_var(f"{pos} {side} 1")
                    arcs[edge] = edge0_var
                    arcs[(edge[1], edge[0])] = edge1_var
                    pos_var = board.get_variable(pos)
                    model.add(pos_var == side_var).only_enforce_if(
                        edge0_var.Not(), edge1_var.Not(), s
                    )
                    model.add(pos_var != side_var).only_enforce_if(edge1_var, s)
                    model.add(pos_var != side_var).only_enforce_if(edge0_var, s)
            pos_bound = board.boundary(key)
            for point_id in range((pos_bound.col + 2) * (pos_bound.row + 2)):
                arcs[(point_id, point_id)] = model.new_bool_var(f"point: {point_id} self edge")
            model.add_circuit([(key[0], key[1], var) for key, var in arcs.items()]).only_enforce_if(s)
