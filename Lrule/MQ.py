#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/13 01:19
# @Author  : DeepSeek Agent
# @FileName: MQ.py
"""
[MQ] 雷值无方：任意2x2内的雷的雷值不能重复。

语义：
- 这是一个雷值左线规则（它不是雷值规则，而是对已有雷值规则添加约束）。
- 需要配合一个提供雷值的规则使用（如 [3CM]、[3CM']、[1M]、[1N]、[4S] 等）。
- 对每一个 2x2 区域，其中的所有雷格（类型 F）的雷值必须两两互不相同。

用法：
- 通过 data 参数指定要读取的雷值命名空间，例如 `MQ:3CM`。
- 当未指定 data 时，规则会自动探测当前题板上已注册的非 `raw` 雷值命名空间。

实现说明：
- 参考 [MH] 的实现模式。
- 因为 3CM/3CM' 等“分配自由型”雷值规则在生成阶段使用独立的小型 CP-SAT 求解雷值分配，
  本规则在实例化时会通过 `board._rule_meta["MQ"]` 注册一个信号，
  这些规则在求解雷值分配时会读取该信号并添加等价约束，从而保证答案板的雷值分布满足 MQ。
- 同时，本规则的 create_constraints 会直接对雷值变量添加约束，
  供一般求解/验证路径使用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from minesweepervariants.board import Board, Position
    from ....impl.summon.solver import Switch


class RuleMQ(AbstractMinesRule):
    id = "MQ"
    name = "Mine Quad"
    name.zh_CN = "雷值无方"
    doc = ("In any 2x2 area, all mines must have pairwise distinct mine values. "
           "This rule does not change mine values; it constrains another mine-value rule.")
    doc.zh_CN = ("任意2x2内的雷的雷值不能重复。"
                 "该规则不改变雷值，只对其他雷值规则添加约束。")
    tags = ["Variant", "Local", "Mine-Value"]
    creation_time = "2026-10-13"
    author = ("NT", 2201963934)

    def __init__(self, board: "Board" = None, data: Optional[str] = None) -> None:
        super().__init__(board, data)
        self._data_rule: Optional[str] = data
        if board is not None:
            # 在规则实例化阶段即注册 MQ 信号，
            # 以便 3CM/3CM' 等“分配自由型”雷值规则在生成雷值分配时能读取到。
            self._register_meta(board, data)

    # -------- 命名空间解析 --------
    def _resolve_rule(self, board: "Board") -> Optional[str]:
        """
        决定读取哪个命名空间下的雷值变量。
        优先使用 data 参数指定的命名空间；否则自动探测已注册的非 raw 雷值命名空间。
        """
        if self._data_rule is not None and self._data_rule != "":
            return self._data_rule

        candidates = set()
        for key in board.get_board_keys():
            board_data = board.board_data.get(key)
            if not board_data:
                continue
            type_special = board_data.get("type_special", {})
            for name in type_special.keys():
                if name == "raw" or name == self.id:
                    continue
                candidates.add(name)

        if not candidates:
            return None

        # 优先选择常见雷值命名空间
        preferred_prefixes = ("3CM", "1M", "1N", "4S")
        for pref in preferred_prefixes:
            matches = sorted(c for c in candidates if c.startswith(pref))
            if matches:
                return matches[0]
        return sorted(candidates)[0]

    # -------- 注册 meta（供分配自由型雷值规则在生成阶段读取） --------
    def _register_meta(self, board: "Board", rule: Optional[str]) -> None:
        meta = getattr(board, "_rule_meta", None)
        if meta is None:
            meta = {}
            try:
                board._rule_meta = meta
            except Exception:
                return
        meta["MQ"] = {
            "rule": rule if rule else None,
        }

    # -------- 约束 --------
    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        model = board.get_model()
        s = switch.get(model, self)

        rule = self._resolve_rule(board)
        if rule is None or rule == "raw":
            # 没有可用的雷值命名空间：不添加约束（语义无法实现）
            return

        # 命名空间必须已注册
        if not board.has_type_special(rule):
            return

        # 再次确保 meta 已注册（补充 data 未指定的情况）
        self._register_meta(board, rule)

        for key in board.get_interactive_keys():
            positions: List["Position"] = [pos for pos, _ in board(key=key)]
            if len(positions) < 2:
                continue

            mine_vars: Dict[tuple, object] = {}
            val_vars: Dict[tuple, object] = {}
            for pos in positions:
                mine_vars[(pos.row, pos.col)] = board.get_variable(pos, special="raw")
                val_vars[(pos.row, pos.col)] = board.get_variable(pos, special=rule)

            boundary = board.boundary(key)
            # 遍历所有 2x2 块（左上角 (r, c)，覆盖 (r,c),(r,c+1),(r+1,c),(r+1,c+1)）
            for r in range(boundary.row):
                for c in range(boundary.col):
                    cells = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
                    valid_cells = []
                    for (rr, cc) in cells:
                        m = mine_vars.get((rr, cc))
                        v = val_vars.get((rr, cc))
                        if m is None or v is None:
                            valid_cells = []
                            break
                        valid_cells.append((m, v))
                    if len(valid_cells) < 2:
                        continue
                    n = len(valid_cells)
                    # 任意两个雷格如果都是雷，则它们的雷值必须互不相同
                    for i in range(n):
                        for j in range(i + 1, n):
                            m1, v1 = valid_cells[i]
                            m2, v2 = valid_cells[j]
                            model.add(v1 != v2).only_enforce_if([m1, m2, s])
