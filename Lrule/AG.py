#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/09/01 22:38:05
# @Author  : botif (1643337042)
# @FileName: AG.py
"""
[AG] 银河: 四连通雷区为中心对称图形

实现策略：
1. 使用 connect 函数获取每个雷格所属的四连通分量 ID
2. 对于每个分量，枚举所有可能的整数中心点 (cr, cc)，其中 0 <= cr < rows, 0 <= cc < cols
3. 对于每个中心点，约束该分量关于该中心对称
4. 每个存在的分量必须至少关于一个中心对称
"""

from typing import List

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position
from .connect import connect


class RuleAG(AbstractMinesRule):
    id = "AG"
    name = "Galaxy"
    name.zh_CN = "银河"
    doc = "Each 4-connected mine region is centrally symmetric."
    doc.zh_CN = "四连通雷区为中心对称图形"
    author = ("botif", 1643337042)
    tags = ["Creative", "Global", "Connectivity", "Strict Shape"]
    creation_time = "2026-09-01"

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            # 收集所有位置和变量
            positions_vars = [
                (pos, board.get_variable(pos, special='raw'))
                for pos, _ in board(key=key, mode='obj', special='raw')
                if board.get_variable(pos, special='raw') is not None
            ]
            if not positions_vars:
                continue

            pos_list, var_list = zip(*positions_vars)
            n = len(pos_list)
            pos_to_idx = {pos: i for i, pos in enumerate(pos_list)}

            # 获取边界信息
            bound = board.boundary(key)
            rows = bound.row + 1
            cols = bound.col + 1

            # 使用 connect 函数获取分量 ID
            component_ids = connect(
                model=model,
                board=board,
                switch=s,
                component_num=None,
                connect_value=1,
                nei_value=1,
                positions_vars=positions_vars,
                special='raw'
            )

            # 对于每个可能的分量 ID
            for comp_id in range(n):
                # 创建该分量存在的布尔变量
                comp_exists = model.NewBoolVar(f'AG_comp_exists_{key}_{comp_id}')

                # 为每个位置创建 active 变量：该位置属于该分量且是雷
                active_vars = []
                for i, pos in enumerate(pos_list):
                    in_comp = model.NewBoolVar(f'AG_in_comp_{key}_{comp_id}_{i}')
                    model.Add(component_ids[i] == comp_id).OnlyEnforceIf([in_comp, s])
                    model.Add(component_ids[i] != comp_id).OnlyEnforceIf([in_comp.Not(), s])

                    active = model.NewBoolVar(f'AG_active_{key}_{comp_id}_{i}')
                    model.Add(active <= var_list[i]).OnlyEnforceIf(s)
                    model.Add(active <= in_comp).OnlyEnforceIf(s)
                    model.Add(active >= var_list[i] + in_comp - 1).OnlyEnforceIf(s)
                    active_vars.append(active)

                # 分量存在当且仅当至少有一个 active 为真
                model.AddBoolOr(active_vars).OnlyEnforceIf([comp_exists, s])
                model.AddBoolAnd([v.Not() for v in active_vars]).OnlyEnforceIf([comp_exists.Not(), s])

                # 枚举所有可能的整数中心点
                sym_choices = []
                for cr in range(rows):
                    for cc in range(cols):
                        is_sym = model.NewBoolVar(f'AG_sym_{key}_{comp_id}_{cr}_{cc}')
                        sym_choices.append(is_sym)

                        # 对于分量中的每个格子，检查其对称点
                        for i, pos in enumerate(pos_list):
                            active = active_vars[i]
                            r, c = pos.row, pos.col
                            sr, sc = 2 * cr - r, 2 * cc - c

                            if 0 <= sr < rows and 0 <= sc < cols:
                                # 对称点在棋盘内，找到其索引
                                sym_idx = None
                                for j, p in enumerate(pos_list):
                                    if p.row == sr and p.col == sc:
                                        sym_idx = j
                                        break

                                if sym_idx is not None:
                                    sym_active = active_vars[sym_idx]
                                    # 约束：如果 is_sym 为真，则 active 和 sym_active 必须相等
                                    model.Add(active == sym_active).OnlyEnforceIf([is_sym, s])
                                else:
                                    # 对称点是被掩码的格子，不能有雷
                                    model.Add(active == 0).OnlyEnforceIf([is_sym, s])
                            else:
                                # 对称点在棋盘外，不能有雷
                                model.Add(active == 0).OnlyEnforceIf([is_sym, s])

                # 如果分量存在，则必须至少关于一个中心对称
                if sym_choices:
                    model.AddBoolOr(sym_choices).OnlyEnforceIf([comp_exists, s])

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        info["soft_fn"](int(ub * 0.4), 0)
