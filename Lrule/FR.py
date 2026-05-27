#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Time    : 2026/05/27 17:24
# @Author  : 雾
# @FileName: FR.py
"""
[FR] 局部阈值 (Local Threshold)：
对于每一个 2×2 区域，必存在一个包含它的 4×4 区域（2×2 区域必须位于该 4×4 的左上/右上/左下/右下角）。
将该 4×4 区域划分为四个 2×2 子块，原 2×2 区域中的每个格子对应一个子块（左上格→左上子块，右上→右上子块，左下→左下子块，右下→右下子块）。
若对应子块内的总雷数为 0 或 1，则该格子必须为**无雷**（0）；
若总雷数为 3 或 4，则该格子必须为**雷**（1）；
若总雷数为 2，则该格子状态自由（无额外约束）。
"""

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.utils.tool import get_logger


class RuleFR(AbstractMinesRule):
    id = "FR"
    name = "Division"
    name.zh_CN = "分域"
    doc = "Every non-overlapping 2x2 block (stride 2) must be a corner of some 4x4 block. The 4x4 is split into four 2x2 subblocks. Each cell in the original 2x2 corresponds to the subblock at the same relative position. If that subblock contains 0 or 1 mines → the cell is empty; 3 or 4 mines → the cell is a mine; 2 mines → free."
    doc.zh_CN = "步长为2的不重叠2×2块，每个块须作为某个4×4区域的角。该4×4均分为四个2×2子块，原块中每个格子对应4×4中同位置的子块（左上→左上子块，等）。子块雷数0-1→该格无雷，3-4→该格有雷，2无约束。"
    author = ("雾", 3140864122)
    tags = ["Variant", "Global", "Construction"]
    creation_time = "2026-05-27 17:24:00"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            max_x = bound.col
            max_y = bound.row

            for x in range(0, max_x, 2):
                for y in range(0, max_y, 2):
                    # 原2x2四个格子
                    pos_tl = board.get_pos(x, y, key)
                    pos_tr = board.get_pos(x, y + 1, key)
                    pos_bl = board.get_pos(x + 1, y, key)
                    pos_br = board.get_pos(x + 1, y + 1, key)
                    if not all(board.in_bounds(p) for p in (pos_tl, pos_tr, pos_bl, pos_br)):
                        continue
                    var_tl = board.get_variable(pos_tl, special='raw')
                    var_tr = board.get_variable(pos_tr, special='raw')
                    var_bl = board.get_variable(pos_bl, special='raw')
                    var_br = board.get_variable(pos_br, special='raw')
                    if any(v is None for v in (var_tl, var_tr, var_bl, var_br)):
                        continue

                    candidates = []
                    # 四个方向: (dx, dy, 子块映射索引)
                    # 映射索引: 0=左上,1=右上,2=左下,3=右下
                    # 原2x2格子索引: [0]=tl, [1]=tr, [2]=bl, [3]=br
                    # 对于每个方向, 原2x2格子i对应4x4内子块mapping[i]
                    directions = [
                        (0, 0),  # 原2x2是4x4的左上角子块
                        (0, -2),  # 右上角子块
                        (-2, 0),  # 左下角子块
                        (-2, -2)  # 右下角子块
                    ]

                    for dx, dy in directions:
                        ox, oy = x + dx, y + dy
                        if not (ox >= 0 and ox + 3 <= max_x and oy >= 0 and oy + 3 <= max_y):
                            continue
                        cand = model.NewBoolVar(f"FR_{key}_{x}_{y}_{ox}_{oy}")
                        candidates.append(cand)

                        # 4x4内四个2x2子块的左上角
                        sub_tl = board.get_pos(ox, oy, key)
                        sub_tr = board.get_pos(ox, oy + 2, key)
                        sub_bl = board.get_pos(ox + 2, oy, key)
                        sub_br = board.get_pos(ox + 2, oy + 2, key)
                        subs = [sub_tl, sub_tr, sub_bl, sub_br]

                        # 计算每个子块的雷数和
                        sums = []
                        for sub in subs:
                            vars_sub = [
                                board.get_variable(sub, special='raw'),
                                board.get_variable(sub.right(), special='raw'),
                                board.get_variable(sub.down(), special='raw'),
                                board.get_variable(sub.right().down(), special='raw')
                            ]
                            sums.append(sum(v for v in vars_sub if v is not None))

                        # 原2x2的四个格子变量列表
                        cells = [var_tl, var_tr, var_bl, var_br]

                        for i, cell_var in enumerate(cells):
                            sub_sum = sums[i]
                            le1 = model.NewBoolVar(f"FR_le1_{key}_{x}_{y}_{i}_{ox}_{oy}")
                            ge3 = model.NewBoolVar(f"FR_ge3_{key}_{x}_{y}_{i}_{ox}_{oy}")
                            model.Add(sub_sum <= 1).OnlyEnforceIf(le1)
                            model.Add(sub_sum >= 2).OnlyEnforceIf(le1.Not())
                            model.Add(sub_sum >= 3).OnlyEnforceIf(ge3)
                            model.Add(sub_sum <= 2).OnlyEnforceIf(ge3.Not())
                            model.Add(cell_var == 0).OnlyEnforceIf([le1, cand, rule_switch])
                            model.Add(cell_var == 1).OnlyEnforceIf([ge3, cand, rule_switch])
                            get_logger().trace(f"[FR] 2x2左上角=({x},{y}) 方向偏移=({dx},{dy}) 格子索引{i}[{cell_var}] 绑定到子块索引{i} 子块雷数和={sub_sum}")

                    if candidates:
                        model.AddBoolOr(candidates).OnlyEnforceIf(rule_switch)
