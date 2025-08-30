# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 14:43
# @Author  : Wu_RH
# @FileName: 1S.py
"""
[1K1S] 马步蛇 (Snake)：所有雷构成一条蛇。蛇是一条宽度为 1 的马步连通路径，不存在分叉、环、交叉
"""
from ....abs.Lrule import AbstractMinesRule

from .connect import connect


class Rule1S(AbstractMinesRule):
    name = ["1K1S", "马步蛇", "Knight-Snake"]
    doc = "所有雷构成一条蛇。蛇是一条宽度为 1 的马步连通路径，不存在分叉、环、交叉"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=(5, 5),
            switch=s,
        )

        tmp_list = []
        for pos, var in board(mode="variable"):
            tmp_bool = model.NewBoolVar("tmp")
            var_list = board.batch(pos.neighbors(5, 5), mode="variable", drop_none=True)
            model.Add(sum(var_list) < 3).OnlyEnforceIf([var, s])
            model.Add(sum(var_list) == 1).OnlyEnforceIf([tmp_bool, s])
            model.Add(var == 1).OnlyEnforceIf([tmp_bool, s])
            tmp_list.append(tmp_bool)
        model.Add(sum(tmp_list) == 2).OnlyEnforceIf(s)
