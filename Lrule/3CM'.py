#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/12
# @Author  : DeepSeek Agent
# @FileName: 3CM'.py
"""
[3CM'] 简单计数雷值：每个雷值为n的雷所在的行和列中总共恰好有n个雷值为n的雷。具体分布未知。

语义：
- 这是一个雷值(mine-value)规则，配合 [V'] 使用（lib_only=True）。
- 每个雷被赋予一个正整数雷值 n。
- 对每个雷值为 n 的雷格 p，p 所在行 ∪ 列（并集，含 p 自身）中雷值恰好为 n 的雷的数量必须等于 n。
- 生成阶段使用 CP-SAT 求解一组满足约束的雷值分配（以雷布局为键缓存）；
  求解阶段由 create_constraints 穷举所有合法分配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Tuple

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from minesweepervariants.board import Board, Position
    from ....impl.summon.solver import Switch


class Rule3CMp(AbstractMinesRule):
    id = "3CM'"
    name = "Simple Count Mine"
    name.zh_CN = "简单计数雷值"
    doc = ("Each mine with value n must have exactly n mines with value n "
           "in its row and column (union). The concrete distribution is unknown.")
    doc.zh_CN = "每个雷值为n的雷所在的行和列中总共恰好有n个雷值为n的雷。具体分布未知。"
    tags = ["Variant", "Local", "Mine-Value", "Creative"]
    creation_time = "2026-10-12"
    lib_only = True
    author = ("NT", 2201963934)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"
        self._assignment_cache: Dict[Tuple, Dict[Tuple[str, int, int], int]] = {}
        self.onboard_init(board)

    # -------- 类型命名空间 --------
    def onboard_init(self, board: "Board" | None):
        if board is None:
            return
        board.register_type_special("3CM'", self._get_type)

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

    def _get_assignment(self, board: "Board"):
        sig = self._mines_signature(board)
        if sig in self._assignment_cache:
            return self._assignment_cache[sig]
        assignment = self._solve_assignment(board)
        if len(self._assignment_cache) > 64:
            self._assignment_cache.clear()
        self._assignment_cache[sig] = assignment
        return assignment

    def _solve_assignment(self, board: "Board"):
        """使用一个小型 CP-SAT 模型求一组满足 3CM' 约束的雷值分配。"""
        from ortools.sat.python import cp_model

        mines: List[Tuple[str, int, int]] = [
            (key, pos.row, pos.col)
            for key in board.get_interactive_keys()
            for pos, t in board(mode="type", key=key, special="raw")
            if t == "F"
        ]
        n = len(mines)
        if n == 0:
            return {}

        model = cp_model.CpModel()
        # 每个雷格的上限 = 其行列并集中的雷数
        ub_list = []
        for i, (key, r, c) in enumerate(mines):
            cnt = sum(
                1 for (k2, r2, c2) in mines
                if k2 == key and (r2 == r or c2 == c)
            )
            ub_list.append(max(cnt, 1))
        val = [model.new_int_var(1, ub_list[i], f"3CMp_v_{i}") for i in range(n)]

        for i, (key, r, c) in enumerate(mines):
            row_col = [
                j for j, (k2, r2, c2) in enumerate(mines)
                if k2 == key and (r2 == r or c2 == c)
            ]
            ub_i = len(row_col)
            for nv in range(1, ub_i + 1):
                cond = model.new_bool_var(f"3CMp_c_{i}_{nv}")
                model.add(val[i] == nv).only_enforce_if(cond)
                model.add(val[i] != nv).only_enforce_if(cond.Not())
                inds = []
                for j in row_col:
                    eq = model.new_bool_var(f"3CMp_e_{i}_{nv}_{j}")
                    model.add(val[j] == nv).only_enforce_if(eq)
                    model.add(val[j] != nv).only_enforce_if(eq.Not())
                    inds.append(eq)
                model.add(sum(inds) == nv).only_enforce_if(cond)

        solver = cp_model.CpSolver()
        solver.parameters.random_seed = 42
        solver.parameters.num_search_workers = 1
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        result = {}
        for i, (key, r, c) in enumerate(mines):
            result[(key, r, c)] = solver.value(val[i])
        return result

    def _get_type(self, board: "Board", pos: "Position", *args, **kwargs) -> int:
        if self.rule == 'raw':
            raw = board.get_type(pos, special='raw')
            is_mine = (raw == 'F')
        else:
            raw = board.get_type(pos, special=self.rule)
            try:
                is_mine = int(raw) != 0
            except (TypeError, ValueError):
                is_mine = False
        if not is_mine:
            return 0
        assignment = self._get_assignment(board)
        if assignment is None:
            return 1
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
                val = board.get_variable(pos, special="3CM'")
                val_vars[(pos.row, pos.col)] = val
                model.add(val >= 0)
                model.add(val <= ub)
                model.add(val == 0).only_enforce_if(mine.Not())
                model.add(val >= 1).only_enforce_if(mine)

            eq_vars: Dict[Tuple[int, int, int], object] = {}
            for pos in positions:
                for nv in range(1, ub + 1):
                    eq = model.new_bool_var(
                        f"3CMp_eq_{key}_{pos.row}_{pos.col}_{nv}"
                    )
                    model.add(val_vars[(pos.row, pos.col)] == nv).only_enforce_if(eq)
                    model.add(val_vars[(pos.row, pos.col)] != nv).only_enforce_if(eq.Not())
                    eq_vars[(pos.row, pos.col, nv)] = eq

            for pos in positions:
                row_col_set = set(board.get_row_pos(pos)) | set(board.get_col_pos(pos))
                row_col = sorted(row_col_set, key=lambda p: (p.row, p.col))
                ub_pos = min(ub, len(row_col))
                for nv in range(1, ub_pos + 1):
                    inds = []
                    for q in row_col:
                        eq = eq_vars.get((q.row, q.col, nv))
                        if eq is not None:
                            inds.append(eq)
                    if not inds:
                        continue
                    eq_pos = eq_vars.get((pos.row, pos.col, nv))
                    if eq_pos is None:
                        continue
                    model.add(sum(inds) == nv).only_enforce_if([eq_pos, s])

    def get_deps(self) -> List[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
