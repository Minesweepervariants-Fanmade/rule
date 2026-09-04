#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/09/04
# @Author  : QuirkyStorm7988（备战高考） (2943562293)
# @FileName: 325.py
"""
[325] 已完成今日325大学习
"""

from ....abs.Lrule import AbstractMinesRule


class Rule325(AbstractMinesRule):
    id = "325"
    aliases = ()
    name = "325"
    name.zh_CN = "三二五"
    doc = "已完成今日325大学习"
    doc.zh_CN = "已完成今日325大学习"
    author = ("QuirkyStorm7988（备战高考）", 2943562293)
    tags = ["Creative", "WIP", "Local"]
    creation_time = "2026-08-01"

    def create_constraints(self, board, switch):
        """
        该规则无任何约束，仅作占位。
        """
        # 获取规则开关变量（框架要求）
        model = board.get_model()
        _ = switch.get(model, self)
        # 不添加任何约束，直接返回
        return
