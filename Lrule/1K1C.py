#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:13
# @Author  : Wu_RH
# @FileName: 1C.py
"""
[1K1C] 马步八连通 (Knight-Connected)：雷区域马步连通
"""
from ....abs.Lrule import AbstractMinesRule
from ....utils.impl_obj import get_total

from .connect import connect


class Rule1C(AbstractMinesRule):
    name = ["1K1C", "马步八连通", "Knight-Connected"]
    doc = "雷区域马步连通"

    def create_constraints(self, board, switch):
        model = board.get_model()
        connect(
            ub=get_total() // 2 + 1,
            model=model,
            board=board,
            connect_value=1,
            nei_value=(5, 5),
            switch=switch.get(model, self),
        )
