# !/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/24 16:14
# @Author  : DeepSeek Agent
# @FileName: 4M.py
"""
[4M] 美杜莎 (Medusa)：雷组成一条蛇，蛇头（其中一端）前方所有格均不是雷
"""
from typing import List, Tuple, Dict, Any
from minesweepervariants.board import Board, Position
from minesweepervariants.abs.Lrule import AbstractMinesRule


class Rule4M(AbstractMinesRule):
    id = "4M"
    aliases = ("Medusa",)
    name = "Medusa"
    name.zh_CN = "美杜莎"
    doc = "The mines form a snake, and the cells in front of the snake's head (one end) are not mines."
    doc.zh_CN = "雷组成一条蛇，蛇头（其中一端）前方所有格均不是雷"
    tags = ["Original", "Connectivity", "Construction", "Global"]
    creation_time = "2026-07-24"
    author = ("DeepSeek Agent", 0)

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

    def nei_pos(self, board: Board, pos: Position) -> List[Position]:
        """返回与pos四连通（上下左右）的相邻位置"""
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
        """
        实现蛇约束 + 美杜莎约束：
        1. 所有雷构成一条四连通路径（蛇），无分叉、环、交叉
        2. 蛇的其中一个端点（蛇头）的前方所有格均不是雷
        """
        model = board.get_model()
        s = switch.get(model, self)
        # 强制该规则开关为真，确保约束生效
        model.add(s == 1)

        # 收集所有交互式位置及其雷变量，同时保存key
        positions = []  # 列表元素为 (key, pos, var)
        for k in board.get_interactive_keys():
            for pos, var in board(key=k, mode="variable"):
                positions.append((k, pos, var))
        n = len(positions)
        if n < 2:
            return

        # ---------- 1. 构建路径约束（蛇） ----------
        arcs, arc_var = [], {}
        for i, (k1, p1, mv1) in enumerate(positions):
            va = model.new_bool_var(f"4M_{i}_root")
            vb = model.new_bool_var(f"4M_root_{i}")
            arc_var[i, n] = va
            arc_var[n, i] = vb
            arcs.append((i, n, va))
            arcs.append((n, i, vb))
            model.add(va == 0).OnlyEnforceIf(mv1.Not())
            model.add(vb == 0).OnlyEnforceIf(mv1.Not())

            for j, (k2, p2, mv2) in enumerate(positions):
                if i != j and p2 in self.nei_pos(board, p1):
                    v = model.new_bool_var(f'4M_{i}_{j}')
                    arc_var[i, j] = v
                    arcs.append((i, j, v))
                    model.add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.add(v == 0).OnlyEnforceIf(mv2.Not())

        for i, (_, _, mv) in enumerate(positions):
            arcs.append((i, i, mv.Not()))
        arcs.append((n, n, False))

        model.add_circuit(arcs).OnlyEnforceIf(s)

        # ---------- 2. 度约束 + 端点标记 + 蛇头选择 + 美杜莎约束 ----------
        # 遍历所有位置，为每个位置创建端点指示变量和蛇头指示变量
        endpoint_vars = []      # 收集所有端点变量
        head_vars = []          # 收集所有蛇头变量
        # 存储每个位置的 (端点变量, 蛇头变量, 位置, 雷变量)
        pos_info = []

        for k, pos, var in positions:
            # 端点指示变量：该位置是端点（雷格且恰好有1个雷邻居）
            is_endpoint = model.new_bool_var(f"4M_endpoint_{pos}")
            endpoint_vars.append(is_endpoint)

            # 蛇头指示变量：该位置是蛇头（必须是端点）
            is_head = model.new_bool_var(f"4M_head_{pos}")
            head_vars.append(is_head)
            # 只有端点才可能是蛇头
            model.add(is_head == 0).OnlyEnforceIf(is_endpoint.Not())

            pos_info.append((k, pos, var, is_endpoint, is_head))

            # 获取该位置的雷邻居变量列表（四连通）
            neighbor_vars = board.batch(self.nei_pos(board, pos), mode="variable", drop_none=True)
            neighbor_count = sum(neighbor_vars)

            # 度约束：
            # - 如果是雷格，则邻居数在1~2之间
            # - 如果是端点（邻居数=1），则is_endpoint为True
            model.add(neighbor_count > 0).OnlyEnforceIf([var, s])
            model.add(neighbor_count < 3).OnlyEnforceIf([var, s])
            model.add(neighbor_count == 1).OnlyEnforceIf([is_endpoint, s])
            model.add(var == 1).OnlyEnforceIf([is_endpoint, s])

        # 恰好有2个端点
        model.add(sum(endpoint_vars) == 2).OnlyEnforceIf(s)

        # 恰好有1个蛇头
        model.add(sum(head_vars) == 1).OnlyEnforceIf(s)

        # ---------- 3. 美杜莎约束：蛇头的前方所有格均不是雷 ----------
        # 对于每个位置，如果它是蛇头，则沿远离其唯一雷邻居的方向上的所有格子都不是雷
        for k, pos, var, is_endpoint, is_head in pos_info:
            # 获取该位置的邻居位置列表
            neighbors = self.nei_pos(board, pos)
            for nb_pos in neighbors:
                # 获取邻居的雷变量
                nb_var = board.get_variable(nb_pos)
                if nb_var is None:
                    continue
                # 计算从nb_pos指向pos的方向向量
                dx = pos.col - nb_pos.col
                dy = pos.row - nb_pos.row
                # 确保是四连通方向（距离为1）
                if abs(dx) + abs(dy) != 1:
                    continue
                # 沿着该方向的所有前方格（不包括pos本身）
                step = 1
                while True:
                    front_col = pos.col + dx * step
                    front_row = pos.row + dy * step
                    front_pos = Position(front_col, front_row, k)
                    if not board.is_valid(front_pos):
                        break
                    front_var = board.get_variable(front_pos)
                    if front_var is not None:
                        # 约束：如果该位置是蛇头，且该邻居是雷，则前方格不是雷
                        model.add(front_var == 0).OnlyEnforceIf([is_head, nb_var, s])
                    step += 1
