#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/23 18:02
# @Author  : 小绿草 (3021857082)
# @FileName: SUD_.py

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch


class RuleSUD_(AbstractMinesRule):
    id = "SUD'"
    name = "Sudoku Box"
    name.zh_CN = "数独宫"
    doc = "Sudoku Box: The board side length must be a multiple of 3. The board is evenly divided into 9 boxes, and numbers in each box must be unique.(V only)"
    doc.zh_CN = "数独宫：题板边长只能为3的整数倍，将题板均匀分为9个宫，每宫内数字不相同(仅限V)"
    tags = ["Original", 'Meta']
    author = ("小绿草", 3021857082)
    creation_time = "2026-05-23 18:02:00"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        bound = board.boundary()
        if bound.x != bound.y:
            raise ValueError("请输入一个正方形题板")
        if (bound.x + 1) % 3 != 0:
            raise ValueError("题板边长必须为3的整数倍")

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key=key)
            # 获取边界行和列的范围，计算边长
            rows = board.get_row_pos(pos_bound)
            cols = board.get_col_pos(pos_bound)
            n_rows = len(rows)
            n_cols = len(cols)

            # 检查边长是否为 3 的倍数且行列相等（标准正方形题板）
            if n_rows != n_cols or n_rows % 3 != 0:
                # 不符合题板要求，不添加约束（或可选择记录警告）
                continue

            block_size = n_rows // 3  # 每个宫的边长

            real_pos_sum = {
                pos: sum([
                    board.get_variable(_pos)
                    for _pos in pos.neighbors(2)
                    if board.is_valid(_pos)
                ]) for pos, _ in board(key=key)
            }
            ub = max(8, max(board.get_config(key, "size")))
            pos_sum = {
                pos: model.new_int_var(0, ub, str(pos))
                for pos, _ in board(key=key)
            }

            for pos, var in board(mode="var", key=key):
                model.add(real_pos_sum[pos] == pos_sum[pos]).OnlyEnforceIf(s, var.Not())

            # 将位置按所在宫分组（使用坐标直接计算宫索引）
            boxes = {}
            for pos, _ in board(key=key):
                # 根据实际坐标计算宫索引（假设坐标从0开始连续）
                box_row = pos.x // block_size
                box_col = pos.y // block_size
                box_idx = (box_row, box_col)
                boxes.setdefault(box_idx, []).append(pos_sum[pos])

            # 每个宫内数字互不相同
            for var_list in boxes.values():
                if len(var_list) > 1:
                    model.add_all_different(var_list).OnlyEnforceIf(s)