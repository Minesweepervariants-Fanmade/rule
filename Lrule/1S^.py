# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 14:43
# @Author  : Wu_RH
# @FileName: 1S.py
"""
[1S^] 双头蛇：所有雷构成一条双头蛇。蛇是一条宽度为 1 的四连通路径，不存在环、交叉, 只存在一个分叉
"""
from ....abs.Lrule import AbstractMinesRule

from .connect import connect


class Rule1S(AbstractMinesRule):
    name = ["1S^", "双头蛇"]
    doc = "所有雷构成一条双头蛇。蛇是一条宽度为 1 的四连通路径，不存在环、交叉, 只存在一个分叉"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=1,
            switch=s
        )

        tmp_list_a = []
        tmp_list_b = []
        for pos, var in board(mode="variable"):
            tmp_bool_a = model.NewBoolVar("tmp")
            tmp_bool_b = model.NewBoolVar("tmp")
            var_list = board.batch(pos.neighbors(1), mode="variable", drop_none=True)
            model.Add(sum(var_list) == 2).OnlyEnforceIf([var, tmp_bool_a.Not(), tmp_bool_b.Not(), s])
            model.Add(sum(var_list) == 1).OnlyEnforceIf([tmp_bool_a, s])
            model.Add(var == 1).OnlyEnforceIf([tmp_bool_a, s])
            model.Add(sum(var_list) == 3).OnlyEnforceIf([tmp_bool_b, s])
            model.Add(var == 1).OnlyEnforceIf([tmp_bool_b, s])
            tmp_list_a.append(tmp_bool_a)
            tmp_list_b.append(tmp_bool_b)
        model.Add(sum(tmp_list_a) == 3).OnlyEnforceIf(s)
        model.Add(sum(tmp_list_b) == 1).OnlyEnforceIf(s)

    @classmethod
    def method_choose(cls) -> int:
        return 1
