#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 20:00
# @Author  : Wu_RH
# @FileName: 3C.py
"""
[3C]连通（Connected）: 每个雷周围八格中恰有两个雷
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class Rule3C(AbstractMinesRule):
    name = ["3C", "连通", "Connected"]
    doc = "每个雷周围八格中恰有两个雷"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="var"):
            var_list = board.batch(pos.neighbors(2), mode="var", drop_none=True)
            model.Add(sum(var_list) == 2).OnlyEnforceIf([var, s])
