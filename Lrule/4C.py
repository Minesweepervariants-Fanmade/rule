#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/11 17:06
# @Author  : Wu_RH
# @FileName: 4C.py
"""
[4C]十字路口(Crossing): 雷区域可以分为6组不重合的八连通蛇，使得对于题板任意两个边都可以找到1个雷组满足只与这两条边接触。
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class Rule4C(AbstractMinesRule):
    # name = ["4C", "十字路口", "Crossing"]

    def suggest_total(self, info: dict):
        def a(model, total):
            model.Add(total >= 12)
        info["hard_fns"].append(a)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        ...



