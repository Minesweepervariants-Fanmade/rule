#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[5L] 回路: 雷格八连通构成哈密顿回路
"""
from ....abs.Lrule import AbstractMinesRule


class Rule5L(AbstractMinesRule):
    id = "5L"
    name = "Circuit"
    name.zh_CN = "回路"
    doc = "All mine cells form a Hamiltonian circuit via 8-connectivity"
    doc.zh_CN = "雷格八连通构成哈密顿回路"
    tags = ["Variant", "Connectivity", "Global"]
    creation_time = "2026-05-05"
    author = ("NT", 2201963934)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)
        positions = [(k, p, v) for k in board.get_interactive_keys() for p, v in board(key=k, mode="variable")]
        n = len(positions)
        if n < 2:
            return

        # 边变量：八连通且两端都是雷格
        arcs, arc_var = [], {}
        for i, (k1, p1, mv1) in enumerate(positions):
            for j, (k2, p2, mv2) in enumerate(positions):
                if i != j and p2 in p1.neighbors(2):
                    v = model.NewBoolVar(f'5L_{i}_{j}')
                    arc_var[i, j] = v
                    arcs.append((i, j, v))
                    model.Add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.Add(v == 0).OnlyEnforceIf(mv2.Not())

        # 自环跳过非雷格节点
        for i, (_, _, mv) in enumerate(positions):
            arcs.append((i, i, mv.Not()))

        model.AddCircuit(arcs).OnlyEnforceIf(s)