"""
[IG] 四邻非一：对于任意非雷格，其周围4格雷数不为1
"""

from typing import Optional
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class IG(AbstractMinesRule):
    """
    IG 规则：禁止非雷格周围四格雷数恰好为1。
    """
    id = "IG"
    name = "四邻非一"
    name.zh_CN = "四邻非一"
    doc = "For any non-mine cell, the number of mines among its four orthogonal neighbors must not be 1."
    doc.zh_CN = "对于任意非雷格，其周围4格雷数不为1"
    author = ("QuirkyStorm7988（备战高考） (2943562293)", 2943562293)
    tags = ["Anti-Construction", "Local", "Weak"]
    creation_time = "2026-07-23"

    def create_constraints(self, board: Board, switch):
        """
        添加约束：对于每个位置，如果它不是雷，则其四个正交邻居中的雷数不能为1。
        使用 BoolOr 约束禁止恰好一个邻居为雷的情况。
        """
        model = board.get_model()
        if model is None:
            return

        # 获取当前规则的开关变量（用于启用/禁用此规则）
        rule_switch = switch.get(model, self)

        # 遍历所有位置
        for pos, var in board(mode="variable"):
            # 只处理有效的、非掩码的位置
            if not board.is_valid(pos):
                continue

            # 收集四个正交邻居的变量（只包括有效位置）
            neighbor_vars = []
            neighbor_positions = []
            for neighbor in pos.neighbors(1):  # 曼哈顿距离为1的四个邻居
                if board.is_valid(neighbor):
                    n_var = board.get_variable(neighbor)
                    if n_var is not None:
                        neighbor_vars.append(n_var)
                        neighbor_positions.append(neighbor)

            # 如果没有邻居，周围雷数恒为0，不为1，无需约束
            if not neighbor_vars:
                continue

            # 对于每个邻居 i，禁止“当前格非雷 且 只有邻居 i 是雷，其他邻居都不是雷”
            # 即：var == 0 且 n_i == 1 且 所有其他邻居 n_j == 0 不能同时成立
            # 等价于：var == 1 或 n_i == 0 或 至少一个其他邻居为1
            # 用 BoolOr 实现：
            #   [var, n_i.Not(), n_0, n_1, ..., n_{i-1}, n_{i+1}, ...]
            for i, n_var in enumerate(neighbor_vars):
                # 构建 literals：var 本身，n_i 的反，以及其他邻居的正变量
                literals = [var]  # var == 1 则满足约束
                literals.append(n_var.Not())  # n_i == 0 则满足约束
                # 添加其他邻居的正变量（至少一个为1则满足约束）
                for j, other_var in enumerate(neighbor_vars):
                    if i != j:
                        literals.append(other_var)

                # 添加约束，并关联到规则开关
                model.AddBoolOr(literals).OnlyEnforceIf(rule_switch)

    def suggest_total(self, info: dict):
        """
        建议雷总数。此规则本身不强制特定总数，但可提供软约束或硬约束。
        """
        # 此规则不强制总数，留空即可
        pass

    def init_board(self, board: Board) -> bool:
        """
        初始化题板时无需特殊操作，返回 True。
        """
        return True

    def init_clear(self, board: Board) -> None:
        """
        清除阶段无需特殊操作。
        """
        pass

    def combine(self, other) -> Optional['IG']:
        """
        规则合并优化：不支持合并，返回 None。
        """
        return None

    def get_deps(self) -> list[str]:
        """
        返回依赖的其他规则名称列表。此规则无依赖。
        """
        return []
