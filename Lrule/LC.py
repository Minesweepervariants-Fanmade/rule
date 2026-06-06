#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/05
# @Author  : NT (2201963934)
# @FileName: LC.py
"""
[LC] 圈地：所有雷格都在一个八联通雷格环上或其内部

雷格要么"在环上"要么"在环内", 非雷格要么"在环外"要么"在环内".
"在环上"的雷格的八连通图是哈密顿图.
"在环内"的雷格周围四格没有"在环外"的非雷格.
非雷"在环外"当且仅当其与题板外四联通.
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from ....impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel


class RuleLC(AbstractMinesRule):
    id = "LC"
    name = "Land Claim"
    name.zh_CN = "圈地"
    doc = "All mine cells are on or inside an 8-connected mine ring"
    doc.zh_CN = "所有雷格都在一个八联通雷格环上或其内部"
    tags = ["Variant", "Connectivity", "Global"]
    creation_time = "2026-05-05"
    author = ("NT", 2201963934)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 状态变量: on_ring, inside_ring, outside_ring
        on_ring = {}
        inside_ring = {}
        outside_ring = {}
        mine_vars = {}

        # 初始化变量
        for key in board.get_interactive_keys():
            for pos, var in board(key=key, mode="variable"):
                on_ring[pos] = model.NewBoolVar(f'LC_on_ring_{pos}')
                inside_ring[pos] = model.NewBoolVar(f'LC_inside_{pos}')
                outside_ring[pos] = model.NewBoolVar(f'LC_outside_{pos}')
                mine_vars[pos] = var

        # 每个格子恰好处于一种状态
        for key in board.get_interactive_keys():
            for pos, var in board(key=key, mode="variable"):
                model.Add(on_ring[pos] + inside_ring[pos] + outside_ring[pos] == 1).OnlyEnforceIf(s)

        # 雷格只能在环上或环内, 非雷格不能在环上
        for key in board.get_interactive_keys():
            for pos, var in board(key=key, mode="variable"):
                model.Add(outside_ring[pos] == 0).OnlyEnforceIf([var, s])
                model.Add(on_ring[pos] == 0).OnlyEnforceIf([var.Not(), s])

        # === 非雷"在环外"约束 ===
        # 边界上的非雷格：与题板外四联通，直接为环外
        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            for pos, var in board(key=key, mode="variable"):
                on_boundary = (pos.x == 0 or pos.x == boundary.x or
                              pos.y == 0 or pos.y == boundary.y)
                if on_boundary:
                    # 边界非雷格是环外
                    model.Add(outside_ring[pos] == 1).OnlyEnforceIf([var.Not(), s])

        # 非边界非雷格的环外约束
        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            for pos, var in board(key=key, mode="variable"):
                on_boundary = (pos.x == 0 or pos.x == boundary.x or
                              pos.y == 0 or pos.y == boundary.y)
                if on_boundary:
                    continue  # 边界非雷格已在上面处理

                # 检查四个四邻域
                nb_outside_vars = []
                for d in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb_pos = board.get_pos(pos.x + d[0], pos.y + d[1], key)
                    if nb_pos is not None and nb_pos in outside_ring:
                        nb_outside_vars.append(outside_ring[nb_pos])

                if nb_outside_vars:
                    # outside_ring[pos] == OR(邻域outside状态)
                    model.AddBoolOr([outside_ring[pos].Not()] + nb_outside_vars).OnlyEnforceIf([var.Not(), s])
                    model.AddBoolAnd([nb.Not() for nb in nb_outside_vars]).OnlyEnforceIf([outside_ring[pos].Not(), var.Not(), s])
                else:
                    # 没有有效邻域（非边界角落），则不能是环外
                    model.Add(outside_ring[pos] == 0).OnlyEnforceIf([var.Not(), s])

        # === 雷格"在环内"约束 ===
        # "在环内"的雷格周围四格没有"在环外"的非雷格 (单向: 环内 → 周围无环外非雷)
        for key in board.get_interactive_keys():
            for pos, var in board(key=key, mode="variable"):
                nbs_outside = []
                for d in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb_pos = board.get_pos(pos.x + d[0], pos.y + d[1], key)
                    if nb_pos is not None and nb_pos in outside_ring:
                        nbs_outside.append(outside_ring[nb_pos])
                if nbs_outside:
                    model.AddBoolAnd([nb.Not() for nb in nbs_outside]).OnlyEnforceIf([inside_ring[pos], var, s])

        # === 环上雷格的哈密顿圈约束（使用AddCircuit + 自环） ===
        positions = [(pos, v) for pos, v in mine_vars.items()]
        n = len(positions)
        if n >= 2:
            # 创建边变量：八连通且两端都是"环上雷格"
            arcs = []
            for i, (pos_i, var_i) in enumerate(positions):
                for j, (pos_j, var_j) in enumerate(positions):
                    if i != j and pos_j in pos_i.neighbors(2):
                        v = model.NewBoolVar(f'LC_arc_{i}_{j}')
                        # 边只有在两端都是"环上雷格"时才可能激活
                        model.Add(v == 0).OnlyEnforceIf([on_ring[pos_i].Not(), s])
                        model.Add(v == 0).OnlyEnforceIf([on_ring[pos_j].Not(), s])
                        arcs.append((i, j, v))
            # 自环跳过非环上雷格节点
            for i, (pos_i, _) in enumerate(positions):
                arcs.append((i, i, on_ring[pos_i].Not()))
            model.AddCircuit(arcs).OnlyEnforceIf(s)

        # 确保至少有一个环上雷
        model.AddBoolOr([on_ring[pos] for pos in on_ring]).OnlyEnforceIf(s)