#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/06/17 13:34
# @Author  : NT (2201963934)
# @FileName: 1TStar5.py

"""
[1T*5] 纯五连: 行列斜方向上，相邻两组雷/非雷组（任意一组可为0）长度之和必须≥5
"""

from typing import List, Tuple
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule1TStar5(AbstractMinesRule):
    id = "1T*5"
    name = "Pure Five"
    name.zh_CN = "纯五连"
    doc = "In horizontal, vertical, and diagonal directions, the sum of lengths of any two adjacent groups (mines or non-mines, either can be 0) must be >= 5"
    doc.zh_CN = "行列斜方向上，相邻两组雷/非雷组（任意一组可为0）长度之和必须≥5"
    author = ("NT", 2201963934)
    tags = ["Variant", "Global", "Construction", "Strict R"]
    creation_time = "2026-06-17"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)

    @staticmethod
    def _collect_all_lines(board: Board, key: str) -> List[List]:
        """
        枚举所有行、列、两条对角线上的位置列表。
        每一条线是一个有序的 Position 列表。
        """
        lines: List[List] = []
        boundary = board.boundary(key)
        max_row = boundary.row
        max_col = boundary.col

        # 水平线 (每行)
        for r in range(max_row + 1):
            positions = []
            for c in range(max_col + 1):
                pos = board.get_pos(r, c, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
            if len(positions) >= 2:
                lines.append(positions)

        # 垂直线 (每列)
        for c in range(max_col + 1):
            positions = []
            for r in range(max_row + 1):
                pos = board.get_pos(r, c, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
            if len(positions) >= 2:
                lines.append(positions)

        # 主对角线 (方向: (1, 1))
        # 起点: 第一行所有列 + 第一列所有行（避免重复 (0,0)）
        for c in range(max_col + 1):
            positions = []
            r, cc = 0, c
            while r <= max_row and cc <= max_col:
                pos = board.get_pos(r, cc, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
                r += 1
                cc += 1
            if len(positions) >= 2:
                lines.append(positions)
        for r in range(1, max_row + 1):
            positions = []
            rr, c = r, 0
            while rr <= max_row and c <= max_col:
                pos = board.get_pos(rr, c, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
                rr += 1
                c += 1
            if len(positions) >= 2:
                lines.append(positions)

        # 副对角线 (方向: (1, -1))
        # 起点: 第一行所有列 + 最后一列所有行（避免重复 (0, max_col)）
        for c in range(max_col + 1):
            positions = []
            r, cc = 0, c
            while r <= max_row and cc >= 0:
                pos = board.get_pos(r, cc, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
                r += 1
                cc -= 1
            if len(positions) >= 2:
                lines.append(positions)
        for r in range(1, max_row + 1):
            positions = []
            rr, c = r, max_col
            while rr <= max_row and c >= 0:
                pos = board.get_pos(rr, c, key)
                if pos is not None and board.in_bounds(pos):
                    positions.append(pos)
                rr += 1
                c -= 1
            if len(positions) >= 2:
                lines.append(positions)

        return lines

    @staticmethod
    def _add_bad_pattern_constraints(
        model, board: Board, switch_var, line: List, line_id: int
    ) -> None:
        """
        对一条线，禁止所有"相邻两组长度之和 < 5"的精确模式。

        策略: 枚举线中每个位置 i 作为段1的起始，段1长度 L1 (1..4)，
        段2长度 L2 (1..4-L1)，且 L1+L2 < 5。
        禁止精确模式: 段1为连续 L1 个同状态，段2为连续 L2 个相反状态，
        且段1左侧边界精确（i 是线起始或 var[i-1] 与段1状态相反），
        段2右侧边界精确（i+L1+L2 超出线或 var[i+L1+L2] 与段1状态相同）。

        使用 BoolOr 直接禁止，避免 OnlyEnforceIf 单向蕴含问题。
        """
        n = len(line)
        if n < 2:
            return

        line_vars = [board.get_variable(pos, special="raw") for pos in line]
        if any(v is None for v in line_vars):
            return

        for L1 in range(1, 5):
            for L2 in range(1, 5 - L1):
                if L1 + L2 >= 5:
                    continue
                for i in range(n - L1 - L2 + 1):
                    # ---------- 情况1: 段1全雷, 段2全非雷 ----------
                    terms = []
                    for k in range(L1):
                        terms.append(line_vars[i + k].Not())
                    for k in range(L2):
                        terms.append(line_vars[i + L1 + k])
                    if i > 0:
                        terms.append(line_vars[i - 1])  # 左侧格是雷
                    if i + L1 + L2 < n:
                        terms.append(line_vars[i + L1 + L2].Not())  # 右侧格非雷

                    model.add_bool_or(terms).only_enforce_if(switch_var)

                    # ---------- 情况2: 段1全非雷, 段2全雷 ----------
                    terms = []
                    for k in range(L1):
                        terms.append(line_vars[i + k])
                    for k in range(L2):
                        terms.append(line_vars[i + L1 + k].Not())
                    if i > 0:
                        terms.append(line_vars[i - 1].Not())  # 左侧格非雷
                    if i + L1 + L2 < n:
                        terms.append(line_vars[i + L1 + L2])  # 右侧格是雷

                    model.add_bool_or(terms).only_enforce_if(switch_var)

    def create_constraints(self, board: Board, switch) -> None:
        """
        为所有交互题板的每条线添加约束:
        - 任何相邻两组长度之和必须>=5。
        """
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            lines = self._collect_all_lines(board, key)
            for line_id, line in enumerate(lines):
                self._add_bad_pattern_constraints(model, board, s, line, line_id)

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数。
        对于小棋盘（如5x5），短对角线（长度2/3）要求线段同色，
        使中间总雷数不可行，只能取0/1/ub-1/ub；
        对于大棋盘，建议约40%。
        """
        ub = 0
        for key in info.get("interactive", []):
            ub += info.get("total", {}).get(key, 0)
        if ub > 0:
            if ub <= 25:
                # 小棋盘：短对角线长度2/3要求全同色，中间值不可行
                # 硬约束限定可行总雷数，避免 init_total 选择中间值
                def hard_constraint(model, total_var):
                    model.add_allowed_assignments(
                        [total_var],
                        [(0,), (1,), (ub - 1,), (ub,)]
                    )
                info["hard_fns"].append(hard_constraint)
                info["soft_fn"](0, 1)
                info["soft_fn"](ub, 1)
            else:
                info["soft_fn"](int(ub * 0.4), 0)
