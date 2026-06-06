# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 14:43
# @Author  : Wu_RH
# @FileName: 1S.py
"""
[1S] 蛇 (Snake)：所有雷构成一条蛇。蛇是一条宽度为 1 的四连通路径，不存在分叉、环、交叉
"""
from minesweepervariants.board import Board, Position
from minesweepervariants.abs.Lrule import AbstractMinesRule


class Rule1S(AbstractMinesRule):
    id = "1S"
    aliases = ("S",)
    name = "Snake"
    name.zh_CN = "蛇"
    doc = "All mines form a snake. A snake is a width-1 orthogonal path without branches, loops or intersections"
    doc.zh_CN = "所有雷构成一条蛇。蛇是一条宽度为 1 的四连通路径，不存在分叉、环、交叉"
    tags = ["Original", "Connectivity", "Construction", "Global"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.nei_values = []
        if data is None:
            self.nei_values = [tuple([1])]
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

    def nei_pos(self, board: Board, pos: Position):
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

        tmp_list = []
        for pos, var in board(mode="variable"):
            tmp_bool = model.new_bool_var("tmp")
            var_list = board.batch(self.nei_pos(board, pos), mode="variable", drop_none=True)
            model.add(sum(var_list) > 0).OnlyEnforceIf([var, s])
            model.add(sum(var_list) < 3).OnlyEnforceIf([var, s])
            model.add(sum(var_list) == 1).OnlyEnforceIf([tmp_bool, s])
            model.add(var == 1).OnlyEnforceIf([tmp_bool, s])
            tmp_list.append(tmp_bool)
        model.add(sum(tmp_list) == 2).OnlyEnforceIf(s)
