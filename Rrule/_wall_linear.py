#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/28
# @FileName: _wall_linear.py
"""
[1W]/[1P]/[1W'] 数墙类规则的线性/布尔编码辅助（替代 256 布局表约束）。

对照 14mv1 官方源码（MinesweeperSolver.cs）与 mv-dsl 项目验证过的编码：

- 1P 段数    = 环形段起点计数 Σ(b[i] ∧ ¬b[i-1])
- 1W' 最长段 = 「无 (w+1) 连续雷」∧「存在 w 连续雷」（窗口布尔组合）
- 1W 数墙    = (雷数 V) ∧ (段数 P) ∧ (最长段 W') 三约束合取
  —— (V, 1P, 1W') 三元组与 1W 段长串一一对应
     （枚举 256 种 8 邻布局验证：23 种段长串 ↔ 23 种三元组，严格单射）

var_list 为 8 邻布尔变量列表，顺序与 fill 一致：
右、右下、下、左下、左、左上、上、右上（从「右」开始顺时针）；
其中 None 表示越界格（视为非雷）。
"""
from typing import List, Optional, Sequence, Union

# 8 邻环形顺序（索引 0..7，从「右」开始顺时针）
RING = list(range(8))


def decompose_wall(values: Sequence[int]) -> tuple[int, int, int]:
    """段长列表（升序）→ (雷数 V, 段数 P, 最长段 W')。

    空段 [0] 或空列表 → (0, 0, 0)。
    """
    vals = [v for v in values if v and v > 0]
    if not vals:
        return 0, 0, 0
    return sum(vals), len(vals), max(vals)


def _ring_window(start: int, length: int) -> List[int]:
    """环形窗口：从 start 起顺时针 length 个格子的索引。"""
    return [(start + k) % 8 for k in range(length)]


def add_segment_count(model, var_list: Sequence[Optional[object]], value: int, switch) -> None:
    """段数约束：环形段起点计数 == value（官方语义，全雷时 1 段）。

    每个段起点 b[i] ∧ ¬b[i-1]（i-1 取模 8，环形）；越界格（None）视为非雷。
    - value == 0：无雷（计数 0 且雷数 0）
    - value == 1：计数 1 或全雷（环形计数在全雷时为 0，官方记 1 段）
    - value >= 2：计数 == value（全雷不可能）
    """
    starts: List[object] = []
    for i in RING:
        cur = var_list[i]
        prev = var_list[(i - 1) % 8]
        if cur is None:
            continue
        if prev is None:
            starts.append(cur)  # 前驱越界 = 非雷 → b[i] 自身即起点
        else:
            t = model.NewBoolVar(f"wall_seg_start_{i}")
            model.Add(t == 1).OnlyEnforceIf([cur, prev.Not()])
            model.Add(t == 0).OnlyEnforceIf([cur.Not()])
            model.Add(t == 0).OnlyEnforceIf([prev])
            starts.append(t)
    cnt = sum(starts)
    if value == 0:
        model.Add(cnt == 0).OnlyEnforceIf(switch)
        model.Add(sum(x for x in var_list if x is not None) == 0).OnlyEnforceIf(switch)
    elif value == 1:
        b1 = model.NewBoolVar("wall_p_one")
        model.Add(cnt == 1).OnlyEnforceIf(b1)
        model.Add(cnt != 1).OnlyEnforceIf(b1.Not())
        b8 = model.NewBoolVar("wall_p_all8")
        model.Add(sum(x for x in var_list if x is not None) == 8).OnlyEnforceIf(b8)
        model.Add(sum(x for x in var_list if x is not None) != 8).OnlyEnforceIf(b8.Not())
        model.AddBoolOr([b1, b8]).OnlyEnforceIf(switch)
    else:
        model.Add(cnt == value).OnlyEnforceIf(switch)


def add_longest_window(model, var_list: Sequence[Optional[object]], value: int, switch) -> None:
    """最长段约束：最长连续雷 == value（窗口布尔组合）。

    - value == 0：无雷（sum == 0）
    - 否则：「无 (value+1) 连续雷」→ 每窗口 sum ≤ value（线性）
           ∧ 「存在 value 连续雷」→ 窗口全雷析取（reify + AddBoolOr）

    含越界格的窗口不可能全雷（越界断开），跳过——其「无连续」约束自动满足。
    """
    if value == 0:
        model.Add(sum(x for x in var_list if x is not None) == 0).OnlyEnforceIf(switch)
        return

    # 无 (value+1) 连续雷（窗口长度 ≤ 8 才有意义；value==8 时 9 连不可能，跳过）
    if value + 1 <= 8:
        for start in RING:
            win = _ring_window(start, value + 1)
            if any(var_list[i] is None for i in win):
                continue
            model.Add(sum(var_list[i] for i in win) <= value).OnlyEnforceIf(switch)

    # 存在 value 连续雷
    full_wins: List[object] = []
    for start in RING:
        win = _ring_window(start, value)
        if any(var_list[i] is None for i in win):
            continue
        b = model.NewBoolVar(f"wall_longest_win_{start}")
        model.Add(sum(var_list[i] for i in win) == value).OnlyEnforceIf(b)
        model.Add(sum(var_list[i] for i in win) < value).OnlyEnforceIf(b.Not())
        full_wins.append(b)
    if full_wins:
        model.AddBoolOr(full_wins).OnlyEnforceIf(switch)
