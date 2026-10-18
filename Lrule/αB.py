#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-03-01 13:28:35
# @Author  : botif (1643337042)
# @FileName: αB.py
"""
[αB] 积木 (Blocks)：
每段横向雷下方相邻格中一定有雷（最下方一行除外）。

等价表述：所有雷都能通过"下、左、右"三个方向在雷格之间移动，最终到达题板下边缘。

证明要点：
- 一段水平连续的雷只能在本段内左右移动（离开段就是非雷格），要向下走必须从段内
  某格的正下方雷进入下一行。因此"每段下方至少有一颗雷" ⇔ "段内存在向下走的通道"。
- 规则递归地作用于下方各段，所以任意雷都能沿行号单调不减地走到最后一行。
  反之，若某段下方没有雷，该段的雷无法向下走也无法上行，只能在本段内左右移动，
  永远无法到达下边缘。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from ortools.sat.python.cp_model import IntVar
    from minesweepervariants.board import Board
    from ....impl.summon.solver import Switch


class RuleAlphaB(AbstractMinesRule):
    id = "αB"
    name = "Blocks"
    name.zh_CN = "积木"
    doc = (
        "Every horizontal segment of mines must have at least one mine directly below it "
        "(the bottom row is excluded)."
    )
    doc.zh_CN = "每段横向雷下方相邻格中一定有雷（最下方一行除外）"
    author = ("botif", 1643337042)
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-03-01"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            rows = bound.row + 1
            cols = bound.col + 1

            pos_map = {(pos.row, pos.col): pos for pos, _ in board(key=key)}

            grid: List[List[Optional[IntVar]]] = [
                [None for _ in range(cols)] for _ in range(rows)
            ]
            for (r, c), pos in pos_map.items():
                if 0 <= r < rows and 0 <= c < cols:
                    grid[r][c] = board.get_variable(pos)

            # aux[r][c] 表示：
            #   从 (r, c) 起（含）沿连续雷向右延伸到某列 j，
            #   使得 (r, c..j) 全为雷且 (r+1, j) 为雷。
            # 递推：aux[r][c] <-> x[r][c] AND ( x[r+1][c] OR (x[r][c+1] AND aux[r][c+1]) )
            aux: List[List[Optional[IntVar]]] = [
                [None for _ in range(cols)] for _ in range(rows)
            ]

            # 最下方一行不参与该规则
            for r in range(rows - 1):
                for c in range(cols - 1, -1, -1):
                    xc = grid[r][c]
                    if xc is None:
                        continue

                    below = grid[r + 1][c]
                    xr = grid[r][c + 1] if c + 1 < cols else None
                    ar = aux[r][c + 1] if c + 1 < cols else None

                    a = model.new_bool_var(f"αB_aux_{key}_{r}_{c}")
                    aux[r][c] = a

                    inner_terms: List[IntVar] = []
                    if below is not None:
                        inner_terms.append(below)
                    if xr is not None and ar is not None:
                        t = model.new_bool_var(f"αB_and_{key}_{r}_{c}")
                        model.add(t <= xr).only_enforce_if(s)
                        model.add(t <= ar).only_enforce_if(s)
                        model.add(t >= xr + ar - 1).only_enforce_if(s)
                        inner_terms.append(t)

                    if inner_terms:
                        inner = model.new_bool_var(f"αB_inner_{key}_{r}_{c}")
                        model.add_bool_or(inner_terms).only_enforce_if([inner, s])
                        for term in inner_terms:
                            model.add(inner >= term).only_enforce_if(s)
                        model.add(a <= xc).only_enforce_if(s)
                        model.add(a <= inner).only_enforce_if(s)
                        model.add(a >= xc + inner - 1).only_enforce_if(s)
                    else:
                        model.add(a == 0).only_enforce_if(s)

            # 每个水平雷段的段起点必须满足 aux = 1
            # 段起点判定：x[r][c] = 1 且 (c = 0 或 x[r][c-1] = 0)
            # 约束形式：aux[r][c] >= x[r][c] - x[r][c-1]
            for r in range(rows - 1):
                for c in range(cols):
                    xc = grid[r][c]
                    a = aux[r][c]
                    if xc is None or a is None:
                        continue

                    left = grid[r][c - 1] if c > 0 else None
                    if left is None:
                        model.add(a >= xc).only_enforce_if(s)
                    else:
                        model.add(a + left >= xc).only_enforce_if(s)
