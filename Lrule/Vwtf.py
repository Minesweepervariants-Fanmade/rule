#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/27
# @Author  : NT
# @FileName: Vwtf.py
"""
[Vwtf] 均一: 所有非雷格的8-邻域雷数相同
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleVwtf(AbstractMinesRule):
    id = "Vwtf"
    name = "Uniform"
    name.zh_CN = "均一"
    doc = "For all non-mine cells, the mine count in their 8-neighbours is the same"
    doc.zh_CN = "所有非雷格的8-邻域雷数相同"
    tags = ["Variant", "Local", "Anti-Construction"]
    creation_time = "2026-05-27"
    author = ("NT", 0)

    def create_constraints(self, board: "Board", switch):
        model = board.get_model()
        s = switch.get(model, self)

        # Collect all non-mine cells that have all 8 neighbours (i.e., not on boundary)
        interior_non_mines = []
        for pos, var in board(mode="variable"):
            # Check if all 8 neighbours exist (not on boundary)
            neighbours = pos.neighbors(2)  # 8-neighbours
            if len(neighbours) != 8:
                continue  # This cell is on the boundary
            # Only consider non-mine cells
            interior_non_mines.append((pos, var))

        if len(interior_non_mines) < 2:
            return  # Need at least 2 cells to compare

        # Create an equality variable to represent the common mine count
        common_count = model.new_int_var(0, 8, "Vwtf_common_count")

        for pos, var in interior_non_mines:
            neighbours = pos.neighbors(2)
            neighbour_vars = board.batch(neighbours, mode="variable", drop_none=True)
            mine_count = sum(neighbour_vars)

            # If this cell is non-mine (var == 0), then its neighbour mine count must equal common_count
            # Enforce: var == 0 => mine_count == common_count
            model.Add(mine_count == common_count).OnlyEnforceIf([var.Not(), s])
            # Alternative: mine_count is only constrained when var == 0
            # When var == 1 (mine), no constraint on mine_count from this rule
