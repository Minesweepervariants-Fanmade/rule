# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/06 07:03
# @Author  : NT (2201963934)
# @FileName: 5S.py
"""
[5S] 5步蛇：蛇恰好有5段直线段
"""
from minesweepervariants.board import Board, Position
from minesweepervariants.abs.Lrule import AbstractMinesRule


class Rule5S(AbstractMinesRule):
    id = "5S"
    aliases = ("5StepSnake",)
    name = "5-Step Snake"
    name.zh_CN = "5步蛇"
    doc = "The snake has exactly 5 straight segments"
    doc.zh_CN = "蛇恰好有5段直线段"
    tags = ["Original", "Connectivity", "Construction", "Global"]
    creation_time = "2026-04-22"
    author = ("NT", 2201963934)

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

        # --- 1. 电路约束：确保所有雷格形成一条简单路径（无分支、无环） ---
        arcs, arc_var = [], {}
        for i, (k1, p1, mv1) in enumerate(positions):
            va = model.new_bool_var(f"5S_{i}_root")
            vb = model.new_bool_var(f"5S_root_{i}")
            arc_var[(i, n)] = va
            arc_var[(n, i)] = vb
            arcs.append((i, n, va))
            arcs.append((n, i, vb))
            model.add(va == 0).OnlyEnforceIf(mv1.Not())
            model.add(vb == 0).OnlyEnforceIf(mv1.Not())
            for j, (k2, p2, mv2) in enumerate(positions):
                if i != j and p2 in self.nei_pos(board, p1):
                    v = model.new_bool_var(f'5S_{i}_{j}')
                    arc_var[(i, j)] = v
                    arcs.append((i, j, v))
                    model.add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.add(v == 0).OnlyEnforceIf(mv2.Not())

        # 自环跳过非雷格节点
        for i, (_, _, mv) in enumerate(positions):
            arcs.append((i, i, mv.Not()))
        arcs.append((n, n, False))

        model.add_circuit(arcs).OnlyEnforceIf(s)

        # --- 2. 度数约束：每个雷格有1或2个邻居，恰好2个端点 ---
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

        # --- 3. 拐点计数：确保恰好4个拐点（5段直线段） ---
        # 对于每个雷格，检查其四个方向的邻居（只考虑同一题板）
        turn_vars = []
        for k, p, var in positions:
            # 获取四个方向的雷变量（如果存在且有效）
            up_pos = p.up()
            down_pos = p.down()
            left_pos = p.left()
            right_pos = p.right()
            up_var = board.get_variable(up_pos) if board.is_valid(up_pos) and up_pos.board_key == k else None
            down_var = board.get_variable(down_pos) if board.is_valid(down_pos) and down_pos.board_key == k else None
            left_var = board.get_variable(left_pos) if board.is_valid(left_pos) and left_pos.board_key == k else None
            right_var = board.get_variable(right_pos) if board.is_valid(right_pos) and right_pos.board_key == k else None

            # 四种垂直方向组合：上+左，上+右，下+左，下+右
            combos = [(up_var, left_var), (up_var, right_var),
                      (down_var, left_var), (down_var, right_var)]
            for d1, d2 in combos:
                if d1 is not None and d2 is not None:
                    combo_var = model.new_bool_var(f"turn_{k}_{p.row}_{p.col}")
                    # combo_var == 1 当且仅当 var=1, d1=1, d2=1
                    model.add(combo_var == 1).OnlyEnforceIf([var, d1, d2])
                    model.add(combo_var == 0).OnlyEnforceIf(var.Not())
                    model.add(combo_var == 0).OnlyEnforceIf(d1.Not())
                    model.add(combo_var == 0).OnlyEnforceIf(d2.Not())
                    turn_vars.append(combo_var)

        # 恰好4个拐点 (5段直线段)
        if turn_vars:
            model.add(sum(turn_vars) == 4).OnlyEnforceIf(s)
