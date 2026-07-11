#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/03/01 13:28
# @Author  : 小小神中医 (3086842243)
# @FileName: 3C~.py
"""
[3C~]行失衡（Row Imbalance）: 每行雷数各不相同
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, MASTER_BOARD_KEY
from minesweepervariants.impl.summon.solver import Switch


class Rule3C_Tilde(AbstractMinesRule):
    id = "3C~"
    name = "Row Imbalance"
    name.zh_CN = "行失衡"
    doc = "Each row has a different number of mines"
    doc.zh_CN = "每行雷数各不相同"
    tags = ["Creative", "Global"]
    creation_time = "2026-03-01"
    author = ("小小神中医", 3086842243)

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        # 获取主板的尺寸信息
        cols, rows = board.get_config(config_name="size", board_key=MASTER_BOARD_KEY)

        # 获取每个位置上的雷变量
        # board(mode="var") 返回 (位置, 变量) 的迭代器
        vars_by_row = [[] for _ in range(rows)]
        for pos, var in board(mode="var"):
            if pos.row < rows:
                vars_by_row[pos.row].append(var)

        # 为每行创建一个变量表示该行的雷数
        row_mine_counts = []
        for r in range(rows):
            row_sum = model.NewIntVar(0, cols, f"row_mine_count_{r}")
            model.Add(row_sum == sum(vars_by_row[r]))
            row_mine_counts.append(row_sum)

        # 保证所有行的雷数互不相同
        model.AddAllDifferent(row_mine_counts)
