#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 17:13
# @Author  : Wu_RH
# @FileName: 1C.py
"""
[3D1C] 三维八连通 (Connected)：雷区域二十六连通
"""
from .. import Abstract3DMinesRule

from .connect import connect


class Rule1C(Abstract3DMinesRule):
    name = ["3D1C", "3DC", "二十六连通"]
    doc = "雷区域二十六连通"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=2,
            switch=s
        )
