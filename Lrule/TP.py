#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[TP] 三分：每行恰好分成三个连续区域（雷-非雷-雷 或 非雷-雷-非雷），每段至少一格
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from ....impl.summon.solver import Switch


class RuleTP(AbstractMinesRule):
    id = "TP"
    name = "TripleSegment"
    name.zh_CN = "三分"
    doc = "Each row is divided into exactly three contiguous segments (Mine-NonMine-Mine or NonMine-Mine-NonMine), each segment at least one cell"
    doc.zh_CN = "每行恰好分成三个连续区域（雷-非雷-雷 或 非雷-雷-非雷），每段至少一格"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-05-13"

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            d_pos = board.boundary(key)
            for pos in board.get_col_pos(d_pos):
                line = board.get_row_pos(pos)
                line_var = board.batch(line, mode="variable")
                n = len(line_var)
                if n == 0:
                    continue

                # boundaries[i] == 1 iff line_var[i] != line_var[i+1]
                # Total boundaries count = number of type changes in the row
                # For 3 segments: exactly 2 boundaries
                # For all-non-mine (all zeros): 0 boundaries (also exactly 1 segment of zeros)
                boundaries = []
                for i in range(n - 1):
                    b = model.NewBoolVar(f"{self.id}_{key}_{pos.y}_b_{i}")
                    boundaries.append(b)
                    cur = line_var[i]
                    nxt = line_var[i + 1]
                    # b == 1 iff cur != nxt, linearize: b = cur XOR nxt
                    # b >= cur - nxt
                    model.Add(b >= cur - nxt).OnlyEnforceIf(s)
                    # b >= nxt - cur
                    model.Add(b >= nxt - cur).OnlyEnforceIf(s)
                    # b <= cur + nxt
                    model.Add(b <= cur + nxt).OnlyEnforceIf(s)
                    # b <= 2 - cur - nxt
                    model.Add(b <= 2 - cur - nxt).OnlyEnforceIf(s)

                # For every row: exactly 2 boundaries (3 segments)
                model.Add(sum(boundaries) == 2).OnlyEnforceIf(s)
