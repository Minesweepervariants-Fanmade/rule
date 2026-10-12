#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/11 01:30
# @Author  : DeepSeek Agent
# @FileName: 3CM.py
"""
[3CM] 计数雷值：雷值为n的雷恰好有0或n个。具体分布未知。

语义：
- 这是一个雷值(mine-value)规则，配合 [V'] 使用（lib_only=True）。
- 每个雷被赋予一个正整数雷值 n。
- 对每个正整数 n，雷值恰好等于 n 的雷的数量必须是 0 或 n。

生成策略：
- 使用一个小型 CP-SAT 求解一组满足 3CM 的雷值分配；
  若当前题板注册了 [MH] 信号，则同时叠加“每行每列雷值互不相同”的约束；
  若叠加后不可行则回退到仅 3CM；仍不可行则使用确定性的 `_collect_assignment`。
- 求解阶段 create_constraints 穷举所有合法分配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from minesweepervariants.board import Board, Position
    from ....impl.summon.solver import Switch


def _stable_key(row: int, col: int, board_key: str) -> int:
    """与进程无关的稳定哈希，用于对雷格做确定性“随机”排序。"""
    c = 0
    for ch in str(board_key):
        c = (c * 131 + ord(ch)) & 0xFFFFFFFF
    x = (row * 0x9E3779B1) ^ (col * 0x85EBCA77) ^ (c * 0xC2B2AE3D)
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return x


def _distinct_partition(total: int) -> List[int]:
    """
    将 total 分解为若干互不相同的正整数之和。
    total <= 0 时返回空列表。
    例如 10 -> [1,2,3,4]; 12 -> [1,2,3,6]; 14 -> [1,2,3,8]; 15 -> [1,2,3,4,5]。
    """
    if total <= 0:
        return []
    parts: List[int] = []
    remaining = total
    cur = 1
    while remaining > 0:
        if remaining - cur > cur:
            parts.append(cur)
            remaining -= cur
            cur += 1
        else:
            parts.append(remaining)
            remaining = 0
    return parts


class Rule3CM(AbstractMinesRule):
    id = "3CM"
    name = "Count Mine"
    name.zh_CN = "计数雷值"
    doc = ("The number of mines with mine value n is exactly 0 or n. "
           "The concrete distribution is unknown.")
    doc.zh_CN = "雷值为n的雷恰好有0或n个。具体分布未知。"
    tags = ["Variant", "Local", "Mine-Value"]
    creation_time = "2026-10-11"
    lib_only = True
    author = ("NT", 2201963934)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"
        self.onboard_init(board)

    # -------- 类型命名空间 --------
    def onboard_init(self, board: "Board" | None):
        if board is None:
            return
        board.register_type_special("3CM", self._get_type)

    # -------- 分配缓存 --------
    @staticmethod
    def _mines_signature(board: "Board") -> Tuple[Tuple[str, int, int], ...]:
        result = []
        for key in board.get_interactive_keys():
            for pos, t in board(mode="type", key=key, special="raw"):
                if t == "F":
                    result.append((key, pos.row, pos.col))
        result.sort()
        return tuple(result)

    def _collect_assignment(self, board: "Board") -> Dict[Tuple[str, int, int], int]:
        """确定性回退分配：逐题板按稳定哈希排序后按不重复分段填值。"""
        assignment: Dict[Tuple[str, int, int], int] = {}
        for key in board.get_interactive_keys():
            mines: List[Tuple[int, int]] = [
                (pos.row, pos.col)
                for pos, t in board(mode="type", key=key, special="raw")
                if t == "F"
            ]
            mines.sort(key=lambda m: (_stable_key(m[0], m[1], key), m[0], m[1]))
            parts = _distinct_partition(len(mines))
            idx = 0
            for part in parts:
                for _ in range(part):
                    if idx >= len(mines):
                        break
                    r, c = mines[idx]
                    assignment[(key, r, c)] = part
                    idx += 1
        return assignment

    def _get_assignment(self, board: "Board") -> Dict[Tuple[str, int, int], int]:
        sig = self._mines_signature(board)
        meta = getattr(board, "_rule_meta", None)
        if meta is None:
            meta = {}
            try:
                setattr(board, "_rule_meta", meta)
            except Exception:
                return self._solve_assignment(board, with_mh=False) or self._collect_assignment(board)

        cache = meta.get("3CM_assign")
        if cache is not None and cache[0] == sig:
            return cache[1]

        # 3CM 语义为“具体分布未知”，在满足 3CM 的基础上，优先叠加当前题板
        # 实际注册的额外雷值约束（[MH] / [MQ]）。若叠加后不可行则逐级回退。
        # 注意：必须依据 meta 中实际注册的约束来决定是否叠加，而不能无条件
        # 叠加 MH——否则用户只组合 MQ 时，答案板会因为优先满足 MH 而破坏 MQ。
        # （生成阶段 board 的 _rule_meta 保留；渲染/重放阶段 clone 后丢失，
        #   但缓存按 sig 命中，不会改变已生成的答案板。）
        has_mh = "MH" in meta
        has_mq = "MQ" in meta
        if has_mh and has_mq:
            combos = [(True, True), (True, False), (False, True), (False, False)]
        elif has_mh:
            combos = [(True, False), (False, False)]
        elif has_mq:
            combos = [(False, True), (False, False)]
        else:
            combos = [(False, False)]

        assignment = None
        for mh_flag, mq_flag in combos:
            assignment = self._solve_assignment(board, with_mh=mh_flag, with_mq=mq_flag)
            if assignment is not None:
                break
        if assignment is None:
            assignment = self._collect_assignment(board)

        meta["3CM_assign"] = (sig, assignment)
        return assignment

    def _solve_assignment(self, board: "Board", with_mh: bool, with_mq: bool = False) -> Optional[Dict[Tuple[str, int, int], int]]:
        """
        用 CP-SAT 求一组满足 3CM 的雷值分配；
        with_mh=True 时额外要求同一行/列内雷值互不相同；
        with_mq=True 时额外要求任意 2x2 内的雷值互不相同。
        """
        from ortools.sat.python import cp_model

        mines: List[Tuple[str, int, int]] = list(self._mines_signature(board))
        n = len(mines)
        if n == 0:
            return {}

        # 每个 key 内的雷数
        key_counts: Dict[str, int] = {}
        for key, _, _ in mines:
            key_counts[key] = key_counts.get(key, 0) + 1

        model = cp_model.CpModel()
        val = [
            model.new_int_var(1, key_counts[key], f"3CM_v_{i}")
            for i, (key, _, _) in enumerate(mines)
        ]

        # 3CM 全局约束：每个 key 内，对于每个 n，val==n 的数量为 0 或 n
        for key, nk in key_counts.items():
            idxs = [i for i, (k, _, _) in enumerate(mines) if k == key]
            for nv in range(1, nk + 1):
                eqs = []
                for i in idxs:
                    b = model.new_bool_var(f"3CM_eq_{key}_{i}_{nv}")
                    model.add(val[i] == nv).only_enforce_if(b)
                    model.add(val[i] != nv).only_enforce_if(b.Not())
                    eqs.append(b)
                cnt = model.new_int_var(0, nk, f"3CM_cnt_{key}_{nv}")
                model.add(cnt == sum(eqs))
                is_zero = model.new_bool_var(f"3CM_zero_{key}_{nv}")
                model.add(cnt == 0).only_enforce_if(is_zero)
                model.add(cnt != 0).only_enforce_if(is_zero.Not())
                is_n = model.new_bool_var(f"3CM_isn_{key}_{nv}")
                model.add(cnt == nv).only_enforce_if(is_n)
                model.add(cnt != nv).only_enforce_if(is_n.Not())
                model.add_bool_or([is_zero, is_n])

        # 可选叠加 MH：每行每列内雷值互不相同
        if with_mh:
            by_row: Dict[Tuple[str, int], List] = {}
            by_col: Dict[Tuple[str, int], List] = {}
            for i, (key, r, c) in enumerate(mines):
                by_row.setdefault((key, r), []).append(val[i])
                by_col.setdefault((key, c), []).append(val[i])
            for group in list(by_row.values()) + list(by_col.values()):
                if len(group) >= 2:
                    model.add_all_different(group)

        # 可选叠加 MQ：任意 2x2 内的雷值互不相同
        if with_mq:
            # 收集每个 key 下所有雷格坐标 -> 索引的映射
            mines_by_key: Dict[str, Dict[Tuple[int, int], int]] = {}
            for i, (key, r, c) in enumerate(mines):
                mines_by_key.setdefault(key, {})[(r, c)] = i
            # 遍历每个 key 下所有可能的 2x2 左上角 (r, c)，
            # 覆盖所有实际存在的 2x2，而不仅限于左上角是雷格的那些。
            for key, cell_map in mines_by_key.items():
                boundary = board.boundary(key)
                max_r = boundary.row
                max_c = boundary.col
                for r in range(max_r):
                    for c in range(max_c):
                        quad = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
                        idxs = [cell_map[cell] for cell in quad if cell in cell_map]
                        if len(idxs) >= 2:
                            model.add_all_different([val[i] for i in idxs])

        solver = cp_model.CpSolver()
        solver.parameters.random_seed = 42
        solver.parameters.num_search_workers = 1
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        return {
            (key, r, c): solver.value(val[i])
            for i, (key, r, c) in enumerate(mines)
        }

    def _get_type(self, board: "Board", pos: "Position", *args, **kwargs) -> int:
        raw = board.get_type(pos, special=self.rule)
        if self.rule == 'raw':
            is_mine = (raw == 'F')
        else:
            try:
                is_mine = int(raw) != 0
            except (TypeError, ValueError):
                is_mine = False
        if not is_mine:
            return 0
        assignment = self._get_assignment(board)
        return assignment.get((pos.board_key, pos.row, pos.col), 1)

    # -------- 约束 --------
    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions: List["Position"] = [pos for pos, _ in board(key=key)]
            ub = len(positions)
            if ub == 0:
                continue

            val_vars: Dict[Tuple[int, int], object] = {}
            for pos in positions:
                mine = board.get_variable(pos, special="raw")
                val = board.get_variable(pos, special="3CM")
                val_vars[(pos.row, pos.col)] = val
                model.add(val >= 0)
                model.add(val <= ub)
                model.add(val == 0).only_enforce_if(mine.Not())
                model.add(val >= 1).only_enforce_if(mine)

            # 统计每个取值 n 的出现次数，并约束为 0 或 n
            for n in range(1, ub + 1):
                eq_vars = []
                for pos in positions:
                    val = val_vars[(pos.row, pos.col)]
                    b = model.new_bool_var(f"3CM_eq_{key}_{pos.row}_{pos.col}_{n}")
                    model.add(val == n).only_enforce_if(b)
                    model.add(val != n).only_enforce_if(b.Not())
                    eq_vars.append(b)
                cnt = model.new_int_var(0, ub, f"3CM_cnt_{key}_{n}")
                model.add(cnt == sum(eq_vars))
                is_zero = model.new_bool_var(f"3CM_zero_{key}_{n}")
                model.add(cnt == 0).only_enforce_if(is_zero)
                model.add(cnt != 0).only_enforce_if(is_zero.Not())
                is_n = model.new_bool_var(f"3CM_isn_{key}_{n}")
                model.add(cnt == n).only_enforce_if(is_n)
                model.add(cnt != n).only_enforce_if(is_n.Not())
                model.add_bool_or([is_zero, is_n]).only_enforce_if(s)

    def get_deps(self) -> List[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
