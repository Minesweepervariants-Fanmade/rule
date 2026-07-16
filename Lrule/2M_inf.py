"""
[2M''∞] 无穷多雷：每行每列恰好有一个雷值为∞
"""
from typing import List, Optional

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel


class Rule2M_inf(AbstractMinesRule):
    id = "2M''∞"
    aliases = ("inf", "Inf", "INF")
    name = "Infinite Mines"
    name.zh_CN = "无穷多雷"
    doc = "Exactly one mine with value ∞ per row and per column"
    doc.zh_CN = "每行每列恰好有一个雷值为∞"
    tags = ["Variant", "Global", "Mine-Counting"]
    creation_time = "2026-07-17"
    lib_only = False
    author = ("NT", 2201963934)

    def __init__(self, board: Optional['Board'] = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        为每行每列添加恰好一个雷的约束。
        """
        model: CpModel = board.get_model()
        keys = board.get_interactive_keys()
        if not keys:
            return
        key = keys[0]

        # 获取边界（行数和列数）
        boundary_pos = board.boundary(key)
        rows = boundary_pos.row + 1
        cols = boundary_pos.col + 1

        # 收集所有有效位置
        row_positions = [[] for _ in range(rows)]
        col_positions = [[] for _ in range(cols)]

        for r in range(rows):
            for c in range(cols):
                pos = Position(c, r, key)
                if board.is_valid(pos):
                    row_positions[r].append(pos)
                    col_positions[c].append(pos)

        # 对每一行，添加恰好一个雷的约束
        for r, positions in enumerate(row_positions):
            if positions:
                vars_ = [board.get_variable(pos) for pos in positions]
                model.Add(sum(vars_) == 1)

        # 对每一列，添加恰好一个雷的约束
        for c, positions in enumerate(col_positions):
            if positions:
                vars_ = [board.get_variable(pos) for pos in positions]
                model.Add(sum(vars_) == 1)

    def get_deps(self) -> List[str]:
        return []

    def companion_id(self) -> Optional[str]:
        return None
