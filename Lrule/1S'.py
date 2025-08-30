# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 14:43
# @Author  : Wu_RH
# @FileName: 1S.py
"""
[1S'] 衔尾蛇：所有雷构成一条蛇。蛇是一条宽度为 1 的四连通路径，不存在分叉、环、交叉, 蛇的头尾相连
"""
from ....abs.Lrule import AbstractMinesRule

from .connect import connect


class Rule1S(AbstractMinesRule):
    name = ["1S'", "衔尾蛇"]
    doc = "所有雷构成一条蛇。蛇是一条宽度为 1 的四连通路径，不存在分叉、环、交叉, 蛇的头尾相连"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=1,
            switch=s,
        )

        for pos, var in board(mode="variable"):
            var_list = board.batch(pos.neighbors(1), mode="variable", drop_none=True)
            model.Add(sum(var_list) == 2).OnlyEnforceIf([var, s])
