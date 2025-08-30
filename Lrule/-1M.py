#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/13 00:30
# @Author  : Wu_RH
# @FileName: -1M.py
"""
[*1M]: 雷分布将随机按照下述方式对称 [水平/垂直/对角/副对角/中心/旋转90度]对称
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rulen1M(AbstractMinesRule):
    name = ["*1M", "镜像", "Mirror"]
    doc = "雷分布将随机按照下述方式对称 [水平/垂直/对角/副对角/中心]对称"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        tmp_a = model.NewBoolVar("[*1M]")      # 垂直对称
        tmp_b = model.NewBoolVar("[*1M]")      # 水平对称
        tmp_c = model.NewBoolVar("[*1M]")      # 正斜角对称
        tmp_d = model.NewBoolVar("[*1M]")      # 副斜角对称
        tmp_e = model.NewBoolVar("[*1M]")      # 中心对称

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            for index_x in range(pos_bound.x + 1):
                for index_y in range(pos_bound.y + 1):
                    var = board.get_variable(board.get_pos(index_x, index_y, key))
                    if var is None:
                        continue
                    var_a = board.get_variable(board.get_pos(index_x, pos_bound.y-index_y, key))
                    var_b = board.get_variable(board.get_pos(pos_bound.x-index_x, index_y, key))
                    var_c = board.get_variable(board.get_pos(pos_bound.y-index_y, pos_bound.x-index_x, key))
                    var_d = board.get_variable(board.get_pos(index_y, index_x, key))
                    var_e = board.get_variable(board.get_pos(pos_bound.x-index_x, pos_bound.y-index_y, key))
                    if var_a is not None: model.Add(var == var_a).OnlyEnforceIf(tmp_a)
                    if var_b is not None: model.Add(var == var_b).OnlyEnforceIf(tmp_b)
                    if var_c is not None: model.Add(var == var_c).OnlyEnforceIf(tmp_c)
                    if var_d is not None: model.Add(var == var_d).OnlyEnforceIf(tmp_d)
                    if var_e is not None: model.Add(var == var_e).OnlyEnforceIf(tmp_e)

        model.AddBoolOr([tmp_a, tmp_b, tmp_c, tmp_d, tmp_e]).OnlyEnforceIf(s)
