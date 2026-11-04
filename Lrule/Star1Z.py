#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-05-12
# @Author  : 波常未来 (81500378)
# @FileName: Star1Z.py
"""
[*1Z] 无环非雷: 任意四连通的非雷格不能与其他非雷格组成环。

等价语义: 所有非雷格在四连通意义下构成的图是一个森林 (无环图)，
允许存在多个互不连通的树、允许孤立点，但任何连通分量都不能含环。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple

from minesweepervariants.abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from minesweepervariants.board import Board
    from minesweepervariants.impl.summon.solver import Switch


class RuleStar1Z(AbstractMinesRule):
    """
    [*1Z] 无环非雷：非雷格四连通图无环（森林）。
    """

    id = "*1Z"
    name = "Non-mine Acyclic"
    name.zh_CN = "无环非雷"
    doc = "Any 4-connected non-mine cells cannot form a loop with other non-mine cells."
    doc.zh_CN = "任意四连通的非雷格不能与其他非雷格组成环。"
    author = ("波常未来", 81500378)
    tags = ["Variant", "Connectivity", "Global"]
    creation_time = "2026-05-12"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions: List[Tuple[object, object]] = [
                (pos, var)
                for pos, var in board(key=key, mode="variable", special="raw")
                if var is not None
            ]
            if not positions:
                continue
            n = len(positions)
            pos_to_index: Dict[object, int] = {pos: i for i, (pos, _) in enumerate(positions)}

            # 非雷格标识：safe = 1 - raw
            safe: List[object] = []
            for i, (pos, raw) in enumerate(positions):
                safe_var = model.new_bool_var(
                    f"{self.id}_safe_{key}_{pos.col}_{pos.row}"
                )
                model.add(safe_var + raw == 1).only_enforce_if(s)
                safe.append(safe_var)

            # level: 0 表示非非雷（雷或无效），1..n 表示该非雷格在森林中的层级
            # 根为 1，子节点层级 = 父层级 + 1
            level: List[object] = [
                model.new_int_var(
                    0, n, f"{self.id}_level_{key}_{pos.col}_{pos.row}"
                )
                for pos, _ in positions
            ]
            for i in range(n):
                # 非 safe 时 level = 0
                model.add(level[i] == 0).only_enforce_if([safe[i].Not(), s])
                # safe 时 level >= 1
                model.add(level[i] >= 1).only_enforce_if([safe[i], s])

            # root: 是否为所在树的根（level == 1 且 safe）
            root: List[object] = [
                model.new_bool_var(
                    f"{self.id}_root_{key}_{pos.col}_{pos.row}"
                )
                for pos, _ in positions
            ]
            for i in range(n):
                model.add_implication(root[i], safe[i]).only_enforce_if(s)
                model.add(level[i] == 1).only_enforce_if([root[i], s])
                model.add(level[i] >= 2).only_enforce_if(
                    [safe[i], root[i].Not(), s]
                )

            # 四邻索引表
            neighbors_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            neighbor_index: Dict[int, List[int]] = {}
            for i, (pos, _) in enumerate(positions):
                lst: List[int] = []
                for dr, dc in neighbors_offsets:
                    npos = board.get_pos(pos.row + dr, pos.col + dc, key)
                    if npos is None:
                        continue
                    j = pos_to_index.get(npos)
                    if j is not None:
                        lst.append(j)
                neighbor_index[i] = lst

            # parent[(i, j)] 表示 i 的父节点是 j（i 为非根非雷格，j 为其四邻非雷格）
            parent: Dict[Tuple[int, int], object] = {}
            for i in range(n):
                for j in neighbor_index[i]:
                    if (i, j) in parent:
                        continue
                    p = model.new_bool_var(
                        f"{self.id}_parent_{key}_{i}_{j}"
                    )
                    parent[(i, j)] = p
                    # parent => 父节点也是非雷格
                    model.add_implication(p, safe[j]).only_enforce_if(s)
                    # parent => level_i = level_j + 1
                    model.add(level[i] == level[j] + 1).only_enforce_if([p, s])

            # 每个非雷格：要么是根，要么恰有一个父节点
            for i in range(n):
                terms: List[object] = [root[i]]
                for j in neighbor_index[i]:
                    terms.append(parent[(i, j)])
                model.add(sum(terms) == 1).only_enforce_if([safe[i], s])
                model.add(sum(terms) == 0).only_enforce_if([safe[i].Not(), s])

            # 无向边约束：对每条四连通边 (i, j)（i < j），
            # 若两端都是非雷格，则两端层级必须差 1（高者以低者为父），
            # 这排除了任何额外的非树边，从而保证每个分量无环。
            seen_pairs = set()
            for i in range(n):
                for j in neighbor_index[i]:
                    if i >= j:
                        continue
                    if (i, j) in seen_pairs:
                        continue
                    seen_pairs.add((i, j))

                    # eq_ij: safe_i & safe_j & (level_i == level_j + 1)
                    eq_ij = model.new_bool_var(
                        f"{self.id}_eq_{key}_{i}_{j}"
                    )
                    # eq_ji: safe_i & safe_j & (level_j == level_i + 1)
                    eq_ji = model.new_bool_var(
                        f"{self.id}_eq_{key}_{j}_{i}"
                    )

                    model.add(level[i] == level[j] + 1).only_enforce_if([eq_ij, s])
                    model.add(level[j] == level[i] + 1).only_enforce_if([eq_ji, s])

                    # eq 变量只在两端 safe 时才可能为真
                    model.add_implication(eq_ij, safe[i]).only_enforce_if(s)
                    model.add_implication(eq_ij, safe[j]).only_enforce_if(s)
                    model.add_implication(eq_ji, safe[i]).only_enforce_if(s)
                    model.add_implication(eq_ji, safe[j]).only_enforce_if(s)

                    # 两端都是非雷格 => 必须恰好一个方向层级差 1
                    model.add_bool_or([eq_ij, eq_ji]).only_enforce_if(
                        [safe[i], safe[j], s]
                    )

                    # 高层级节点必须以低层级邻居为父
                    if (i, j) in parent:
                        model.add_implication(eq_ij, parent[(i, j)]).only_enforce_if(s)
                    if (j, i) in parent:
                        model.add_implication(eq_ji, parent[(j, i)]).only_enforce_if(s)

    def suggest_total(self, info: dict) -> None:
        """
        无环非雷要求非雷格图是森林，不能太密导致必然成环。
        给出约 50% 雷数的软建议，辅助生成。
        """
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]
        if total_cells > 0:
            info["soft_fn"](int(total_cells * 0.5), 0)
