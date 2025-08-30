#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/29 10:00
# @Author  : AI Assistant
# @FileName: 3DW.py

"""
[3DW]海浪(Wave): 所有层的同一行列中有且只有一格有雷, 且所有雷的水平邻居中每一个的上下偏移一格以内的范围内必定有雷.
1. 对于任意x,y, 存在唯一z使得(x,y,z)有雷
2. 若(x0,y0,z0)有雷, 则{(x, y, z)| |x - x0| <= 1, |y - y0| <= 1, |z - z0| <= 1}中的雷格数为其2D邻格个数+1
"""

from typing import List

from .. import Abstract3DMinesRule
from .....abs.board import AbstractPosition, AbstractBoard


def get_vertical_column(board: AbstractBoard, pos: AbstractPosition) -> List[AbstractPosition]:
    """获取给定x,y坐标在所有层中的位置列表"""
    positions = []
    keys = board.get_interactive_keys()

    for key in keys:
        # 克隆位置并改变层
        new_pos = pos.clone()
        new_pos.board_key = key
        if board.in_bounds(new_pos):
            positions.append(new_pos)

    return positions


def get_3d_neighbors(board: AbstractBoard, center_pos: AbstractPosition) -> List[AbstractPosition]:
    """获取3D空间中的27邻域(3x3x3立方体)内的所有位置"""
    neighbors = []

    # 遍历3x3x3立方体
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                # 计算新位置
                temp_pos = center_pos.clone()

                # x轴移动
                if dx > 0:
                    temp_pos = temp_pos.right()
                elif dx < 0:
                    temp_pos = temp_pos.left()

                if temp_pos is None:
                    continue

                # y轴移动
                if dy > 0:
                    temp_pos = temp_pos.down()
                elif dy < 0:
                    temp_pos = temp_pos.up()

                if temp_pos is None:
                    continue

                # z轴移动
                if dz > 0:
                    temp_pos = Rule3DW.up(board, temp_pos, 1)
                elif dz < 0:
                    temp_pos = Rule3DW.down(board, temp_pos, 1)

                if temp_pos is not None and board.in_bounds(temp_pos):
                    neighbors.append(temp_pos)

    return neighbors


class Rule3DW(Abstract3DMinesRule):
    name = ["3DW", "海浪", "Wave"]
    doc = """所有层的同一行列中有且只有一格有雷, 且所有雷的水平邻居中每一个的上下偏移一格以内的范围内必定有雷.
1. 对于任意x,y, 存在唯一z使得(x,y,z)有雷
2. 若(x0,y0,z0)有雷, 则{(x, y, z)| |x - x0| <= 1, |y - y0| <= 1, |z - z0| <= 1}中的雷格数为其2D邻格个数+1"""

    def suggest_total(self, info: dict):
        # 建议合适的雷数
        size = next(iter(info["size"].values()))
        total_cells = size[0] * size[1]
        info["hard_fns"].append(lambda model, total: model.Add(total == int(total_cells)))
        info["soft_fn"](total_cells, 3)

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)

        boundary = board.boundary()
        for col_pos in board.get_col_pos(boundary):
            for pos in board.get_row_pos(col_pos):
                # 获取该(x,y)位置在所有层的垂直柱
                column_positions = get_vertical_column(board, pos)
                if column_positions:
                    var_list = [board.get_variable(p) for p in column_positions]
                    # 每个垂直柱中有且只有一个雷
                    model.Add(sum(var_list) == 1).OnlyEnforceIf(s1)

        boundary = board.boundary()
        for col_pos in board.get_col_pos(boundary):
            for pos in board.get_row_pos(col_pos):
                # 对每一层的每个位置检查
                for key in board.get_interactive_keys():
                    center_pos = pos.clone()
                    center_pos.board_key = key
                    if not board.in_bounds(center_pos):
                        continue

                    # 获取3x3x3邻域
                    neighbors = get_3d_neighbors(board, center_pos)

                    neighbors2d = [neighbor for neighbor in center_pos.neighbors(2) if board.in_bounds(neighbor)]

                    center_var = board.get_variable(center_pos)
                    neighbor_vars = [board.get_variable(neighbor) for neighbor in neighbors]

                    model.Add(sum(neighbor_vars) == len(neighbors2d)+1).OnlyEnforceIf([center_var, s2])
