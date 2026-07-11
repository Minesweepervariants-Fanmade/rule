"""
[UC] UnCross：题板上不允许出现一颗雷的上下左右均为雷的构造（边界外视为0）
"""

from typing import Optional
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class UC(AbstractMinesRule):
    """
    UnCross 规则：禁止出现十字形雷构造（上下左右均为雷）。
    """
    id = "UC"
    name = "UnCross"
    name.zh_CN = "反十字雷"
    doc = "No cell may have mines on all four orthogonal neighbors."
    doc.zh_CN = "题板上不允许出现一颗雷的上下左右均为雷的构造（边界外视为0）"
    author = ("雾 (3140864122)", 3140864122)
    tags = ["Anti-Construction", "Local"]
    creation_time = "2026-07-11"

    def create_constraints(self, board: Board, switch):
        """
        添加约束：对于每个位置，如果它是雷，则其上下左右邻居中至少有一个不是雷。
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
            for neighbor in pos.neighbors(1):  # 曼哈顿距离为1的四个邻居
                if board.is_valid(neighbor):
                    n_var = board.get_variable(neighbor)
                    if n_var is not None:
                        neighbor_vars.append(n_var)

            # 如果邻居数量少于4，说明部分在边界外，无法形成四雷构造，无需约束
            if len(neighbor_vars) < 4:
                continue

            # 约束：如果当前格是雷，则四个邻居不能全为雷
            # 即：var == 1 => sum(neighbor_vars) <= 3
            # 等价于：not var OR not n1 OR not n2 OR not n3 OR not n4
            literals = [var.Not()] + [n_var.Not() for n_var in neighbor_vars]

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

    def combine(self, other) -> Optional['UC']:
        """
        规则合并优化：不支持合并，返回 None。
        """
        return None

    def get_deps(self) -> list[str]:
        """
        返回依赖的其他规则名称列表。此规则无依赖。
        """
        return []
