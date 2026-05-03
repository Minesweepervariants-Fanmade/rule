#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/02 18:20
# @Author  : DeepSeek
# @FileName: DQ.py
"""
[DQ] 双队列 (Double Queue)：行雷数的多重集合等于列雷数的多重集合。
"""

from typing import List, TYPE_CHECKING

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleDQ(AbstractMinesRule):
    id = "DQ"
    name = "Double Queue"
    name.zh_CN = "双队列"
    doc = "The multiset of row mine counts equals the multiset of column mine counts."
    doc.zh_CN = "行雷数的多重集合等于列雷数的多重集合（即排序后行雷数列表与列雷数列表相同）。"
    author = ("DeepSeek", "")
    tags = ["Original", "Global", "Mine-Counting", "Strict R"]

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.x + 1      # 行数
            cols = bound.y + 1      # 列数
            if rows == 0 or cols == 0:
                continue

            # 1. 构建每行的雷数变量
            row_sums: List[IntVar] = []
            for x in range(rows):
                row_vars = [board.get_variable(board.get_pos(x, y, key))
                            for y in range(cols)]
                # 过滤掉可能为 None 的变量（实际不会）
                row_vars = [v for v in row_vars if v is not None]
                if not row_vars:
                    row_sums.append(model.NewConstant(0))
                    continue
                row_sum = model.NewIntVar(0, cols, f"row_{key}_{x}")
                model.Add(row_sum == sum(row_vars)).OnlyEnforceIf(s)
                row_sums.append(row_sum)

            # 2. 构建每列的雷数变量
            col_sums: List[IntVar] = []
            for y in range(cols):
                col_vars = [board.get_variable(board.get_pos(x, y, key))
                            for x in range(rows)]
                col_vars = [v for v in col_vars if v is not None]
                if not col_vars:
                    col_sums.append(model.NewConstant(0))
                    continue
                col_sum = model.NewIntVar(0, rows, f"col_{key}_{y}")
                model.Add(col_sum == sum(col_vars)).OnlyEnforceIf(s)
                col_sums.append(col_sum)

            # 可能出现的最大雷数值
            max_val = max(cols, rows)

            # 对每个可能的雷数值 v，统计其在行和列中出现的次数，并约束相等
            for v in range(max_val + 1):
                # 统计行中出现 v 的次数
                row_cnt = model.NewIntVar(0, rows, f"row_cnt_{key}_{v}")
                row_indicators = []
                for i, rs in enumerate(row_sums):
                    indicator = model.NewBoolVar(f"row_eq_{key}_{v}_{i}")
                    model.Add(rs == v).OnlyEnforceIf(indicator)
                    model.Add(rs != v).OnlyEnforceIf(indicator.Not())
                    row_indicators.append(indicator)
                model.Add(row_cnt == sum(row_indicators)).OnlyEnforceIf(s)

                # 统计列中出现 v 的次数
                col_cnt = model.NewIntVar(0, cols, f"col_cnt_{key}_{v}")
                col_indicators = []
                for j, cs in enumerate(col_sums):
                    indicator = model.NewBoolVar(f"col_eq_{key}_{v}_{j}")
                    model.Add(cs == v).OnlyEnforceIf(indicator)
                    model.Add(cs != v).OnlyEnforceIf(indicator.Not())
                    col_indicators.append(indicator)
                model.Add(col_cnt == sum(col_indicators)).OnlyEnforceIf(s)

                # 行和列中 v 的出现次数必须相等
                model.Add(row_cnt == col_cnt).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        # 软约束：建议总雷数约为格子总数的 40%（与多数左线规则保持一致）
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        info["soft_fn"](int(ub * 0.4), 0)
