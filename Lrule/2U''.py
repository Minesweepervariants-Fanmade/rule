#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/03
# @Author  : muratsubo
# @FileName: 2U''.py
"""
[2U''] 孤岛：每行每列恰有一个雷符合1U（孤立雷，上下左右无雷）。
同时，所有非孤立雷必须至少有一个相邻雷。
目标总雷数R=40%并四舍五入，若达不到则范围在 (0.4*n², n+2] 内。
"""
import math
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.size import Size
from minesweepervariants.position import Position


class Rule2U(AbstractMinesRule):
    id = "2U''"
    aliases = ("2U",)
    name = "Islands"
    name.zh_CN = "孤岛"
    doc = "Exactly one isolated mine per row and column; all non-isolated mines must have at least one adjacent mine."
    doc.zh_CN = "每行每列恰有一个孤立雷（上下左右无雷）；所有非孤立雷至少有一个相邻雷。"
    tags = ["Creative", "Global", "Strict R"]
    creation_time = "2026-08-01"
    author = ("muratsubo", 0)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        # 每次调用都添加约束，因为 fill_valid 每次尝试都会清除模型并重新调用

        interactive_keys = board.get_interactive_keys()
        if not interactive_keys:
            interactive_keys = board.get_board_keys()
        if not interactive_keys:
            return
        main_key = interactive_keys[0]
        boundary_pos = board.boundary(main_key)
        height = boundary_pos.row + 1
        width = boundary_pos.col + 1

        # 规则要求正方形题板
        if height != width:
            model.Add(0 == 1)
            return
        n = height

        # 为每个位置创建孤立雷辅助变量
        unary_vars = {}
        for row in range(height):
            for col in range(width):
                pos = board.get_pos(row, col, main_key)
                var = board.get_variable(pos)
                unary = model.NewBoolVar(f"unary_{row}_{col}")
                unary_vars[pos] = unary

                # unary => var (孤立雷必须是雷)
                model.AddImplication(unary, var)
                # unary => 邻居不是雷
                for d in [pos.up(), pos.down(), pos.left(), pos.right()]:
                    if board.in_bounds(d) and d.board_key == main_key:
                        nv = board.get_variable(d)
                        model.AddImplication(unary, nv.Not())
                # var AND 所有邻居都不是雷 => unary
                neighbor_vars = []
                for d in [pos.up(), pos.down(), pos.left(), pos.right()]:
                    if board.in_bounds(d) and d.board_key == main_key:
                        neighbor_vars.append(board.get_variable(d))
                if neighbor_vars:
                    # 如果 var 为真且所有邻居都为假，则 unary 必须为真
                    # 约束: (var) AND (NOT any neighbor) => unary
                    # 转换为 CNF: NOT var OR any_neighbor OR unary
                    model.AddBoolOr([var.Not()] + neighbor_vars + [unary])
                else:
                    # 如果没有邻居（1x1题板），则 var => unary
                    model.AddImplication(var, unary)

        # 每行恰好一个孤立雷
        for row in range(height):
            row_unaries = [unary_vars[board.get_pos(row, col, main_key)] for col in range(width)]
            model.Add(sum(row_unaries) == 1)

        # 每列恰好一个孤立雷
        for col in range(width):
            col_unaries = [unary_vars[board.get_pos(row, col, main_key)] for row in range(height)]
            model.Add(sum(col_unaries) == 1)

        # 非孤立雷必须至少有一个相邻雷这个约束是多余的，因为孤立雷的定义已经隐含了这一点。
        # 但我们保留此约束以增强语义清晰度（虽然它实际上是由 unary 定义保证的）。
        # 但为了模型简洁，这里不再重复添加。



    def init_clear(self, board: 'Board') -> None:
        # 无需清除任何内容
        pass

    def suggest_total(self, info: dict):
        for key in info["interactive"]:
            h, w = info["size"][key]
            if h != w:
                continue
            n = h
            total_cells = n * n
            target = int(round(0.4 * total_cells))
            # 软约束：尽量接近 target（权重1）
            # 框架会自动搜索可行解，自动调整到最接近目标的值
            info["soft_fn"](target, 1)
            return
        # 若无交互式题板，至少尝试主键
        for key in info.get("size", {}):
            h, w = info["size"][key]
            if h == w:
                n = h
                target = int(round(0.4 * n * n))
                info["soft_fn"](target, 1)
                return
