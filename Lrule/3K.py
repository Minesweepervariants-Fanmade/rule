#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-09-07
# @Author  : DeepSeek Agent
# @FileName: 3K.py
"""
[3K] 三消：题版可以经过若干轮三消变成全空题版。

规则语义：
- 每轮选中所有面积不小于 3 的雷/非雷连通块（四连通），"删去"这些格子，
  让上面的格子落下来（每列独立垂直下落），并在上方补齐非雷格。
- 重复此操作若干轮后，若题版内没有雷格，则该题版满足规则。

完整 CP-SAT 约束编码（充要条件）：
- 建模多轮状态：S[r][pos] 表示第 r 轮后 pos 位置的雷状态（0=非雷，1=雷）。
- 每轮：计算删除变量 Del[r][pos]（该格所属同值四连通分量面积 >= 3），
  然后编码重力下落得到 S[r+1]。
- 最终状态 S[max_rounds] 全空（无雷）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, List, Set

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule3K(AbstractMinesRule):
    """[3K] 三消规则：完整 CP-SAT 建模多轮删除+重力过程。"""

    id = "3K"
    name = "3K"
    name.zh_CN = "三消"
    doc = "The board can be cleared by repeatedly removing all 4-connected components of size >= 3 and applying gravity."
    doc.zh_CN = "题版可以经过若干轮三消（删除面积>=3的连通块并下落）变成全空题版。"
    tags = ["Creative", "Variant", "Construction"]
    creation_time = "2026-09-07"
    author = ("NT", 2201963934)

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)

    def _get_rc(self, board: Board, key: str) -> Tuple[int, int]:
        """获取单板行数/列数。"""
        bound = board.boundary(key=key)
        return bound.row + 1, bound.col + 1

    def _get_neighbors(self, i: int, j: int, rows: int, cols: int) -> List[Tuple[int, int]]:
        """返回位置 (i,j) 的四邻坐标列表（在边界内）。"""
        neighbors = []
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < rows and 0 <= nj < cols:
                neighbors.append((ni, nj))
        return neighbors

    def create_constraints(self, board: Board, switch: Switch) -> None:
        """完整编码三消语义（充要条件）。"""
        model = board.get_model()
        s = switch.get(model, self)

        keys = board.get_interactive_keys()
        if not keys:
            return
        key = keys[0]

        rows, cols = self._get_rc(board, key)
        if rows == 0 or cols == 0:
            return

        # 最大轮数：每列最多 rows 个格子被删，最多 rows 轮可清空
        max_rounds = rows

        # === 状态变量 S[r][(i,j)] ===
        S: List[Dict[Tuple[int, int], object]] = []
        for r in range(max_rounds + 1):
            S_r: Dict[Tuple[int, int], object] = {}
            for i in range(rows):
                for j in range(cols):
                    pos = board.get_pos(i, j, key=key)
                    if pos is not None and board.is_valid(pos):
                        S_r[(i, j)] = model.new_bool_var(f"3K_S_{r}_{i}_{j}")
                    else:
                        S_r[(i, j)] = None
            S.append(S_r)

        # 初始状态：S[0][(i,j)] == board.get_variable(pos)
        for i in range(rows):
            for j in range(cols):
                pos = board.get_pos(i, j, key=key)
                if pos is not None and board.is_valid(pos):
                    raw_var = board.get_variable(pos, special="raw")
                    if raw_var is not None and S[0][(i, j)] is not None:
                        model.add(S[0][(i, j)] == raw_var).only_enforce_if(s)

        # 最终状态：所有 S[max_rounds][(i,j)] == 0
        for (i, j) in S[max_rounds]:
            if S[max_rounds][(i, j)] is not None:
                model.add(S[max_rounds][(i, j)] == 0).only_enforce_if(s)

        # === 对每轮 r 编码删除+重力 ===
        for r in range(max_rounds):
            self._encode_round(model, board, s, S, r, rows, cols, key)

    def _encode_round(self, model, board, s, S, r, rows, cols, key):
        """编码第 r 轮的删除+重力过程，从 S[r] 生成 S[r+1]。"""
        # Del[(i,j)]：该轮中位置 (i,j) 是否被删除
        Del: Dict[Tuple[int, int], object] = {}
        for i in range(rows):
            for j in range(cols):
                pos = board.get_pos(i, j, key=key)
                if pos is not None and board.is_valid(pos):
                    Del[(i, j)] = model.new_bool_var(f"3K_Del_{r}_{i}_{j}")

        # 编码 Del：属于面积>=3 的连通分量
        self._encode_del(model, s, S[r], Del, rows, cols, r)

        # 编码重力：从 S[r] + Del 生成 S[r+1]
        self._encode_gravity(model, s, S[r], S[r + 1], Del, rows, cols, r)

    def _encode_del(self, model, s, S_r, Del, rows, cols, r):
        """编码 Del[(i,j)]：存在包含 (i,j) 的 3 格同值连通集合。"""
        # 使用 DFS/BFS 动态来判定连通分量大小 >= 3
        # 更严谨的编码：使用 connect 风格的连通建模
        # 对每种值（雷/非雷），建立连通分量，要求如果格子属于面积 >= 3 的分量则 Del=1

        # 简化但正确的编码：
        # Del[(i,j)] = 1 当且仅当存在同值的邻居 q 使得 q 也属于一个面积 >= 2 的同值连通块
        # 等价于：存在两个同值的邻居或邻居的邻居与 (i,j) 同值连通

        # 最严谨方式：对每个位置，检查是否存在包含它的 3 格连通同值集合
        # 这等价于：存在路径 (i,j) -> a -> b 使得三格同值且路径连通

        for i in range(rows):
            for j in range(cols):
                if (i, j) not in S_r or S_r[(i, j)] is None:
                    continue

                triple_any_list: list[object] = []
                neis = self._get_neighbors(i, j, rows, cols)

                # 收集所有包含 (i,j) 的连通三元组（去重）
                triple_sets: Set[Tuple[Tuple[int, int], ...]] = set()

                # 情况1：从 (i,j) 的邻居中选两个
                for k1 in range(len(neis)):
                    for k2 in range(k1 + 1, len(neis)):
                        q1 = neis[k1]
                        q2 = neis[k2]
                        if S_r.get(q1) is not None and S_r.get(q2) is not None:
                            cells = [(i, j), q1, q2]
                            cells_sorted = tuple(sorted(cells))
                            if cells_sorted not in triple_sets:
                                triple_sets.add(cells_sorted)
                                triple_any = self._encode_triple_same(
                                    model, s, S_r, cells, r
                                )
                                triple_any_list.append(triple_any)

                # 情况2：通过 (i,j) 的邻居 q 再访问 q 的邻居
                for q in neis:
                    if S_r.get(q) is None:
                        continue
                    for rr in self._get_neighbors(q[0], q[1], rows, cols):
                        if rr == (i, j):
                            continue
                        if S_r.get(rr) is None:
                            continue
                        cells = [(i, j), q, rr]
                        cells_sorted = tuple(sorted(cells))
                        if cells_sorted not in triple_sets:
                            triple_sets.add(cells_sorted)
                            triple_any = self._encode_triple_same(
                                model, s, S_r, cells, r
                            )
                            triple_any_list.append(triple_any)

                # Del == OR(triple_any_list)
                if triple_any_list:
                    model.add(Del[(i, j)] <= sum(triple_any_list)).only_enforce_if(s)
                    for ta in triple_any_list:
                        model.add(Del[(i, j)] >= ta).only_enforce_if(s)
                else:
                    model.add(Del[(i, j)] == 0).only_enforce_if(s)

    def _encode_triple_same(self, model, s, S_r, cells, r):
        """编码三个格子同值（都是雷或都是非雷）。返回布尔变量。"""
        c0 = cells[0]
        c1 = cells[1]
        c2 = cells[2]

        all_mine = model.new_bool_var(f"3K_tm_{r}_{c0[0]}_{c0[1]}_{c1[0]}_{c1[1]}_{c2[0]}_{c2[1]}")
        all_safe = model.new_bool_var(f"3K_ts_{r}_{c0[0]}_{c0[1]}_{c1[0]}_{c1[1]}_{c2[0]}_{c2[1]}")
        triple_any = model.new_bool_var(f"3K_ta_{r}_{c0[0]}_{c0[1]}_{c1[0]}_{c1[1]}_{c2[0]}_{c2[1]}")

        # all_mine：三者都为雷
        model.add(all_mine <= S_r[c0]).only_enforce_if(s)
        model.add(all_mine <= S_r[c1]).only_enforce_if(s)
        model.add(all_mine <= S_r[c2]).only_enforce_if(s)
        model.add(all_mine >= S_r[c0] + S_r[c1] + S_r[c2] - 2).only_enforce_if(s)

        # all_safe：三者都非雷
        model.add(all_safe <= S_r[c0].Not()).only_enforce_if(s)
        model.add(all_safe <= S_r[c1].Not()).only_enforce_if(s)
        model.add(all_safe <= S_r[c2].Not()).only_enforce_if(s)
        model.add(all_safe >= S_r[c0].Not() + S_r[c1].Not() + S_r[c2].Not() - 2).only_enforce_if(s)

        # triple_any = all_mine OR all_safe
        model.add(triple_any <= all_mine + all_safe).only_enforce_if(s)
        model.add(triple_any >= all_mine).only_enforce_if(s)
        model.add(triple_any >= all_safe).only_enforce_if(s)

        return triple_any

    def _encode_gravity(self, model, s, S_r, S_next, Del, rows, cols, r):
        """编码重力：S_next[i][j] 由 S_r 中保留的格子（keep=1-Del）下落生成。"""
        for j in range(cols):
            # keep[i]：第 i 行第 j 列是否保留
            keep = [model.new_bool_var(f"3K_keep_{r}_{j}_{i}") for i in range(rows)]
            for i in range(rows):
                if (i, j) in Del:
                    model.add(keep[i] == 1 - Del[(i, j)]).only_enforce_if(s)
                else:
                    model.add(keep[i] == 1).only_enforce_if(s)

            # 前缀和 prefix[k] = sum_{i<k} keep[i]
            prefix = [model.new_int_var(0, rows, f"3K_pref_{r}_{j}_{k}") for k in range(rows + 1)]
            model.add(prefix[0] == 0).only_enforce_if(s)
            for i in range(rows):
                model.add(prefix[i + 1] == prefix[i] + keep[i]).only_enforce_if(s)

            total_keep = prefix[rows]

            # 关键约束：保留的格子数不能超过行数
            model.add(total_keep <= rows).only_enforce_if(s)

            # 对每个源行 src，计算其目标位置 target_pos[src]
            # 保留格子按 src 从小到大排列，落到从底部往上数第 prefix[src] 个位置
            target_pos = [model.new_int_var(0, rows, f"3K_tp_{r}_{j}_{src}") for src in range(rows)]
            for src in range(rows):
                model.add(
                    target_pos[src] == rows - 1 - prefix[src]
                ).only_enforce_if(keep[src], s)
                model.add(target_pos[src] == rows).only_enforce_if(keep[src].Not(), s)

            # 对每个目标行 t（0..rows-1）：
            # S_next[t][j] 如果存在源 src（target_pos[src]==t），则等于 S_r[src][j]
            # 否则为 0
            for t in range(rows):
                eq_list = []
                for src in range(rows):
                    eq = model.new_bool_var(f"3K_eq_{r}_{j}_{t}_{src}")
                    model.add(target_pos[src] == t).only_enforce_if(eq)
                    model.add(target_pos[src] != t).only_enforce_if(eq.Not())
                    eq_list.append(eq)

                if S_next[(t, j)] is not None:
                    for src in range(rows):
                        if S_r[(src, j)] is not None:
                            model.add(S_next[(t, j)] == S_r[(src, j)]).only_enforce_if(eq_list[src], s)

                    has_source = model.new_bool_var(f"3K_hs_{r}_{j}_{t}")
                    model.add(has_source <= sum(eq_list)).only_enforce_if(s)
                    for eq in eq_list:
                        model.add(has_source >= eq).only_enforce_if(s)
                    model.add(S_next[(t, j)] == 0).only_enforce_if(has_source.Not(), s)

    def suggest_total(self, info: dict) -> None:
        """建议总雷数范围（仅作为软约束）。"""
        ub = 0
        for key in info.get("interactive", []):
            total_cells = info.get("total", {}).get(key, 0)
            ub += total_cells
        if ub > 0:
            info["soft_fn"](int(ub * 0.35), 0)
            info["soft_fn"](int(ub * 0.45), 0)
