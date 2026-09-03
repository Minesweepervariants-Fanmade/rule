#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/09/04
# @Author  : DeepSeek Agent
# @FileName: wB.py
"""
[wB] 弱平衡：每行每列的雷数≤(n+1)/2（n为题板边长）
"""

from typing import Optional

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleWB(AbstractMinesRule):
    """
    [wB] 弱平衡规则：每行每列的雷数不超过 (n+1)/2，其中 n 为题板边长。
    """
    id = "wB"
    aliases = ("WB",)
    name = "Weak Balance"
    name.zh_CN = "弱平衡"
    doc = "The number of mines in each row and each column does not exceed (n+1)/2, where n is the board side length."
    doc.zh_CN = "每行每列的雷数不超过 (n+1)/2，其中 n 为题板边长。"
    author = ("萌", 1219009468)
    tags = ["Original", "Global", "Weak"]
    creation_time = "2026-09-04"

    def create_constraints(self, board: 'Board', switch):
        """
        添加约束：对于每个交互式题板，每行和每列的雷数 ≤ (n+1)/2。
        """
        model = board.get_model()
        if model is None:
            return

        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)
            
            # 计算题板边长 n（假设为正方形）
            n = boundary_pos.row + 1
            # 如果行列数不同，取最大值作为边长（但规则要求正方形）
            if boundary_pos.row != boundary_pos.col:
                # 对于非正方形，分别计算行和列的上限
                row_n = boundary_pos.row + 1
                col_n = boundary_pos.col + 1
                row_limit = (row_n + 1) / 2
                col_limit = (col_n + 1) / 2
            else:
                row_limit = (n + 1) / 2
                col_limit = row_limit

            # ---------- 行约束 ----------
            row_positions = board.get_row_pos(boundary_pos)
            for pos in row_positions:
                # 计算该行的雷数之和
                row_sum = sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                # 约束：row_sum <= row_limit
                # 由于 row_limit 可能是小数，需要转换为整数比较
                # 例如 n=5，row_limit=3，则 row_sum <= 3
                # 使用整数上限：row_sum <= floor(row_limit)
                # 但 (n+1)//2 当 n 为偶数时等于 n/2，当 n 为奇数时等于 (n+1)/2
                # 对于偶数 n，例如 n=4，上限为 2.5，整数上限为 2
                # 对于奇数 n，例如 n=5，上限为 3，整数上限为 3
                max_mines = (row_n + 1) // 2 if boundary_pos.row != boundary_pos.col else (n + 1) // 2
                # 使用整数上限
                model.Add(row_sum <= max_mines).OnlyEnforceIf(rule_switch)

            # ---------- 列约束 ----------
            col_positions = board.get_col_pos(boundary_pos)
            for pos in col_positions:
                # 计算该列的雷数之和
                col_sum = sum(board.get_variable(_pos) for _pos in board.get_row_pos(pos))
                # 约束：col_sum <= col_limit
                max_mines = (col_n + 1) // 2 if boundary_pos.row != boundary_pos.col else (n + 1) // 2
                model.Add(col_sum <= max_mines).OnlyEnforceIf(rule_switch)

    def suggest_total(self, info: dict):
        """
        建议总雷数范围：最大雷数不超过每行上限乘以行数。
        """
        def add_constraints(model, total_var):
            nonlocal max_possible
            model.Add(total_var <= max_possible)

        max_possible = 0
        for key in info["interactive"]:
            size = info["size"][key]
            rows, cols = size
            n = rows  # 假设正方形
            if rows != cols:
                # 对于非正方形，分别计算行和列的上限，取较小者作为全局上限
                row_limit = (rows + 1) // 2
                col_limit = (cols + 1) // 2
                max_possible += min(row_limit * rows, col_limit * cols)
            else:
                max_per_row = (n + 1) // 2
                max_possible += max_per_row * n

        info["hard_fns"].append(add_constraints)
        # 软约束：建议总雷数约为最大可能的一半
        info["soft_fn"](max_possible // 2, 0)

    def init_board(self, board: Board) -> bool:
        """
        初始化题板时无需特殊操作。
        """
        return True

    def init_clear(self, board: Board) -> None:
        """
        清除阶段无需特殊操作。
        """
        pass

    def combine(self, other) -> Optional['RuleWB']:
        """
        规则合并优化：不支持合并。
        """
        return None

    def get_deps(self) -> list[str]:
        """
        返回依赖的其他规则名称列表。此规则无依赖。
        """
        return []
