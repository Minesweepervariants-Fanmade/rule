#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:21
# @Author  : Wu_RH
# @FileName: 1D'.py
"""
[1D'] 战舰 (Battleship)：每个雷区域为宽度为 1、长度不超过 4 的矩形，矩形不能对角相邻
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1Dp(AbstractMinesRule):
    name = ["1D'", "战舰", "Battleship"]
    doc = "每个雷区域为宽度为 1、长度不超过 4 的矩形，矩形不能对角相邻"

    def create_constraints(self, board: AbstractBoard, switch):
        # 获取求解器模型
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key)
            max_x = boundary_pos.x
            max_y = boundary_pos.y

            # 创建二维数组存储连续长度变量
            h_length = {}  # 水平连续长度
            v_length = {}  # 垂直连续长度

            # 遍历所有格子
            for y in range(max_y + 1):
                for x in range(max_x + 1):
                    pos = board.get_pos(x, y, key)
                    cell_var = board.get_variable(pos)

                    # === 对角相邻必须为非雷 ===
                    diagonals = []
                    # 左上
                    if x > 0 and y > 0:
                        diagonals.append(board.get_pos(x - 1, y - 1, key))
                    # 右上
                    if x < max_x and y > 0:
                        diagonals.append(board.get_pos(x + 1, y - 1, key))
                    # 左下
                    if x > 0 and y < max_y:
                        diagonals.append(board.get_pos(x - 1, y + 1, key))
                    # 右下
                    if x < max_x and y < max_y:
                        diagonals.append(board.get_pos(x + 1, y + 1, key))

                    for diag_pos in diagonals:
                        diag_var = board.get_variable(diag_pos)
                        model.Add(diag_var == 0).OnlyEnforceIf([cell_var, s])

                    # === 正交相邻雷数限制 (0-2) ===
                    ortho_vars = []
                    # 上
                    if y > 0:
                        ortho_vars.append(board.get_variable(board.get_pos(x, y - 1, key)))
                    # 下
                    if y < max_y:
                        ortho_vars.append(board.get_variable(board.get_pos(x, y + 1, key)))
                    # 左
                    if x > 0:
                        ortho_vars.append(board.get_variable(board.get_pos(x - 1, y, key)))
                    # 右
                    if x < max_x:
                        ortho_vars.append(board.get_variable(board.get_pos(x + 1, y, key)))

                    ortho_count = 0
                    if ortho_vars:
                        ortho_count = sum(ortho_vars)
                        model.Add(ortho_count <= 2).OnlyEnforceIf([cell_var, s])

                    # === 两个相邻雷必须同向 ===
                    # 创建方向指示变量
                    has_horizontal = model.NewBoolVar(f'hor_{x}_{y}')
                    has_vertical = model.NewBoolVar(f'ver_{x}_{y}')

                    # 水平相邻条件
                    if 0 < x < max_x:
                        left_var = board.get_variable(board.get_pos(x - 1, y, key))
                        right_var = board.get_variable(board.get_pos(x + 1, y, key))
                        model.Add(left_var + right_var == 2).OnlyEnforceIf([has_horizontal, s])
                        model.Add(has_horizontal == 0).OnlyEnforceIf([left_var.Not(), s])
                        model.Add(has_horizontal == 0).OnlyEnforceIf([right_var.Not(), s])
                    else:
                        has_horizontal = model.NewConstant(0)

                    # 垂直相邻条件
                    if 0 < y < max_y:
                        up_var = board.get_variable(board.get_pos(x, y - 1, key))
                        down_var = board.get_variable(board.get_pos(x, y + 1, key))
                        model.Add(up_var + down_var == 2).OnlyEnforceIf([has_vertical, s])
                        model.Add(has_vertical == 0).OnlyEnforceIf([up_var.Not(), s])
                        model.Add(has_vertical == 0).OnlyEnforceIf([down_var.Not(), s])
                    else:
                        has_vertical = model.NewConstant(0)

                    # 当有2个相邻雷时，必须是同一直线方向
                    if ortho_vars:
                        model.Add(ortho_count != 2).OnlyEnforceIf([has_horizontal.Not(), has_vertical.Not(), s])

                    # === 战舰长度限制 (1-4) ===
                    # 水平连续长度变量 (0-4)
                    h_len_var = model.NewIntVar(0, 4, f'hlen_{x}_{y}')
                    h_length[(x, y)] = h_len_var

                    # 水平长度约束
                    if x == 0:  # 最左列
                        # 当前是起点：长度=1(是雷)或0(非雷)
                        model.Add(h_len_var == cell_var).OnlyEnforceIf(s)
                    else:
                        left_pos = board.get_pos(x - 1, y, key)
                        left_var = board.get_variable(left_pos)

                        # 情况1：当前不是雷 → 长度为0
                        model.Add(h_len_var == 0).OnlyEnforceIf([cell_var.Not(), s])

                        # 情况2：当前是雷且左边不是雷 → 新起点，长度=1
                        model.Add(h_len_var == 1).OnlyEnforceIf([cell_var, left_var.Not(), s])

                        # 情况3：当前是雷且左边是雷 → 继承左边长度+1
                        if x > 0:
                            model.Add(h_len_var == h_length[(x - 1, y)] + 1).OnlyEnforceIf(
                                [cell_var, left_var, s])

                    # 垂直连续长度变量 (0-4)
                    v_len_var = model.NewIntVar(0, 4, f'vlen_{x}_{y}')
                    v_length[(x, y)] = v_len_var

                    # 垂直长度约束
                    if y == 0:  # 最上行
                        model.Add(v_len_var == cell_var).OnlyEnforceIf(s)
                    else:
                        up_pos = board.get_pos(x, y - 1, key)
                        up_var = board.get_variable(up_pos)

                        model.Add(v_len_var == 0).OnlyEnforceIf([cell_var.Not(), s])
                        model.Add(v_len_var == 1).OnlyEnforceIf([cell_var, up_var.Not(), s])
                        if y > 0:
                            model.Add(v_len_var == v_length[(x, y - 1)] + 1).OnlyEnforceIf(
                                [cell_var, up_var, s])

                    # === 长度上限约束 ===
                    # 当战舰达到最大长度(4)时，下一格必须不能是雷
                    # 水平方向
                    # if x < max_x - 1:  # 确保有下一格
                    #     next_right = board.get_pos(x + 1, y, key)
                    #     next_right_var = board.get_variable(next_right)
                    #     # 如果当前长度=4，下一格必须不是雷
                    #     model.Add(next_right_var == 0).OnlyEnforceIf(h_len_var == 4)
                    #
                    # # 垂直方向
                    # if y < max_y - 1:
                    #     next_down = board.get_pos(x, y + 1, key)
                    #     next_down_var = board.get_variable(next_down)
                    #     model.Add(next_down_var == 0).OnlyEnforceIf(v_len_var == 4)
