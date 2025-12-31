#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 16:43
# @Author  : Wu_RH
# @FileName: connect.py
from typing import List, Callable, Union

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import IntVar

from ....abs.board import AbstractBoard, AbstractPosition

def connect(
        model: cp_model.CpModel,
        board: AbstractBoard,
        switch: IntVar,     
        component_num: Union[int, IntVar] = 1,   # 允许的连通块数量
        ub=False, # 最长连通上限
        connect_value=1, # 1 雷连通 0 非雷连通
        nei_value: Union[int, tuple[int, int], Callable[[AbstractPosition], List[AbstractPosition]]] = 2, # 连通方向定义，1 四连通 2 八连通
        root_vars: List[IntVar] | None = None,
        positions_vars: List[tuple[AbstractPosition, IntVar]] | None = None,
        special='',
):
    # 获取题板上所有位置及其对应的布尔变量
    if positions_vars is None:
        positions_vars = [(pos, var) for pos, var in board("always", mode="variable", special=special)]
    if not positions_vars:
        return

    pos_list, var_list = zip(*positions_vars)
    n = len(pos_list)

    # active_vars 表示该格是否属于待连通的集合（雷/非雷）
    active_vars: List[IntVar] = [model.NewBoolVar(f'active_{i}') for i in range(n)]
    for i in range(n):
        if connect_value == 1:
            model.Add(active_vars[i] == var_list[i]).OnlyEnforceIf(switch)
        else:
            model.Add(active_vars[i] + var_list[i] == 1).OnlyEnforceIf(switch)  # active = not mine

    # component_ids 标识节点归属的连通块，根节点会绑定自身索引
    component_ids = [model.NewIntVar(0, n - 1, f'component_{i}') for i in range(n)]

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

    # 父指针与根标记：每个 active 节点选择恰好一个父（可指向自身表示根）
    parent_neighbor_bools: List[List[tuple[int, IntVar]]] = []
    self_parent_bools: List[IntVar] = []
    for i in range(n):
        choices = []
        neighbor_choices: List[tuple[int, IntVar]] = []
        # 邻居作为父
        for j in adj[i]:
            b = model.NewBoolVar(f'parent_{j}_to_{i}')
            choices.append(b)
            neighbor_choices.append((j, b))
            # 父必须是 active
            model.AddImplication(b, active_vars[j]).OnlyEnforceIf(switch)
        # 自身作为父（根）
        self_b = model.NewBoolVar(f'self_parent_{i}')
        choices.append(self_b)
        self_parent_bools.append(self_b)

        parent_neighbor_bools.append(neighbor_choices)

        # active -> 选 exactly 1 父；非 active -> 不选父
        model.Add(sum(choices) == 1).OnlyEnforceIf([active_vars[i], switch])
        model.Add(sum(choices) == 0).OnlyEnforceIf([active_vars[i].Not(), switch])

    # root_vars 处理
    if root_vars is None:
        root_vars = [model.NewBoolVar(f'root_{i}') for i in range(n)]
    elif len(root_vars) != n:
        raise ValueError("root_vars 的长度必须与 positions_vars 相同")

    for i in range(n):
        model.Add(root_vars[i] == self_parent_bools[i]).OnlyEnforceIf(switch)
        model.Add(component_ids[i] == i).OnlyEnforceIf([self_parent_bools[i], switch])

    # 根数量 = component_num
    if isinstance(component_num, int):
        if component_num < 0 or component_num > n:
            raise ValueError("component_num 超出可行范围")
        model.Add(sum(root_vars) == component_num).OnlyEnforceIf(switch)
    else:
        model.Add(sum(root_vars) == component_num).OnlyEnforceIf(switch)

    # 层级变量（用于防环并保证根可达）：非 active 为 0；根为 1；子 = 父 + 1
    level_vars = [model.NewIntVar(0, (ub if ub else n + 1), f'level_{i}') for i in range(n)]
    for i in range(n):
        model.Add(level_vars[i] == 0).OnlyEnforceIf([active_vars[i].Not(), switch])
        model.Add(level_vars[i] == 1).OnlyEnforceIf([root_vars[i], switch])
        model.Add(level_vars[i] >= 2).OnlyEnforceIf([active_vars[i], root_vars[i].Not(), switch])

        # 邻居父指针：level_i = level_parent + 1；组件标签同步
        for j, b in parent_neighbor_bools[i]:
            model.Add(level_vars[i] == level_vars[j] + 1).OnlyEnforceIf([b, switch])
            model.Add(component_ids[i] == component_ids[j]).OnlyEnforceIf([b, switch])
        # 自身父（根）已经约束 level == 1

    # 连通性一致性：active -> level > 0；非 active -> level == 0
    for i in range(n):
        model.Add(level_vars[i] > 0).OnlyEnforceIf([active_vars[i], switch])
        model.Add(level_vars[i] == 0).OnlyEnforceIf([active_vars[i].Not(), switch])

    # 邻接的激活格必须属于同一连通块，避免环边被拆分到不同根
    seen_pairs = set()
    for i in range(n):
        for j in adj[i]:
            if i < j and (i, j) not in seen_pairs:
                model.Add(component_ids[i] == component_ids[j]).OnlyEnforceIf([active_vars[i], active_vars[j], switch])
                seen_pairs.add((i, j))
