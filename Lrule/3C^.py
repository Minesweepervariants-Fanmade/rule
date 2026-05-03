#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 20:00
# @Author  : Wu_RH
# @FileName: 3C.py
"""
[3C^]连通^（Connected^）: 每个雷周围八格中雷的数量为偶数（包括0）
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class Rule3C(AbstractMinesRule):
    id = "3C^"
    name = "Connected^"
    name.zh_CN = "连通^"
    doc = "Each mine is surrounded by an even number of mines in the eight adjacent cells (including 0)"
    doc.zh_CN = "每个雷周围八格中雷的数量为偶数（包括0）"

    tags = ["Variant", "Local", "Connectivity", "Weak"]

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="var"):
            var_list = board.batch(pos.neighbors(2), mode="var", drop_none=True)
            mod_num = model.NewIntVar(0, 8, "")
            model.AddModuloEquality(0, mod_num, 2)
            model.Add(sum(var_list) == mod_num).OnlyEnforceIf([var, s])
