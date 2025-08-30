#!/usr/bin/env python3

"""
[3DJ] 枣糕(Jujubecake)：所有非雷格均形成1x2x1、2x1x1或1x1x2的三维矩形，即每个非雷格恰好有一个六连通相邻的非雷格...洞里全是什么啊!!!
"""

from .. import Abstract3DMinesRule
from .....abs.board import AbstractBoard


class Rule3DJ(Abstract3DMinesRule):  # type: ignore
    name = ["3DJ", "枣糕", "Jujubecake"]
    doc = "所有非雷格均形成1x2x1、2x1x1或1x1x2的三维矩形，即每个非雷格恰好有一个六连通相邻的非雷格(全是洞啊!!!)"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            # 获取六连通邻域：同层四连通 + 上下层对应位置
            six_neighbors = self._get_six_connected_neighbors(board, pos)
            six_neighbor_vars = board.batch(six_neighbors, mode="variable", drop_none=True)

            if not six_neighbor_vars:
                # 如果没有六连通邻居，该位置必须是雷（因为非雷格需要有相邻的非雷格）
                model.Add(var == 1).OnlyEnforceIf(s)
                continue

            # 核心约束：每个非雷格恰好有1个六连通相邻的非雷格
            # 等价于：var为0时，六连通邻域中恰好有1个非雷格（即sum_vals == len(six_neighbor_vars) - 1）
            sum_vals = sum(six_neighbor_vars)  # 邻域中雷的数量
            non_mine_count = len(six_neighbor_vars) - sum_vals  # 邻域中非雷的数量

            # 当当前位置是非雷时，邻域中恰好有1个非雷
            model.Add(non_mine_count == 1).OnlyEnforceIf([var.Not(), s])

    def _get_six_connected_neighbors(self, board: 'AbstractBoard', pos):
        """获取六连通邻域：同层四连通 + 上下层对应位置"""
        neighbors = []

        # 同层四连通邻域（左右上下）
        four_neighbors = pos.neighbors(1)
        neighbors.extend(four_neighbors)

        # 上层对应位置
        up_pos = self.up(board, pos, n=1)
        if up_pos is not None:
            neighbors.append(up_pos)

        # 下层对应位置
        down_pos = self.down(board, pos, n=1)
        if down_pos is not None:
            neighbors.append(down_pos)

        return neighbors

    def suggest_total(self, info: dict):
        """建议非雷的总数应该是偶数，因为非雷成对出现"""
        def constraint_even_non_mines(model, total):
            # 获取总格子数
            total_cells = 0
            for key in info["interactive"]:
                size_info = info["size"][key]
                total_cells += size_info[0] * size_info[1]

            # 非雷数量 = 总格子数 - 雷数量
            non_mine_total = total_cells - total

            # 非雷数量应该是偶数
            model.AddModuloEquality(0, non_mine_total, 2)

        info["hard_fns"].append(constraint_even_non_mines)
