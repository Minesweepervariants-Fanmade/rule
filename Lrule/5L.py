#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[5L] 回路: 雷格八连通构成哈密顿回路
"""
from minesweepervariants.position import Position

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

    def __init__(self, board: "Board" = None, data=None) -> None:
        self.invert = False
        super().__init__(board, data)
        self.nei_values = []
        if data is None:
            self.nei_values = [tuple([1, 2])]
            return
        if data[0]=='~':
            self.invert = True
            data = data[1:]
        nei_values = data.split(";")
        for nei_value in nei_values:
            if ":" in nei_value:
                self.nei_values.append(tuple([
                    int(nei_value.split(":")[0]),
                    int(nei_value.split(":")[1])
                ]))
            else:
                self.nei_values.append(tuple([int(nei_value)]))

    def nei_pos(self, pos: Position):
        positions = []
        for nei_value in self.nei_values:
            if len(nei_value) == 1:
                positions.extend(
                    pos.neighbors(nei_value[0], nei_value[0])
                )
            elif len(nei_value) == 2:
                positions.extend(
                    pos.neighbors(nei_value[0], nei_value[1])
                )
        return positions

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
            if self.invert:
                mv1 = mv1.Not()
            for j, (k2, p2, mv2) in enumerate(positions):
                if self.invert:
                    mv2 = mv2.Not()
                if i != j and p2 in self.nei_pos(p1):
                    v = model.new_bool_var(f'5L_{i}_{j}')
                    arc_var[i, j] = v
                    arcs.append((i, j, v))
                    model.add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.add(v == 0).OnlyEnforceIf(mv2.Not())

        # 自环跳过非雷格节点
        for i, (_, _, mv) in enumerate(positions):
            if self.invert:
                mv = mv.Not()
            arcs.append((i, i, mv.Not()))

        model.add_circuit(arcs).OnlyEnforceIf(s)