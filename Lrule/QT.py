#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-07-21 13:18:13
# @Author  : 小中医 (3086842243)
# @FileName: QT.py
"""
[QT] 三连框 (Triple Box): 题板上每个完整的 3x3 方框内，至少存在一条横线、竖线
或对角线，其上的三个格子全部是雷。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.position import Position

if TYPE_CHECKING:
    from minesweepervariants.board import Board
    from minesweepervariants.impl.summon.solver import Switch


# 3x3 方框内 8 条长度为 3 的线，每个元素是 (行偏移, 列偏移)。
_LINES: Tuple[Tuple[Tuple[int, int], ...], ...] = (
    # 横向
    ((0, 0), (0, 1), (0, 2)),
    ((1, 0), (1, 1), (1, 2)),
    ((2, 0), (2, 1), (2, 2)),
    # 纵向
    ((0, 0), (1, 0), (2, 0)),
    ((0, 1), (1, 1), (2, 1)),
    ((0, 2), (1, 2), (2, 2)),
    # 两条对角线
    ((0, 0), (1, 1), (2, 2)),
    ((0, 2), (1, 1), (2, 0)),
)


class RuleQT(AbstractMinesRule):
    id = "QT"
    name = "Triple Box"
    name.zh_CN = "三连框"
    doc = (
        "Every complete 3x3 box on the board must contain three mines in a row, "
        "in a column, or on a diagonal."
    )
    doc.zh_CN = "每个3*3框至少有横竖斜的其中一组三连雷。"
    author = ("小中医", 3086842243)
    tags = ["Original", "Local", "Mine-Position", "Construction"]
    creation_time = "2026-07-21 13:18:13"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            rows = bound.row + 1
            cols = bound.col + 1
            if rows < 3 or cols < 3:
                continue

            # 枚举所有完整位于题板内的 3x3 方框。
            for top in range(rows - 2):
                for left in range(cols - 2):
                    window = [
                        Position(left + dc, top + dr, key)
                        for dr in range(3)
                        for dc in range(3)
                    ]
                    if not all(board.is_valid(pos) for pos in window):
                        continue

                    line_vars = []
                    for line_index, line in enumerate(_LINES):
                        cell_vars = [
                            board.get_variable(
                                Position(left + dc, top + dr, key),
                                special="raw",
                            )
                            for dr, dc in line
                        ]
                        if any(var is None for var in cell_vars):
                            continue

                        # line_var 当且仅当该线上的三格全部为雷。
                        line_var = model.new_bool_var(
                            f"QT_{key}_{top}_{left}_{line_index}"
                        )
                        model.add_bool_and(cell_vars).only_enforce_if(
                            line_var, rule_switch
                        )
                        model.add_bool_or(
                            [var.Not() for var in cell_vars]
                        ).only_enforce_if(line_var.Not(), rule_switch)
                        line_vars.append(line_var)

                    # 每个 3x3 方框至少有一条三连雷线。
                    if line_vars:
                        model.add_bool_or(line_vars).only_enforce_if(rule_switch)
