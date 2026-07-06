#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/06 10:04
# @Author  : Wu_RH
# @FileName: URB-2Gp.py
"""
[URB-2G'] 环面三连块 (Group')：所有四连通雷区域的面积为 3
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

def urb_neighbors_4(board, pos):
    directions = [
        (1, 0), (0, 1),
        (0, -1), (-1, 0)
    ]

    neighbors = []
    for dr, dc in directions:
        nr = (pos.row + dr) % (board.boundary(pos.board_key).row + 1)
        nc = (pos.col + dc) % (board.boundary(pos.board_key).col + 1)
        neighbors.append(board.get_pos(nr, nc, pos.board_key))

    return neighbors


class Rule2Gp(AbstractMinesRule):
    id = "URB-2G'"
    name = "URB-Group'"
    name.zh_CN = "环面三连块"
    doc = "All torus four-connected mine areas have an area of 3"
    doc.zh_CN = "所有环面四连通雷区域的面积为3"

    tags = ["Variant", "Global", "Connectivity", "Construction"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            nei = board.batch(urb_neighbors_4(board, pos), mode="variable", drop_none=True)
            model.Add(sum(nei) < 3).OnlyEnforceIf([var, s])
            model.Add(sum(nei) > 0).OnlyEnforceIf([var, s])
            tmp = model.NewBoolVar("tmp")
            model.Add(sum(nei) == 2).OnlyEnforceIf([tmp, s])
            model.Add(sum(nei) != 2).OnlyEnforceIf([tmp.Not(), s])
            for _pos in urb_neighbors_4(board, pos):
                if not board.is_valid(_pos):
                    continue
                _var = board.get_variable(_pos)
                nei = board.batch(urb_neighbors_4(board, _pos), mode="variable", drop_none=True)
                model.Add(sum(nei) == 1).OnlyEnforceIf([_var, var, tmp, s])
                model.Add(sum(nei) == 2).OnlyEnforceIf([_var, var, tmp.Not(), s])

    def suggest_total(self, info: dict):
        def hard_constraint(m, total):
            m.AddModuloEquality(0, total, 3)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.335, 0)
        info["hard_fns"].append(hard_constraint)
