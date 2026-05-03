#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/05
# @Author  : botif
# @FileName: AS.py
"""
[AS] 自旋 (Spin):
每一行不能同时存在染色非雷格、非染色非雷格、染色雷格和非染色雷格。
作者: botif (1643337042)
最后编辑时间: 2026-03-01 13:28:35
内容由AI生成质量不保证
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition
from ortools.sat.python.cp_model import CpModel


class RuleAS(AbstractMinesRule):
    id = "AS"
    name = "Spin"
    name.zh_CN = "自旋"
    doc = "Each row cannot simultaneously contain dyed non-mine, undyed non-mine, dyed mine, and undyed mine"
    doc.zh_CN = "每一行不能同时存在染色非雷格、非染色非雷格、染色雷格和非染色雷格"
    author = ("botif", 1643337042)
    tags = ["Creative", "Local", "Dyed"]

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            # 遍历每一行
            for row_start in board.get_col_pos(boundary):
                row_positions = board.get_row_pos(row_start)
                if not row_positions:
                    continue

                # 四个存在性标志
                has_dyed_mine = model.NewBoolVar(f"{key}_row_{row_start.x}_has_dyed_mine")
                has_dyed_nonmine = model.NewBoolVar(f"{key}_row_{row_start.x}_has_dyed_nonmine")
                has_undyed_mine = model.NewBoolVar(f"{key}_row_{row_start.x}_has_undyed_mine")
                has_undyed_nonmine = model.NewBoolVar(f"{key}_row_{row_start.x}_has_undyed_nonmine")

                # 逐格子建立约束
                for pos in row_positions:
                    var = board.get_variable(pos)
                    dye = board.get_dyed(pos)

                    if dye:
                        # 染色格子
                        # 染色雷
                        tmp_mine = model.NewBoolVar(f"{key}_tmp_dyed_mine_{pos.x}_{pos.y}")
                        model.Add(tmp_mine == var).OnlyEnforceIf(s)
                        model.AddImplication(tmp_mine, has_dyed_mine).OnlyEnforceIf(s)

                        # 染色非雷
                        tmp_nonmine = model.NewBoolVar(f"{key}_tmp_dyed_nonmine_{pos.x}_{pos.y}")
                        model.Add(tmp_nonmine == var.Not()).OnlyEnforceIf(s)
                        model.AddImplication(tmp_nonmine, has_dyed_nonmine).OnlyEnforceIf(s)
                    else:
                        # 非染色格子
                        # 非染色雷
                        tmp_mine = model.NewBoolVar(f"{key}_tmp_undyed_mine_{pos.x}_{pos.y}")
                        model.Add(tmp_mine == var).OnlyEnforceIf(s)
                        model.AddImplication(tmp_mine, has_undyed_mine).OnlyEnforceIf(s)

                        # 非染色非雷
                        tmp_nonmine = model.NewBoolVar(f"{key}_tmp_undyed_nonmine_{pos.x}_{pos.y}")
                        model.Add(tmp_nonmine == var.Not()).OnlyEnforceIf(s)
                        model.AddImplication(tmp_nonmine, has_undyed_nonmine).OnlyEnforceIf(s)

                # 禁止四种类型同时存在
                model.AddBoolOr([
                    has_dyed_mine.Not(),
                    has_dyed_nonmine.Not(),
                    has_undyed_mine.Not(),
                    has_undyed_nonmine.Not()
                ]).OnlyEnforceIf(s)