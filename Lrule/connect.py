#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 16:43
# @Author  : Wu_RH
# @FileName: connect.py
from typing import List, Callable, Union

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.board import Board, Position

def connect(
        model: cp_model.CpModel,
        board: Board,
        switch: IntVar,
        component_num: Union[int, IntVar, None] = 1,   # 允许的连通块数量，填 None 表示不限制
        ub=False, # 最长连通上限
        connect_value=1, # 1 雷连通 0 非雷连通
        nei_value: Union[int, tuple[int, int], Callable[[Position], List[Position]]] = 2, # 连通方向定义，1 四连通 2 八连通
        root_vars: List[IntVar] | None = None,
        positions_vars: List[tuple[Position, IntVar]] | None = None,
        special='',
) -> List[IntVar]: # 返回表示各位置所属连通块 ID 的列表
    # 获取题板上所有位置及其对应的布尔变量
    if positions_vars is None:
        positions_vars = [(pos, var) for pos, var in board("always", mode="variable", special=special)]
    if not positions_vars:
        return []

    pos_list, var_list = zip(*positions_vars)
    n = len(pos_list)

    # active_vars 表示该格是否属于待连通的集合（雷/非雷）
    active_vars: List[IntVar] = [model.NewBoolVar(f'active_{i}') for i in range(n)]
    for i in range(n):
        if connect_value == 1:
            model.Add(active_vars[i] == var_list[i]).OnlyEnforceIf(switch)
        else:
            model.Add(active_vars[i] + var_list[i] == 1).OnlyEnforceIf(switch)  # active = not mine

    # 构造邻接列表
    adj = [[] for _ in range(n)]
    for i, pos_i in enumerate(pos_list):
        for j, pos_j in enumerate(pos_list):
            if i != j and (board is None or board.in_bounds(pos_j)):
                if callable(nei_value):
                    is_neighbor = pos_j in nei_value(pos_i)
                elif type(nei_value) is int:
                    is_neighbor = pos_j in pos_i.neighbors(nei_value)
                elif type(nei_value) is tuple:
                    is_neighbor = pos_j in pos_i.neighbors(nei_value[0], nei_value[1])
                else:
                    raise ValueError("nei_value 无效")
                if is_neighbor:
                    adj[i].append(j)

    # ============ 轻量连通编码（对比实验结论：完整 parent 指针编码在 CP-SAT 上
    # 比官方 csugar 的 Tarjan 传播器慢 1-2 个数量级，本实现去掉 parent 指针层）====
    #
    # - component_ids：分量编号，**根格 id == 自身索引**（调用方契约，如 2G^ 依赖）
    # - level_vars：BFS 层，非 active 为 0，根为 0；非根 active 存在邻居 layer-1
    #   （层递减链保证连通到根，配合根计数即得每分量恰一根）
    # - root_vars：是否为根；root ⟺ (active ∧ level==0)
    #
    component_ids: List[IntVar] = [model.NewIntVar(0, n - 1, f'component_{i}') for i in range(n)]
    level_vars: List[IntVar] = [model.NewIntVar(0, (ub if ub else n + 1), f'level_{i}') for i in range(n)]

    if root_vars is None:
        root_vars = [model.NewBoolVar(f'root_{i}') for i in range(n)]

    for i in range(n):
        active = active_vars[i]
        root = root_vars[i]

        # 非 active：层 0、非根
        model.Add(level_vars[i] == 0).OnlyEnforceIf([active.Not(), switch])
        model.Add(root == 0).OnlyEnforceIf([active.Not(), switch])
        # 根 ⇒ active（逆否已由「非 active → 非根」覆盖，显式写出更稳）
        model.Add(active == 1).OnlyEnforceIf([root, switch])
        # root ⟺ (active ∧ level==0)
        model.Add(level_vars[i] == 0).OnlyEnforceIf([root, switch])
        model.Add(level_vars[i] != 0).OnlyEnforceIf([root.Not(), active, switch])

        # 根 → 分量 id == 自身索引
        model.Add(component_ids[i] == i).OnlyEnforceIf([root, switch])
        # active → id <= 自身索引（根 id==i 即等号情形）
        model.Add(component_ids[i] <= i).OnlyEnforceIf([active, switch])
        # 非根 active → id != 自身索引（保证分量编号取根索引）
        model.Add(component_ids[i] != i).OnlyEnforceIf([active, root.Not(), switch])

        # 非根 active → 存在 active 邻居 level == level-1（层递减链）
        # 注意：b 是「该边被选为父」的指示变量，只做单向蕴含（b → 层关系 ∧ 父 active），
        # 不做 ¬b → 非层关系——否则 lv 传播确定后，层恰好匹配的非 active 邻居
        # 会被强制为父（b 被迫为真 → active[j] 被迫为真）导致误 UNSAT。
        lower = []
        for j in adj[i]:
            b = model.NewBoolVar(f'level_{j}_to_{i}')
            model.Add(level_vars[i] == level_vars[j] + 1).OnlyEnforceIf([b, switch])
            model.Add(active_vars[j] == 1).OnlyEnforceIf([b, switch])
            lower.append(b)
        if lower:
            model.AddBoolOr(lower).OnlyEnforceIf([active, root.Not(), switch])

    # 相邻的激活格必须属于同一连通块（不同分量被雷/空隔开）
    seen_pairs = set()
    for i in range(n):
        for j in adj[i]:
            if i < j and (i, j) not in seen_pairs:
                model.Add(component_ids[i] == component_ids[j]).OnlyEnforceIf([active_vars[i], active_vars[j], switch])
                seen_pairs.add((i, j))

    # 根数量 = component_num
    if component_num is not None:
        model.Add(sum(root_vars) == component_num).OnlyEnforceIf(switch)

    return component_ids

