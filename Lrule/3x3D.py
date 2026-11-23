#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[3*3D] 3x3 Distinct: 雷盘中任意两块不相交的 3x3 区域内雷的分布都不完全相同,
旋转与镜像视为同一种分布。

语义:
    对题板上任意两个互不重叠(不共享格子)的、完全位于题板内的 3x3 区域 A、B,
    A 内的 0/1 雷分布与 B 内的 0/1 雷分布不能相等, 即使把其中一个分布
    旋转 90/180/270 度或做水平/垂直/主副对角线镜像后也不允许相等。

实现:
    - 只考虑完全有效(在题板内且未被掩码)的 3x3 区域;
    - 把一个 3x3 区域编码成 9 位整数, 第 row*3+col 位表示该格是否为雷;
    - 对每个区域计算 8 种 D4 变换后的模式, 取最小值作为该分布的规范代表;
      两个分布旋转/镜像等价当且仅当它们的规范代表相同;
    - 对每对不相交的区域 A、B, 添加 canonical(A) != canonical(B);
    - 所有约束都由 switch.get(model, self) 返回的开关变量控制。

作者: 时天使阿蒙 (2648450484)
最后编辑时间: 2026-11-20 23:57:14
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING, List, Tuple

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


# 3x3 区域内的格子按 (row, col) 编号为 row * 3 + col。
# 对每个 D4 变换 T, 变换后目标格 j 的值取自源区域中 T(j) 处的值。
_TRANSFORMS = (
    lambda r, c: (r, c),                  # 恒等
    lambda r, c: (c, 2 - r),              # 顺时针旋转 90 度
    lambda r, c: (2 - r, 2 - c),          # 旋转 180 度
    lambda r, c: (2 - c, r),              # 顺时针旋转 270 度
    lambda r, c: (r, 2 - c),              # 左右镜像
    lambda r, c: (2 - r, c),              # 上下镜像
    lambda r, c: (c, r),                  # 主对角线镜像
    lambda r, c: (2 - c, 2 - r),          # 副对角线镜像
)

# 每个变换对应一个长度 9 的置换: perm[j] 是变换后第 j 格在源区域中的下标。
_D4_PERMS: Tuple[Tuple[int, ...], ...] = tuple(
    tuple(tf(r, c)[0] * 3 + tf(r, c)[1] for r in range(3) for c in range(3))
    for tf in _TRANSFORMS
)


class Rule3x3D(AbstractMinesRule):
    id = "3*3D"
    name = "3x3 Distinct"
    name.zh_CN = "3x3 互异"
    doc = ("Any two non-overlapping 3x3 regions must not contain the same mine pattern, "
           "even after rotation or reflection.")
    doc.zh_CN = "雷盘中任意两块不相交的3乘3区域内雷的分布都不完全相同，不考虑该区域的旋转与对称。"
    author = ("时天使阿蒙 (2648450484)", 2648450484)
    tags = ["Original", "Global", "Mine-Position", "Strong"]
    creation_time = "2026-11-20 23:57:14"

    @staticmethod
    def _collect_regions(board: Board, key: str) -> List[Tuple[int, int, List[Position]]]:
        """收集某块题板上所有完全有效(9 格均有效)的 3x3 区域。

        返回 (左上角行, 左上角列, 9 个位置) 的列表, 位置按 row*3+col 排列。
        """
        boundary = board.boundary(key)
        rows = boundary.row + 1
        cols = boundary.col + 1
        if rows < 3 or cols < 3:
            return []

        regions: List[Tuple[int, int, List[Position]]] = []
        for row in range(rows - 2):
            for col in range(cols - 2):
                positions = [
                    Position(col + dc, row + dr, key)
                    for dr in range(3)
                    for dc in range(3)
                ]
                if all(board.is_valid(pos) for pos in positions):
                    regions.append((row, col, positions))
        return regions

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            regions = self._collect_regions(board, key)
            if len(regions) < 2:
                continue

            # (左上角行, 左上角列, 9 位模式的 D4 规范代表变量)
            canonicals: List[Tuple[int, int, object]] = []
            for row, col, positions in regions:
                cell_vars = [board.get_variable(pos, special='raw') for pos in positions]
                if any(var is None for var in cell_vars):
                    # 理论上 _collect_regions 已过滤, 这里仅作防御。
                    continue

                # 9 个 D4 变换后的 9 位模式, 用最小值作为规范代表。
                transformed = [
                    sum(
                        cell_vars[perm[bit]] * (1 << bit) for bit in range(9)
                    )
                    for perm in _D4_PERMS
                ]
                canonical = model.new_int_var(
                    0, 511, f"rule3x3d_canonical_{key}_{row}_{col}"
                )
                model.add_min_equality(
                    canonical, transformed
                ).only_enforce_if(rule_switch)
                canonicals.append((row, col, canonical))

            for (
                row_a, col_a, canonical_a
            ), (
                row_b, col_b, canonical_b
            ) in combinations(canonicals, 2):
                # 两个 3x3 区域不相交 <=> 行区间不相交或列区间不相交。
                if abs(row_a - row_b) < 3 and abs(col_a - col_b) < 3:
                    continue

                # 两个分布旋转/镜像等价 <=> 规范代表相等。
                model.add(canonical_a != canonical_b).only_enforce_if(rule_switch)
