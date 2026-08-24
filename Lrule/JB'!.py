#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/24 19:32
# @Author  : Wu_RH
# @FileName: JB'!.py
"""
[JB'!] 唯一格调：每个雷格恰好属于一个格调，格调之间不共享任何格子
"""

from dataclasses import dataclass
from typing import List, Tuple
from collections import defaultdict

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


@dataclass(frozen=True)
class Pattern:
    rot: int
    a_rel: Tuple[Tuple[int, int], ...]
    b_rel: Tuple[Tuple[int, int], ...]


TEMPLATES: List[Pattern] = [
    Pattern(0, ((0, 1), (1, 1)), ((2, 0), (2, 2))),
    Pattern(1, ((1, 1), (1, 2)), ((0, 0), (2, 0))),
    Pattern(2, ((1, 1), (2, 1)), ((0, 0), (0, 2))),
    Pattern(3, ((1, 0), (1, 1)), ((0, 2), (2, 2))),
]


class RuleJBpBang(AbstractMinesRule):
    id = "JB'!"
    name = "Only Dick"
    name.zh_CN = "纯几把"
    doc = "Each mine belongs to exactly one pattern; patterns cannot share any cell."
    doc.zh_CN = "每个雷格恰好属于一个格调，格调之间不能共享任何格子。"
    author = ("雾", 3140864122)
    tags = ["Variant", "Global", "Construction", "Strong"]
    creation_time = "2026-08-24"

    def create_constraints(self, board: Board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            max_x = boundary.row
            max_y = boundary.col
            if max_x < 2 or max_y < 2:
                continue

            # 记录每个格子被哪些格调变量覆盖（不限角色）
            cover_by_cell = defaultdict(list)
            # 记录每个格调变量及其覆盖的位置列表，用于施加 implication
            pattern_info = []

            for ox in range(max_x - 1):
                for oy in range(max_y - 1):
                    for rot, pat in enumerate(TEMPLATES):
                        var = model.NewBoolVar(f"jbp_{key}_{ox}_{oy}_{rot}")
                        positions = []

                        # A 格
                        for dx, dy in pat.a_rel:
                            px, py = ox + dx, oy + dy
                            pos = board.get_pos(px, py, key=key)
                            cover_by_cell[(px, py)].append(var)
                            positions.append(pos)

                        # B 格
                        for dx, dy in pat.b_rel:
                            px, py = ox + dx, oy + dy
                            pos = board.get_pos(px, py, key=key)
                            cover_by_cell[(px, py)].append(var)
                            positions.append(pos)

                        pattern_info.append((var, positions))

            # 1) 格调活跃 => 其所有格子为雷
            for var, positions in pattern_info:
                for pos in positions:
                    mine_var = board.get_variable(pos)
                    model.AddImplication(var, mine_var).OnlyEnforceIf(s)

            # 2) 每个格子的覆盖数 == 雷变量（0 或 1）
            for x in range(max_x + 1):
                for y in range(max_y + 1):
                    covers = cover_by_cell.get((x, y), [])
                    pos = board.get_pos(x, y, key=key)
                    mine_var = board.get_variable(pos)
                    if covers:
                        model.Add(sum(covers) == mine_var).OnlyEnforceIf(s)
                    else:
                        # 没有任何格调能覆盖该格子 => 必须非雷
                        model.Add(mine_var == 0).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        # 可选项：提示总雷数应为 4 的倍数（因为每个格调提供 4 雷）
        def hard_constraint(m, total):
            m.AddModuloEquality(0, total, 4)

        info["hard_fns"].append(hard_constraint)
