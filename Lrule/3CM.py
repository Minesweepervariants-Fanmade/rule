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
- 生成阶段随机分配（此处采用与雷布局绑定的确定性伪随机分配，保证 clone 一致性）；
  求解阶段穷举所有合法分配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple

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

    def _collect_assignment(self, board: "Board") -> Dict[Tuple[str, int, int], int]:
        """基于当前题板的雷布局（逐题板）计算一个确定性雷值分配。"""
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
        sig = tuple(sorted(
            (pos.board_key, pos.row, pos.col)
            for key in board.get_interactive_keys()
            for pos, t in board(mode="type", key=key, special="raw")
            if t == "F"
        ))
        meta = getattr(board, "_rule_meta", None)
        if meta is None:
            meta = {}
            try:
                setattr(board, "_rule_meta", meta)
            except Exception:
                return self._collect_assignment(board)
        cache = meta.get("3CM_assign")
        if cache is not None and cache[0] == sig:
            return cache[1]
        assignment = self._collect_assignment(board)
        meta["3CM_assign"] = (sig, assignment)
        return assignment

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
