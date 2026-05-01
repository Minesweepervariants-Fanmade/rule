#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/05 12:00
# @Author  : AI Assistant
# @FileName: 1D''.py
"""
[D''] 矩形和对角线拼图 (Rectangles & Diagonals)：
所有雷必须是 1x1~1x4 矩形或者长度 2~4 的对角线的一部分，这些矩形和对角线之间不能互相接触（对角也不行）。
作者：对映 (3242525312)
最后编辑时间：2026-03-01 13:28:35

(内容由AI生成 质量不可靠)
"""

from typing import List, Tuple

from ortools.sat.python.cp_model import CpModel, IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition


class Rule1Dpp(AbstractMinesRule):
    id = "1D''"
    aliases = ("D''",)
    name = "RectDiag"
    name.zh_CN = "矩形对角线"
    doc = "所有雷必须是1x1~1x4矩形或者长度2~4的对角线的一部分，这些形状之间不能互相接触（对角也不行）。"

    def __init__(self, board: AbstractBoard = None, data=None) -> None:
        super().__init__(board, data)

    def create_constraints(self, board: 'AbstractBoard', switch) -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.x + 1
            cols = bound.y + 1

            # 收集所有可能的形状及其包含的格子
            shapes: List[Tuple[List[AbstractPosition], IntVar]] = []

            # 1. 水平矩形 (宽度1，长度1~4)
            for length in range(1, 5):
                for x in range(rows):
                    for y in range(cols - length + 1):
                        positions = [board.get_pos(x, y + i, key) for i in range(length)]
                        shapes.append((positions, None))  # var 稍后创建

            # 2. 主对角线 (dx=1, dy=1, 长度2~4)
            for length in range(2, 5):
                for x in range(rows - length + 1):
                    for y in range(cols - length + 1):
                        positions = [board.get_pos(x + i, y + i, key) for i in range(length)]
                        shapes.append((positions, None))

            # 3. 副对角线 (dx=1, dy=-1, 长度2~4)
            for length in range(2, 5):
                for x in range(rows - length + 1):
                    for y in range(length - 1, cols):
                        positions = [board.get_pos(x + i, y - i, key) for i in range(length)]
                        shapes.append((positions, None))

            # 为每个形状创建布尔变量
            shape_vars = []
            for idx, (positions, _) in enumerate(shapes):
                var = model.NewBoolVar(f"shape_{key}_{idx}")
                shape_vars.append(var)
                # 形状选中 => 所有格子都是雷
                for pos in positions:
                    model.Add(board.get_variable(pos) == 1).OnlyEnforceIf([var, s])
                # 可选：如果某个格子不是雷，则形状不能选中（但由覆盖约束自动保证，无需额外）

            # 记录每个格子被哪些形状覆盖
            pos_to_shapes: dict[AbstractPosition, List[IntVar]] = {}
            for shape_var, (positions, _) in zip(shape_vars, shapes):
                for pos in positions:
                    pos_to_shapes.setdefault(pos, []).append(shape_var)

            # 覆盖约束：每个格子的雷变量 == 覆盖它的形状变量之和（0 或 1）
            for pos, shape_list in pos_to_shapes.items():
                mine_var = board.get_variable(pos)
                if mine_var is None:
                    continue
                model.Add(mine_var == sum(shape_list)).OnlyEnforceIf(s)

            # 不接触约束：任意两个形状如果存在任何一对格子八连通接触，则不能同时为 True
            n = len(shapes)
            for i in range(n):
                for j in range(i + 1, n):
                    if self._shapes_touch(shapes[i][0], shapes[j][0], board):
                        model.AddBoolOr([shape_vars[i].Not(), shape_vars[j].Not()]).OnlyEnforceIf(s)

    @staticmethod
    def _shapes_touch(shape_a: List[AbstractPosition], shape_b: List[AbstractPosition],
                      board: AbstractBoard) -> bool:
        """
        判断两个形状是否八连通接触（包括对角相邻）。
        即是否存在格子 p in A, q in B 使得 max(|dx|,|dy|) <= 1。
        """
        for p in shape_a:
            for q in shape_b:
                dx = abs(p.x - q.x)
                dy = abs(p.y - q.y)
                if dx <= 1 and dy <= 1:
                    return True
        return False

    def suggest_total(self, info: dict):
        # 简单软约束：建议总雷数不超过总格子数的 40%
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        info["soft_fn"](int(ub * 0.4), 0)