def connect_legacy(
        model: cp_model.CpModel,
        board: Board,
        switch: IntVar,     # 连通性选择
        ub=False,  # 可达处的上限
        connect_value=1,  # 1=雷连通，0=非雷连通
        nei_value: Union[int, tuple, Callable] = 2,  # 1=四连通，2=八连通
        root_vars: List[IntVar] = None,  # 允许提供根节点变量
        positions_vars: List[tuple[Position, IntVar]] = None,
        special='',
):
    # 获取题板上所有位置及其对应的布尔变量
    if positions_vars is None:
        positions_vars = [(pos, var) for pos, var in board("always", mode="variable", special=special)]
    if not positions_vars:
        return

    pos_list, var_list = zip(*positions_vars)
    n = len(pos_list)

    # 定义reach_vars整数变量
    reach_vars = [model.NewIntVar(0, (ub if ub else n + 1), f'reach_{i}') for i in range(n)]

    # 定义root_vars布尔变量
    if root_vars is None:
        root_vars = [model.NewBoolVar(f'root_{i}') for i in range(n)]
        model.Add(sum(root_vars) == 1).OnlyEnforceIf(switch)

    for i in range(n):
        # 根据connect_value决定连通对象
        if connect_value == 1:  # 雷连通
            model.AddImplication(root_vars[i], var_list[i]).OnlyEnforceIf(switch)
            model.Add(reach_vars[i] == 1).OnlyEnforceIf([root_vars[i], switch])
            model.Add(reach_vars[i] != 1).OnlyEnforceIf([root_vars[i].Not(), switch])
            model.Add(reach_vars[i] == 0).OnlyEnforceIf([var_list[i].Not(), switch])
        else:  # 非雷连通
            model.AddImplication(root_vars[i], var_list[i].Not()).OnlyEnforceIf(switch)
            model.Add(reach_vars[i] == 1).OnlyEnforceIf([root_vars[i], switch])
            model.Add(reach_vars[i] != 1).OnlyEnforceIf([root_vars[i].Not(), switch])
            model.Add(reach_vars[i] == 0).OnlyEnforceIf([var_list[i], switch])

    # 构造邻接列表（根据nei_value决定连通方式）
    adj = [[] for _ in range(n)]
    for i, pos_i in enumerate(pos_list):
        for j, pos_j in enumerate(pos_list):
            if i != j and board.in_bounds(pos_j):
                # 根据nei_value判断连通方式
                if callable(nei_value):
                    is_neighbor = pos_j in nei_value(pos_i)
                elif type(nei_value) is int:  # 四连通
                    is_neighbor = pos_j in pos_i.neighbors(nei_value)
                elif type(nei_value) is tuple:  # 四连通
                    is_neighbor = pos_j in pos_i.neighbors(nei_value[0], nei_value[1])
                else:  # 八连通
                    raise ValueError("")
                if is_neighbor:
                    adj[i].append(j)

    # 传播约束
    for i in range(n):
        # 条件判断根据connect_value变化
        if connect_value == 1:  # 雷连通
            cond = [var_list[i], root_vars[i].Not()]
        else:  # 非雷连通
            cond = [var_list[i].Not(), root_vars[i].Not()]

        possible_sources = []
        for j in adj[i]:
            tmp = model.NewBoolVar(f'path_{j}_to_{i}')
            model.Add(reach_vars[i] == reach_vars[j] + 1).OnlyEnforceIf([tmp, switch])

            # 根据connect_value决定传播条件
            if connect_value == 1:
                model.AddImplication(tmp, var_list[j]).OnlyEnforceIf(switch)
            else:
                model.AddImplication(tmp, var_list[j].Not()).OnlyEnforceIf(switch)

            is_reach_j_pos = model.NewBoolVar(f'is_reach_pos_{j}')
            model.Add(reach_vars[j] > 0).OnlyEnforceIf([is_reach_j_pos, switch])
            model.Add(reach_vars[j] == 0).OnlyEnforceIf([is_reach_j_pos.Not(), switch])
            model.AddImplication(tmp, is_reach_j_pos).OnlyEnforceIf(switch)

            possible_sources.append(tmp)

        if possible_sources:
            model.AddBoolOr(possible_sources).OnlyEnforceIf(cond + [switch])

    # 最终约束
    for i in range(n):
        if connect_value == 1:  # 雷连通
            model.Add(reach_vars[i] > 0).OnlyEnforceIf([var_list[i], switch])
            model.Add(reach_vars[i] == 0).OnlyEnforceIf([var_list[i].Not(), switch])
        else:  # 非雷连通
            model.Add(reach_vars[i] > 0).OnlyEnforceIf([var_list[i].Not(), switch])
            model.Add(reach_vars[i] == 0).OnlyEnforceIf([var_list[i], switch])
