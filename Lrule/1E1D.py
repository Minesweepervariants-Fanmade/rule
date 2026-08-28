#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-29
# @Author  : 萌 (1219009468)
# @FileName: 1E1D.py
"""
[1E1D] 视野对偶：每个雷同行列中最近的雷恰有一个，它们是彼此的同行列中最近的雷

语义等价表述：
- 所有雷可以分成若干对，每对包含两个雷
- 每对中的两个雷在同一行或同一列
- 每对中的两个雷之间没有其他雷（即它们在该行/列上是相邻的雷）
- 每个雷恰好属于一对
"""

from typing import Dict, Tuple, List, Optional
from ortools.sat.python.cp_model import IntVar, CpModel

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position
from ....impl.summon.solver import Switch
from ....utils.tool import get_logger


class Rule1E1D(AbstractMinesRule):
    """
    [1E1D] 视野对偶：每个雷同行列中最近的雷恰有一个，它们是彼此的同行列中最近的雷
    """

    id = "1E1D"
    name = "Eyesight Dual"
    name.zh_CN = "视野对偶"
    doc = (
        "For each mine, there is exactly one nearest mine in its row or column, "
        "and they are each other's nearest mine in the row or column."
    )
    doc.zh_CN = "每个雷同行列中最近的雷恰有一个，它们是彼此的同行列中最近的雷"
    author = ("萌", 1219009468)
    tags = ["Variant", "Local", "Mine-Position", "Strict R"]
    creation_time = "2026-08-29"

    def __init__(self, board: Optional["Board"] = None, data: Optional[str] = None) -> None:
        super().__init__(board, data)

    def _is_same_row_or_col(self, p1: Position, p2: Position) -> bool:
        """判断两个位置是否在同一行或同一列"""
        return p1.row == p2.row or p1.col == p2.col

    def _positions_between(self, p1: Position, p2: Position, board: Board) -> List[Position]:
        """
        返回两个位置之间（不包括端点）在同一行或同一列上的所有位置。
        仅当 p1 和 p2 在同一行或同一列时有效。
        """
        if p1.row == p2.row:
            # 同一行
            row = p1.row
            col_min = min(p1.col, p2.col)
            col_max = max(p1.col, p2.col)
            positions = []
            for col in range(col_min + 1, col_max):
                pos = board.get_pos(row, col, p1.board_key)
                if pos is not None and board.is_valid(pos):
                    positions.append(pos)
            return positions
        elif p1.col == p2.col:
            # 同一列
            col = p1.col
            row_min = min(p1.row, p2.row)
            row_max = max(p1.row, p2.row)
            positions = []
            for row in range(row_min + 1, row_max):
                pos = board.get_pos(row, col, p1.board_key)
                if pos is not None and board.is_valid(pos):
                    positions.append(pos)
            return positions
        return []

    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        """
        添加 CP-SAT 约束，确保每个雷恰好与另一个雷配对，
        配对的雷在同一行或同一列，且它们之间没有其他雷。
        """
        model: CpModel = board.get_model()
        if model is None:
            get_logger().warning("[1E1D] 无法获取 CpModel，跳过约束创建")
            return

        rule_switch = switch.get(model, self)

        # 对每个交互式题板独立处理
        for key in board.get_interactive_keys():
            # 收集该题板的所有有效位置及其雷变量
            positions: List[Position] = []
            mine_vars: Dict[Position, IntVar] = {}
            for pos, var in board(key=key, mode="variable", special="raw"):
                if pos is None or var is None:
                    continue
                if not board.is_valid(pos):
                    continue
                positions.append(pos)
                mine_vars[pos] = var

            n = len(positions)
            if n == 0:
                continue

            # 位置索引映射，用于快速访问
            pos_to_idx: Dict[Position, int] = {pos: idx for idx, pos in enumerate(positions)}

            # --- 1. 创建配对变量 pair[i][j] ---
            # pair[i][j] 表示位置 i 和位置 j 配对
            # 只对同行或同列的位置对创建配对变量
            pair_vars: Dict[Tuple[int, int], IntVar] = {}

            # 为了后续方便，也存储 pair 变量到位置对的映射
            pair_pos_to_var: Dict[Tuple[Position, Position], IntVar] = {}

            for i in range(n):
                for j in range(i + 1, n):
                    p1 = positions[i]
                    p2 = positions[j]
                    if not self._is_same_row_or_col(p1, p2):
                        continue

                    var_name = f"1E1D_pair_{key}_{p1.row}_{p1.col}_{p2.row}_{p2.col}"
                    pair_var = model.NewBoolVar(var_name)
                    pair_vars[(i, j)] = pair_var
                    pair_vars[(j, i)] = pair_var
                    pair_pos_to_var[(p1, p2)] = pair_var
                    pair_pos_to_var[(p2, p1)] = pair_var

                    # --- 2. 配对约束：如果配对，则两个位置都必须是雷 ---
                    # pair[i][j] => mine[i] AND mine[j]
                    model.Add(pair_var <= mine_vars[p1]).OnlyEnforceIf(rule_switch)
                    model.Add(pair_var <= mine_vars[p2]).OnlyEnforceIf(rule_switch)

                    # --- 3. 配对约束：配对的两个雷之间不能有其他雷 ---
                    # pair[i][j] => 中间所有位置都不是雷
                    between = self._positions_between(p1, p2, board)
                    for mid_pos in between:
                        mid_var = mine_vars.get(mid_pos)
                        if mid_var is not None:
                            # pair_var => NOT mid_var
                            model.Add(pair_var + mid_var <= 1).OnlyEnforceIf(rule_switch)

            # --- 4. 每个雷恰好配对一个雷 ---
            # 对于每个位置 i： sum_j pair[i][j] == mine[i]
            # 如果该位置是雷，则恰好配对一个；如果不是雷，则不配对
            for i in range(n):
                pos = positions[i]
                incident_pairs = []
                for j in range(n):
                    if i == j:
                        continue
                    if (i, j) in pair_vars:
                        incident_pairs.append(pair_vars[(i, j)])
                if incident_pairs:
                    model.Add(sum(incident_pairs) == mine_vars[pos]).OnlyEnforceIf(rule_switch)
                else:
                    # 如果没有可配对的位置，则该位置不能是雷
                    model.Add(mine_vars[pos] == 0).OnlyEnforceIf(rule_switch)

            # --- 5. 配对对称性（由 pair_vars 的对称存储保证）---
            # 已经通过 pair_vars[(i,j)] = pair_vars[(j,i)] 保证了对称性

        # 记录调试信息
        get_logger().debug("[1E1D] 约束创建完成")

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数：由于每个雷都配对到另一个雷，总雷数必须为偶数。
        添加硬约束确保总雷数为偶数，并提供一个软约束建议总雷数约为总格子数的 40%。
        """
        ub = 0
        for key in info.get("interactive", []):
            total_cells = info.get("total", {}).get(key, 0)
            ub += total_cells

        # 硬约束：总雷数必须为偶数
        def hard_constraint(model: CpModel, total: IntVar) -> None:
            model.AddModuloEquality(0, total, 2)

        info["hard_fns"].append(hard_constraint)

        # 软约束：建议总雷数约为总格子数的 40%
        target = int(ub * 0.4)
        if target % 2 == 1:
            target += 1  # 确保偶数
        info["soft_fn"](target, 0)

        get_logger().debug(f"[1E1D] suggest_total: ub={ub}, target={target}")
