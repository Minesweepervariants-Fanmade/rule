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
    id = "*1M~"
    name = "Mirror~"
    name.zh_CN = "反镜像"
    doc = ("Mine distribution is randomly symmetric-inversed in one of the following ways, except its own position:"
           " [horizontal/vertical/diagonal/anti-diagonal/center/Rotate 90 degrees] "
           "(arg: number, zero‑based index to choose fixed symmetry: "
           "[horizontal/vertical/diagonal/anti-diagonal/center/Rotate 90 degrees])")
    doc.zh_CN = ("雷分布将随机按照下述方式对称后取反 [水平/垂直/对角/副对角/中心/旋转90度]对称. 如果对称后是同一格则无限制.  "
                 "(arg: number, 作为index选择固定[水平/垂直/对角/副对角/中心/旋转90度]对称(从0开始))")
    author = ("NT", 2201963934)
    tags = ["Creative", "Fun", "Global", "Strict R"]
    creation_time = "2026-05-27"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.choose = int(data) if data and data.isdigit() else -1

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        choose_list = []
        map_fcs = [
            lambda _index_x, _index_y:      # 垂直对称       x,-y
            board.get_pos(_index_x, pos_bound.col-_index_y, key),
            lambda _index_x, _index_y:      # 水平对称       -x,y
            board.get_pos(pos_bound.row-_index_x, _index_y, key),
            lambda _index_x, _index_y:      # 正斜角对称     -y,-x
            board.get_pos(pos_bound.col-_index_y, pos_bound.row-_index_x, key),
            lambda _index_x, _index_y:      # 副斜角对称     y,x
            board.get_pos(_index_y, _index_x, key),
            lambda _index_x, _index_y:      # 中心对称       -x,-y
            board.get_pos(pos_bound.row-_index_x, pos_bound.col-_index_y, key),
            lambda _index_x, _index_y:      # 旋转90度
            board.get_pos(_index_y, pos_bound.row-_index_x, key)
        ]
        if self.choose > -1:
            map_fcs = [map_fcs[self.choose]]

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            for map_fc in map_fcs:
                tmp_var = model.new_bool_var("[*1M]")
                choose_list.append(tmp_var)
                for index_x in range(pos_bound.row + 1):
                    for index_y in range(pos_bound.col + 1):
                        var_t = board.get_variable(map_fc(index_x, index_y))
                        var = board.get_variable(board.get_pos(index_x, index_y, key))
                        if var is None:
                            continue
                        if var_t is var:
                            continue
                        if var_t is not None: model.add(var != var_t).OnlyEnforceIf(tmp_var)

        model.add_bool_or(choose_list).OnlyEnforceIf(s)
