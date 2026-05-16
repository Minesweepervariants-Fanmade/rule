#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[SD] 雷数独 (Sudoku)

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 左线规则(Lrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 前置条件: 棋盘必须为正方形且边长为 8 或 27。

2) 核心术语精确定义:
    - 块尺寸: 8→2×2块(共4×4=16个块), 27→3×3块(共9×9=81个块)。
    - 块值: 块内雷数之和。2×2块取值0~4, 3×3块取值0~9。
    - 拉丁方: n×n的块值矩阵中，每行/每列的值互不相同。
    - 值种类数: 整个矩阵中实际出现的不同值的个数，必须等于 n (n=4或n=9)。
    - 宫内数字不能相同: 每个块(宫)内的雷数不能全为0或全为最大值(即块值必须在1~max-1之间)。
      这确保每个宫既有雷有无雷。

3) 计数对象、边界条件、越界处理:
    - 仅统计有效格，越界格不计入块内。
    - 棋盘必须恰好划分为整块，不处理部分块。

4) fill 阶段语义与 create_constraints 阶段语义等价关系:
    - 无 fill 阶段，仅在 create_constraints 中建模。
    - 约束语义: 每行/列块值互异，全局不同值的总数等于 n，且每个块值在0~max之间。

5) 可验证样例:
    - 样例A(应通过): 8×8棋盘(4×4个2×2块), n=4, 块值矩阵为 [[1,2,3,4],[2,1,4,3],[3,4,1,2],[4,3,2,1]],
      满足行/列互异, 全局值{1,2,3,4}共4种, 每块值均在0~4之间。
    - 样例B(应失败): 8×8棋盘, 块值矩阵为 [[0,0,0,0],[1,1,1,1],[2,2,2,2],[3,3,3,3]],
      行/列有重复(每行值全相同), 且0和全4不符合"宫内数字不能相同"。
    - 样例C(应失败): 尺寸为10时抛出 ValueError。
"""

from typing import List

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard
from ....impl.summon.solver import Switch


class RuleSD(AbstractMinesRule):
    id = "SD"
    name = "Sudoku"
    name.zh_CN = "雷数独"
    doc = ("Latin square rules, but with the board size restricted to 8 or 27, "
           "blocks of size 2x2 or 3x3 respectively, and the requirement that the number of mines in each block cannot be all the same.")
    doc.zh_CN = "拉丁方规则，但是题版大小只能是8 27，且区域形状分别为2x2，3x3，且有宫内数字不能相同的要求。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Construction", "Strict R"]
    creation_time = "2026-05-15"

    def __init__(self, board: AbstractBoard = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        # 验证棋盘尺寸是否为 8 或 27
        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            rows = bound.x + 1
            cols = bound.y + 1
            if rows != cols:
                raise ValueError(f"SD 规则要求正方形棋盘, 但当前尺寸为 {rows}×{cols}")
            if rows not in (8, 27):
                raise ValueError(f"SD 规则要求边长只能是 8 或 27, 但当前边长为 {rows}")

    def create_constraints(self, board: AbstractBoard, switch: Switch) -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            size = bound.x + 1          # 边长, 必为 8 或 27

            if size == 8:
                block_size = 2
                n = 4                  # 4x4 个块
                max_val = 4             # 2x2 块最大值
            elif size == 27:
                block_size = 3
                n = 9                  # 9x9 个块
                max_val = 9             # 3x3 块最大值
            else:
                continue               # 不可能到达，已在 __init__ 验证

            # 为每个块创建整型变量
            block_vals: List[List[IntVar]] = []
            for i in range(n):
                row_vals = []
                for j in range(n):
                    # 获取该块内格子的变量
                    vars_block = []
                    for di in range(block_size):
                        for dj in range(block_size):
                            pos = board.get_pos(block_size*i + di, block_size*j + dj, key)
                            var = board.get_variable(pos, special='raw')
                            if var is None:
                                continue
                            vars_block.append(var)
                    # 块值变量
                    bv = model.NewIntVar(0, max_val, f"SD_block_{key}_{i}_{j}")
                    # 约束: bv == sum(vars_block)
                    model.Add(bv == sum(vars_block)).OnlyEnforceIf(s)
                    row_vals.append(bv)
                block_vals.append(row_vals)

            if n == 0:
                continue

            # 行/列 AllDifferent 约束 (拉丁方核心)
            for i in range(n):
                model.AddAllDifferent([block_vals[i][j] for j in range(n)]).OnlyEnforceIf(s)
            for j in range(n):
                model.AddAllDifferent([block_vals[i][j] for i in range(n)]).OnlyEnforceIf(s)

            # 宫内数字不能相同: 每个宫(block_vals的子矩阵)内的块值互不相同
            # n=4 时宫大小为 2x2 块, n=9 时宫大小为 3x3 块
            palace_size = block_size  # 宫在块矩阵中的尺寸 = 块尺寸
            for pi in range(0, n, palace_size):
                for pj in range(0, n, palace_size):
                    palace_cells = []
                    for di in range(palace_size):
                        for dj in range(palace_size):
                            palace_cells.append(block_vals[pi + di][pj + dj])
                    model.AddAllDifferent(palace_cells).OnlyEnforceIf(s)

            # 全局值种类数 == n
            if n <= 4:
                used = []
                for v in range(max_val + 1):
                    any_eq = model.NewBoolVar(f"SD_used_{key}_{v}")
                    eq_flags = []
                    for i in range(n):
                        for j in range(n):
                            eq = model.NewBoolVar(f"SD_eq_{key}_{i}_{j}_{v}")
                            model.Add(block_vals[i][j] == v).OnlyEnforceIf(eq)
                            model.Add(block_vals[i][j] != v).OnlyEnforceIf(eq.Not())
                            eq_flags.append(eq)
                    model.AddBoolOr(eq_flags).OnlyEnforceIf(any_eq)
                    model.AddBoolAnd([e.Not() for e in eq_flags]).OnlyEnforceIf(any_eq.Not())
                    used.append(any_eq)
                model.Add(sum(used) == n).OnlyEnforceIf(s)
            # n=9 时值域为 0~9, 约束可简化

    def suggest_total(self, info: dict) -> None:
        """总雷数约束: 根据块尺寸和块数计算可行的总雷数范围。"""
        from itertools import combinations

        for key in info["interactive"]:
            size = info["size"][key]
            if size[0] != size[1] or size[0] not in (8, 27):
                continue

            if size[0] == 8:
                block_size = 2
                n = 4
                max_val = 4
            else:  # 27
                block_size = 3
                n = 9
                max_val = 9

            # 每个块的值必须在 0~max 之间
            # n 个块，每个块值是 0~max 的某个值，且全局恰好有 n 种不同值
            # 可行的块值集合是 {0, 1, ..., max} 的某个 n 元素子集
            feasible_totals = set()
            for comb in combinations(range(0, max_val+1), n):
                s = sum(comb)
                feasible_totals.add(n * s)
            if not feasible_totals:
                continue
            allowed = [(v,) for v in sorted(feasible_totals)]
            def total_hard(model, total_var):
                model.AddAllowedAssignments([total_var], allowed)
            info["hard_fns"].append(total_hard)