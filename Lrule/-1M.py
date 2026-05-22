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
    id = "*1M"
    name = "Mirror"
    name.zh_CN = "镜像"
    doc = "Mine distribution is randomly symmetric in one of the following ways: [horizontal/vertical/diagonal/anti-diagonal/center]"
    doc.zh_CN = "雷分布将随机按照下述方式对称 [水平/垂直/对角/副对角/中心]对称"
    author = ("雾", 3140864122)
    tags = ["Creative", "Fun", "Global"]
    creation_time = "2025-08-06"
    arg_doc = ""
    arg_doc.zh_CN = "number, 作为index选择固定[水平/垂直/对角/副对角/中心]对称(从0开始)"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.choose = int(data) if data and data.isdigit() else -1

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        tmp_a = model.new_bool_var("[*1M]-0")      # 垂直对称
        tmp_b = model.new_bool_var("[*1M]-1")      # 水平对称
        tmp_c = model.new_bool_var("[*1M]-2")      # 正斜角对称
        tmp_d = model.new_bool_var("[*1M]-3")      # 副斜角对称
        tmp_e = model.new_bool_var("[*1M]-4")      # 中心对称

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
                    if var_a is not None: model.add(var == var_a).OnlyEnforceIf(tmp_a)
                    if var_b is not None: model.add(var == var_b).OnlyEnforceIf(tmp_b)
                    if var_c is not None: model.add(var == var_c).OnlyEnforceIf(tmp_c)
                    if var_d is not None: model.add(var == var_d).OnlyEnforceIf(tmp_d)
                    if var_e is not None: model.add(var == var_e).OnlyEnforceIf(tmp_e)

        if self.choose > -1:
            model.add_bool_and([tmp_a, tmp_b, tmp_c, tmp_d, tmp_e][self.choose])

        model.add_bool_or([tmp_a, tmp_b, tmp_c, tmp_d, tmp_e]).OnlyEnforceIf(s)
