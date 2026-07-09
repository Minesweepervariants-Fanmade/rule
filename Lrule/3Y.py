#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/18 14:01
# @Author  : Wu_RH
# @FileName: 3I.py
"""
[3Y]阴阳(Yin-Yang):所有雷四连通，所有非雷四连通，不存在2*2的雷或非雷
"""
from typing import List, Tuple, Dict

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from .connect import connect


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


class Rule3Y(AbstractMinesRule):
    id = "3Y"
    name = "Yin-Yang"
    name.zh_CN = "阴阳"
    doc = ("All mines are orthogonally connected, all non-mines are orthogonally connected, no 2x2 block of mines or "
           "non-mines exists")
    doc.zh_CN = "所有雷四连通，所有非雷四连通，不存在2*2的雷或非雷"
    tags = ["Creative", "Global", "Connectivity", "Anti-Construction"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_board_keys():
            arcs: Dict[Tuple[int, int], IntVar] = {}
            for pos, _ in board(key=key):
                for face in range(4):
                    edge = pos2edge(pos, face, board)
                    if edge in arcs:
                        continue
                    side = ['up', 'left', 'right', 'down'][face]
                    side_pos = getattr(pos, side)(1)
                    if not board.is_valid(side_pos):
                        continue
                    edge0_var = model.new_bool_var(f"{pos} {side} 0")
                    edge1_var = model.new_bool_var(f"{pos} {side} 1")
                    arcs[edge] = edge0_var
                    arcs[(edge[1], edge[0])] = edge1_var
                    side_var = board.get_variable(side_pos)
                    pos_var = board.get_variable(pos)
                    model.add(pos_var == side_var).only_enforce_if(
                        edge0_var.Not(), edge1_var.Not(), s
                    )
                    model.add(pos_var != side_var).only_enforce_if(edge1_var, s)
                    model.add(pos_var != side_var).only_enforce_if(edge0_var, s)
            pos_bound = board.boundary(key)
            root_point = (pos_bound.col + 2) * (pos_bound.row + 2)
            arcs[(root_point, root_point)] = model.new_bool_var("root self edge")
            for point_id in range(1, pos_bound.col + 1):
                arcs[(point_id, root_point)] = model.new_bool_var(f"point: {point_id} root edge")
                arcs[(root_point, point_id)] = model.new_bool_var(f"point: {point_id} edge root")
                arcs[(point_id, point_id)] = model.new_bool_var(f"point: {point_id} edge self")
                point_id += (pos_bound.col + 2) * (pos_bound.row + 1)
                arcs[(point_id, root_point)] = model.new_bool_var(f"point: {point_id} root edge")
                arcs[(root_point, point_id)] = model.new_bool_var(f"point: {point_id} edge root")
                arcs[(point_id, point_id)] = model.new_bool_var(f"point: {point_id} edge self")
            for point_id in range(pos_bound.col + 2, (pos_bound.col + 2) * (pos_bound.row + 1), pos_bound.col + 2):
                arcs[(point_id, root_point)] = model.new_bool_var(f"point: {point_id} root edge")
                arcs[(root_point, point_id)] = model.new_bool_var(f"point: {point_id} edge root")
                arcs[(point_id, point_id)] = model.new_bool_var(f"point: {point_id} edge self")
                point_id += pos_bound.col + 1
                arcs[(point_id, root_point)] = model.new_bool_var(f"point: {point_id} root edge")
                arcs[(root_point, point_id)] = model.new_bool_var(f"point: {point_id} edge root")
                arcs[(point_id, point_id)] = model.new_bool_var(f"point: {point_id} edge self")
            model.add_circuit([(key[0], key[1], var) for key, var in arcs.items()]).only_enforce_if(s)

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            size = info["size"][key]
            ub += size[0] * size[1]
        info["soft_fn"](ub * 0.5, 0)
