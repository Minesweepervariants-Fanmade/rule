#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[LD] 拉丁方 (Latin Square)

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 左线规则(Lrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 前置条件: 棋盘必须为正方形且边长为偶数(2n × 2n)。

2) 核心术语精确定义:
    - 2x2 块: 将边长为 2n 的正方形棋盘划分为 n×n 个互不重叠的 2x2 子区域。
    - 块值: 块内四个格子的雷数之和，取值范围 0~4。
    - 拉丁方: n×n 的块值矩阵中，每行、每列的值互不相同（即每行/列均为 0~4 中某 n 个不同值的排列）。
    - 值种类数: 整个矩阵中实际出现的不同值的个数，必须等于 n。

3) 计数对象、边界条件、越界处理:
    - 仅统计有效格，越界格不计入块内。
    - 棋盘必须恰好划分为整块，不处理部分块。

4) fill 阶段语义与 create_constraints 阶段语义等价关系:
    - 无 fill 阶段，仅在 create_constraints 中建模。
    - 约束语义: 每行/列块值互异，且全局不同值的总数等于 n。

5) 可验证样例:
    - 样例A(应通过): 4x4 棋盘(2x2块), n=2, 块值矩阵为 [[1,2],[2,1]] 满足行/列互异, 全局值{1,2}共2种, 符合。
    - 样例B(应失败): 4x4 棋盘, 块值矩阵为 [[1,2],[1,3]] 行互异但列有重复(第一列1,1), 且全局值有3种>n。
    - 样例C(应失败): 尺寸不为偶数时抛出 ValueError。
"""

from typing import List

from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard
from ....impl.summon.solver import Switch


class RuleLD(AbstractMinesRule):
    id = "LD"
    name = "Latin Square"
    name.zh_CN = "拉丁方"
    doc = ("Square board of size 2n: each 2x2 block forms a region; the mine count in each region forms a Latin square "
           "(rows/cols have distinct values), and exactly n distinct values appear globally.")
    doc.zh_CN = "正方形题版边长为2n：将每个2x2区域视为一个单元，该区域内的雷数作为单元的值；所有单元的值构成拉丁方（每行/列值互异），且全盘总共出现n种不同的值。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Construction", "Strict R"]
    creation_time = "2026-05-13"

    def __init__(self, board: AbstractBoard = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        # 验证棋盘尺寸是否为偶数正方形
        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            rows = bound.x + 1
            cols = bound.y + 1
            if rows != cols:
                raise ValueError(f"LD 规则要求正方形棋盘, 但当前尺寸为 {rows}×{cols}")
            if rows % 2 != 0:
                raise ValueError(f"LD 规则要求边长为偶数(2n), 但当前边长为 {rows}")
            if rows > 10:
                raise ValueError(f"LD 规则要求边长小于等于10的值, 但当前边长为 {rows}")

    def create_constraints(self, board: AbstractBoard, switch: Switch) -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key)
            size = bound.x + 1          # 边长, 必为偶数
            n = size // 2                # 2x2 块的行/列数

            # 为每个2x2块创建整型变量 (0~4)
            block_vals: List[List[IntVar]] = []
            for i in range(n):
                row_vals = []
                for j in range(n):
                    # 获取该2x2块内四个格子的变量
                    pos_tl = board.get_pos(2*i, 2*j, key)
                    pos_tr = board.get_pos(2*i, 2*j+1, key)
                    pos_bl = board.get_pos(2*i+1, 2*j, key)
                    pos_br = board.get_pos(2*i+1, 2*j+1, key)
                    # 收集四个格子的原始雷变量
                    vars_block = []
                    for p in (pos_tl, pos_tr, pos_bl, pos_br):
                        var = board.get_variable(p, special='raw')
                        if var is None:
                            continue
                        vars_block.append(var)
                    # 块值变量
                    bv = model.NewIntVar(0, 4, f"LD_block_{key}_{i}_{j}")
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

            # 全局值种类数 == n (仅当 n <= 4 时需要显式约束，因为值域足够大)
            if n <= 4:
                used = []
                for v in range(5):          # 0,1,2,3,4
                    # 是否存在某个块的值等于 v
                    any_eq = model.NewBoolVar(f"LD_used_{key}_{v}")
                    # 收集所有块等于 v 的指示变量
                    eq_flags = []
                    for i in range(n):
                        for j in range(n):
                            eq = model.NewBoolVar(f"LD_eq_{key}_{i}_{j}_{v}")
                            model.Add(block_vals[i][j] == v).OnlyEnforceIf(eq)
                            model.Add(block_vals[i][j] != v).OnlyEnforceIf(eq.Not())
                            eq_flags.append(eq)
                    # any_eq 等价于 OR(eq_flags)
                    model.AddBoolOr(eq_flags).OnlyEnforceIf(any_eq)
                    model.AddBoolAnd([e.Not() for e in eq_flags]).OnlyEnforceIf(any_eq.Not())
                    used.append(any_eq)
                model.Add(sum(used) == n).OnlyEnforceIf(s)

    def suggest_total(self, info: dict) -> None:
        """总雷数约束：对于 n<=4 添加硬约束确保拉丁方可行总雷数；对于 n=5 只添加软建议，避免过度限制；n>5 不可行。"""
        from itertools import combinations
        
        for key in info["interactive"]:
            size = info["size"][key]
            if size[0] != size[1] or size[0] % 2 != 0:
                continue
            n = size[0] // 2
            
            if n <= 4:
                # 生成所有可能的拉丁方总雷数
                feasible_values = set()
                for comb in combinations(range(5), n):
                    s = sum(comb)
                    feasible_values.add(n * s)
                if not feasible_values:
                    continue
                allowed = [(v,) for v in sorted(feasible_values)]
                def total_hard(model, total_var):
                    model.AddAllowedAssignments([total_var], allowed)
                info["hard_fns"].append(total_hard)
            elif n == 5:
                # n=5 时，拉丁方必定使用 0-4 全部值，总和为 10，总雷数 = 5 * 10 = 50
                # 为避免硬约束导致 10x10 生成困难，只使用高优先级软建议
                info["soft_fn"](50, 2)
                total_cells = size[0] * size[1]
                info["soft_fn"](int(total_cells * 0.5), 0)
            else:
                # n > 5 时无法从0~4中选出n个不同值，规则不可满足
                raise ValueError(f"LD 规则要求边长小于等于10的值, 但当前边长为 {rows}")
