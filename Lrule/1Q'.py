#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/24 06:59
# @Author  : 雾 (3140864122)
# @FileName: 1Q'.py
"""
[1Q'] 扭断: 任意2x2区域中，不能恰好有两个雷且位于对角上
"""

from typing import List

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position


class Rule1Qp(AbstractMinesRule):
    """
    [1Q'] 扭断规则：禁止 2x2 区域内恰好有两个对角雷的情况。
    """
    id = "1Q'"
    aliases = ("Q'",)
    name = "Twist"
    name.zh_CN = "扭断"
    doc = "No 2x2 area may contain exactly two mines that are diagonally opposite."
    doc.zh_CN = "任意2x2区域中，不能恰好有两个雷且位于对角上。"
    tags = ["Variant", "Local", "Anti-Construction"]
    creation_time = "2026-08-24"
    author = ("雾", 3140864122)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        # 可选：支持 3I 命名空间扩展（类似 1Q 的 _3I 模式）
        self._3I = False
        if data is not None and data == "3I":
            self._3I = True

    def create_constraints(self, board: 'Board', switch):
        """
        为每个 2x2 区域添加约束：禁止恰好两个对角雷的情况。
        """
        model = board.get_model()
        s = switch.get(model, self)

        # 获取所有交互式题板
        interactive_keys = board.get_interactive_keys()
        if not interactive_keys:
            return

        for key in interactive_keys:
            # 获取边界位置（右下角）
            bound = board.boundary(key=key)
            # 边界位置返回的是 (row, col) 的最大值，rows = bound.x + 1, cols = bound.y + 1
            # 注意：Position 的 row 是行，col 是列；但 bound.x 对应 row，bound.y 对应 col
            max_row = bound.x
            max_col = bound.y

            # 遍历所有可能的 2x2 左上角位置 (row, col)
            for row in range(max_row):
                for col in range(max_col):
                    # 获取 2x2 区域的四个位置
                    pos_tl = board.get_pos(row, col, key)
                    pos_tr = board.get_pos(row, col + 1, key)
                    pos_bl = board.get_pos(row + 1, col, key)
                    pos_br = board.get_pos(row + 1, col + 1, key)

                    # 确保四个位置都有效（可能在异形板中无效）
                    if not all(board.is_valid(p) for p in (pos_tl, pos_tr, pos_bl, pos_br)):
                        continue

                    # 获取四个变量的雷状态（基于 3I 或 raw 命名空间）
                    if self._3I:
                        var_tl = board.get_variable(pos_tl, special="3I")
                        var_tr = board.get_variable(pos_tr, special="3I")
                        var_bl = board.get_variable(pos_bl, special="3I")
                        var_br = board.get_variable(pos_br, special="3I")
                    else:
                        var_tl = board.get_variable(pos_tl)
                        var_tr = board.get_variable(pos_tr)
                        var_bl = board.get_variable(pos_bl)
                        var_br = board.get_variable(pos_br)

                    # 跳过缺失变量的情况
                    if any(v is None for v in (var_tl, var_tr, var_bl, var_br)):
                        continue

                    # 添加约束：禁止恰好两个对角雷的情况
                    # 情况1：左上和右下是雷，右上和左下不是雷
                    # 等价于：not (var_tl and var_br and not var_tr and not var_bl)
                    # 用 BoolOr 表达：not var_tl or not var_br or var_tr or var_bl
                    model.AddBoolOr([var_tl.Not(), var_br.Not(), var_tr, var_bl]).OnlyEnforceIf(s)

                    # 情况2：右上和左下是雷，左上和右下不是雷
                    # 等价于：not (var_tr and var_bl and not var_tl and not var_br)
                    # 用 BoolOr 表达：not var_tr or not var_bl or var_tl or var_br
                    model.AddBoolOr([var_tr.Not(), var_bl.Not(), var_tl, var_br]).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        """
        建议总雷数范围：避免总雷数过少（导致无解）或过多。
        """
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        # 建议总雷数约为总格子数的 40%（与 1Q 规则类似）
        info["soft_fn"](int(ub * 0.4), 0)
