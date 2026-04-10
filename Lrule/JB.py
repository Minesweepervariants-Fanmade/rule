#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[JB] 格调
作者: NT (2201963934)
最后编辑时间: 2026-04-08 15:57:01

每组恰好由 1 个非方形矩形和 2 个方形矩形组成；非方形短边的两个端点分别与两个方形矩形发生一次对角接触；组间完全不接触。
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition


TL = 0
TR = 1
BL = 2
BR = 3


@dataclass(frozen=True)
class RectTemplate:
    x1: int
    x2: int
    y1: int
    y2: int
    cells: tuple[AbstractPosition, ...]
    square: bool

    @property
    def width(self) -> int:
        return self.y2 - self.y1 + 1

    @property
    def height(self) -> int:
        return self.x2 - self.x1 + 1


def _build_templates(board: AbstractBoard, key: str) -> List[RectTemplate]:
    boundary = board.boundary(key=key)
    max_x = boundary.x
    max_y = boundary.y
    templates: List[RectTemplate] = []

    for x1 in range(max_x + 1):
        for x2 in range(x1, max_x + 1):
            for y1 in range(max_y + 1):
                for y2 in range(y1, max_y + 1):
                    cells = tuple(
                        board.get_pos(x, y, key)
                        for x in range(x1, x2 + 1)
                        for y in range(y1, y2 + 1)
                    )
                    templates.append(
                        RectTemplate(
                            x1=x1,
                            x2=x2,
                            y1=y1,
                            y2=y2,
                            cells=cells,
                            square=(x2 - x1) == (y2 - y1),
                        )
                    )
    return templates


def _overlap(a: RectTemplate, b: RectTemplate) -> bool:
    return not (
        a.x2 < b.x1 or b.x2 < a.x1 or
        a.y2 < b.y1 or b.y2 < a.y1
    )


def _orth_touch(a: RectTemplate, b: RectTemplate) -> bool:
    if a.x2 + 1 == b.x1 or b.x2 + 1 == a.x1:
        return max(a.y1, b.y1) <= min(a.y2, b.y2)
    if a.y2 + 1 == b.y1 or b.y2 + 1 == a.y1:
        return max(a.x1, b.x1) <= min(a.x2, b.x2)
    return False


def _diag_corners(a: RectTemplate, b: RectTemplate) -> Tuple[int, int] | None:
    if a.x2 + 1 == b.x1 and a.y2 + 1 == b.y1:
        return BR, TL
    if a.x2 + 1 == b.x1 and b.y2 + 1 == a.y1:
        return BL, TR
    if b.x2 + 1 == a.x1 and a.y2 + 1 == b.y1:
        return TR, BL
    if b.x2 + 1 == a.x1 and b.y2 + 1 == a.y1:
        return TL, BR
    return None


class RuleJB(AbstractMinesRule):
    name = ["JB", "格调", "Adick"]
    doc = "每组恰好由 1 个非方形矩形和 2 个方形矩形组成；短边两端分别与两个方形矩形对角接触，且组间完全不接触"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            templates = _build_templates(board, key)
            if not templates:
                continue

            active_vars = [model.NewBoolVar(f"jb_active[{key},{i}]") for i in range(len(templates))]
            square_flags = [tpl.square for tpl in templates]

            boundary = board.boundary(key=key)
            cell_cover: Dict[Tuple[int, int], List[int]] = {}
            for idx, tpl in enumerate(templates):
                for pos in tpl.cells:
                    cell_cover.setdefault((pos.x, pos.y), []).append(idx)

            for x in range(boundary.x + 1):
                for y in range(boundary.y + 1):
                    pos = board.get_pos(x, y, key)
                    mine_var = board.get_variable(pos)
                    covering = [active_vars[idx] for idx in cell_cover[(x, y)]]
                    model.Add(sum(covering) == mine_var).OnlyEnforceIf(s)

            diag_neighbors: List[List[int]] = [[] for _ in templates]
            corner_neighbors: List[List[List[int]]] = [[[] for _ in range(4)] for _ in templates]

            for i in range(len(templates)):
                a = templates[i]
                for j in range(i + 1, len(templates)):
                    b = templates[j]
                    if _overlap(a, b):
                        continue
                    if _orth_touch(a, b):
                        model.Add(active_vars[i] + active_vars[j] <= 1).OnlyEnforceIf(s)
                        continue

                    diag = _diag_corners(a, b)
                    if diag is None:
                        continue

                    a_corner, b_corner = diag
                    if square_flags[i] == square_flags[j]:
                        model.Add(active_vars[i] + active_vars[j] <= 1).OnlyEnforceIf(s)
                        continue

                    diag_neighbors[i].append(j)
                    diag_neighbors[j].append(i)
                    corner_neighbors[i][a_corner].append(j)
                    corner_neighbors[j][b_corner].append(i)

            for idx, tpl in enumerate(templates):
                mine_active = active_vars[idx]
                if tpl.square:
                    model.Add(sum(active_vars[j] for j in diag_neighbors[idx]) == 1).OnlyEnforceIf(
                        [mine_active, s]
                    )
                    continue

                if tpl.width > tpl.height:
                    side_left = model.NewBoolVar(f"jb_side_left[{key},{idx}]")
                    side_right = model.NewBoolVar(f"jb_side_right[{key},{idx}]")
                    model.Add(side_left + side_right == 1).OnlyEnforceIf([mine_active, s])
                    side_defs = [
                        (side_left, (TL, BL)),
                        (side_right, (TR, BR)),
                    ]
                else:
                    side_top = model.NewBoolVar(f"jb_side_top[{key},{idx}]")
                    side_bottom = model.NewBoolVar(f"jb_side_bottom[{key},{idx}]")
                    model.Add(side_top + side_bottom == 1).OnlyEnforceIf([mine_active, s])
                    side_defs = [
                        (side_top, (TL, TR)),
                        (side_bottom, (BL, BR)),
                    ]

                model.Add(sum(active_vars[j] for j in diag_neighbors[idx]) == 2).OnlyEnforceIf([
                    mine_active,
                    s,
                ])

                for side_var, (corner_a, corner_b) in side_defs:
                    model.Add(
                        sum(active_vars[j] for j in corner_neighbors[idx][corner_a]) == 1
                    ).OnlyEnforceIf([mine_active, side_var, s])
                    model.Add(
                        sum(active_vars[j] for j in corner_neighbors[idx][corner_b]) == 1
                    ).OnlyEnforceIf([mine_active, side_var, s])

                    for corner in (TL, TR, BL, BR):
                        if corner == corner_a or corner == corner_b:
                            continue
                        model.Add(
                            sum(active_vars[j] for j in corner_neighbors[idx][corner]) == 0
                        ).OnlyEnforceIf([mine_active, side_var, s])
