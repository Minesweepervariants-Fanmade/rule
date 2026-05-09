#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/13 23:00
# @Author  : Wu_RH
# @FileName: 3P.py
"""
[3P]游行(Parade):可以通过骑士的移动方式，从某一个雷格开始，在只经过雷格的情况下，不重复且不遗漏地通过所有雷格
[3P]游行(Parade):可以通过雷与该雷马步格的雷链接的图形成哈密顿路径
[3P]游行(Parade):可以通过从某格雷出发每次走马步格随后一笔画完所有雷
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger


class Rule3P(AbstractMinesRule):
    id = "3P"
    name = "Parade"
    name.zh_CN = "游行"
    doc = "Starting from any mine cell, can traverse all mine cells without repetition or omission using knight moves"
    doc.zh_CN = "可以通过骑士的移动方式，从某一个雷格开始，在只经过雷格的情况下，不重复且不遗漏地通过所有雷格"
    tags = ["Creative", "Connectivity", "Construction", "Global", "Extensive Trial"]
    creation_time = "2025-08-14"
    author = ("对映", 3242525312)

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.nei_values = []
        if data is None:
            self.nei_values = [tuple([5])]
            return
        nei_values = data.split(";")
        for nei_value in nei_values:
            if ":" in nei_value:
                self.nei_values.append(tuple([
                    int(nei_value.split(":")[0]),
                    int(nei_value.split(":")[1])
                ]))
            else:
                self.nei_values.append(tuple([int(nei_value)]))

    def nei_pos(self, board: AbstractBoard, pos: AbstractPosition):
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
        return [pos for pos in positions if board.is_valid(pos)]

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        positions = [(k, p, v) for k in board.get_interactive_keys() for p, v in board(key=k, mode="variable")]
        n = len(positions)
        if n < 2:
            return

        # 边变量：八连通且两端都是雷格
        arcs, arc_var = [], {}
        for i, (k1, p1, mv1) in enumerate(positions):
            va = model.new_bool_var(f"3P_{i}_root")
            vb = model.new_bool_var(f"3P_root_{i}")
            arc_var[i, n] = va
            arc_var[n, i] = vb
            arcs.append((i, n, va))
            arcs.append((n, i, vb))
            model.add(va == 0).OnlyEnforceIf(mv1.Not())
            model.add(vb == 0).OnlyEnforceIf(mv1.Not())
            for j, (k2, p2, mv2) in enumerate(positions):
                if i != j and p2 in self.nei_pos(board, p1):
                    v = model.new_bool_var(f'3P_{i}_{j}')
                    arc_var[i, j] = v
                    arcs.append((i, j, v))
                    model.add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.add(v == 0).OnlyEnforceIf(mv2.Not())

        # 自环跳过非雷格节点
        for i, (_, _, mv) in enumerate(positions):
            arcs.append((i, i, mv.Not()))
        arcs.append((n, n, False))

        model.add_circuit(arcs).OnlyEnforceIf(s)
