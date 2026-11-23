#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-11-24 05:51:05
# @Author  : NT (2201963934)
# @FileName: Sc0.py
"""
[Sc0] 无断连：任何3x3范围内雷格都属于同一雷区。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position

if TYPE_CHECKING:
    from ortools.sat.python.cp_model import IntVar
    from minesweepervariants.impl.summon.solver import Switch


class RuleSc0(AbstractMinesRule):
    id = "Sc0"
    name = "No Disconnection"
    name.zh_CN = "无断连"
    doc = (
        "In every 3x3 area, all mine cells belong to the same 4-connected "
        "mine region."
    )
    doc.zh_CN = "无断连：任何3x3范围内雷格都属于同一雷区"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Connectivity", "Global"]
    creation_time = "2026-11-24 05:51:05"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            rows = bound.row + 1
            cols = bound.col + 1
            if rows < 3 or cols < 3:
                continue

            cells: List[Position] = [pos for pos, _ in board(key=key)]
            if len(cells) < 2:
                continue

            mine_vars: Dict[Position, 'IntVar'] = {}
            for pos in cells:
                var = board.get_variable(pos, special='raw')
                if var is not None:
                    mine_vars[pos] = var
            if len(mine_vars) < 2:
                continue

            def add_window_flow(window: List[Position], tag: str) -> None:
                window_vars = [mine_vars[pos] for pos in window]
                if len(window_vars) < 2:
                    return
                capacity = len(window_vars)

                root: Dict[Position, 'IntVar'] = {
                    pos: model.new_bool_var(f"Sc0_{tag}_root_{pos.col}_{pos.row}")
                    for pos in window
                }
                has_target = model.new_bool_var(f"Sc0_{tag}_has_target")
                model.add_max_equality(has_target, window_vars).only_enforce_if(s)
                model.add(sum(root.values()) == has_target).only_enforce_if(s)
                for pos in window:
                    model.add(root[pos] <= mine_vars[pos]).only_enforce_if(s)

                target_count = model.new_int_var(
                    0, capacity, f"Sc0_{tag}_target_count"
                )
                model.add(target_count == sum(window_vars)).only_enforce_if(s)

                supply: Dict[Position, object] = {pos: 0 for pos in cells}
                for pos in window:
                    root_times_count = model.new_int_var(
                        0, capacity,
                        f"Sc0_{tag}_root_count_{pos.col}_{pos.row}",
                    )
                    model.add_multiplication_equality(
                        root_times_count, [root[pos], target_count]
                    ).only_enforce_if(s)
                    supply[pos] = root_times_count - mine_vars[pos]

                flow: Dict[tuple[Position, Position], 'IntVar'] = {}
                for pos in cells:
                    for nxt in pos.neighbors(1):
                        if nxt not in mine_vars:
                            continue
                        f = model.new_int_var(
                            0, capacity,
                            f"Sc0_{tag}_flow_{pos.col}_{pos.row}_{nxt.col}_{nxt.row}",
                        )
                        flow[pos, nxt] = f
                        model.add(
                            f <= capacity * mine_vars[pos]
                        ).only_enforce_if(s)
                        model.add(
                            f <= capacity * mine_vars[nxt]
                        ).only_enforce_if(s)

                for pos in cells:
                    neighbors = [
                        nxt for nxt in pos.neighbors(1) if nxt in mine_vars
                    ]
                    out_flow = sum(flow[pos, nxt] for nxt in neighbors)
                    in_flow = sum(flow[nxt, pos] for nxt in neighbors)
                    model.add(
                        out_flow - in_flow == supply[pos]
                    ).only_enforce_if(s)

            window_index = 0
            for top in range(rows - 2):
                for left in range(cols - 2):
                    window = [
                        Position(left + dc, top + dr, key)
                        for dr in range(3)
                        for dc in range(3)
                        if board.is_valid(Position(left + dc, top + dr, key))
                    ]
                    if len(window) < 2:
                        continue
                    add_window_flow(window, f"{key}_{window_index}")
                    window_index += 1
