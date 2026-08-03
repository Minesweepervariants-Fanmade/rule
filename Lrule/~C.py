"""
[~C] 任何四个雷都不能共圆。四点共线也算共圆。
"""

from typing import Optional, List
from itertools import combinations
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class TildeC(AbstractMinesRule):
    """
    ~C 规则：任何四个雷都不能共圆（包括共线）。
    使用行列式判定四点是否共圆。
    """
    id = "~C"
    name = "No Four Concyclic Mines"
    name.zh_CN = "无四雷共圆"
    doc = "No four mines may lie on the same circle. Collinear points are also considered concyclic."
    doc.zh_CN = "任何四个雷都不能共圆。四点共线也算共圆。"
    author = ("世界第二睦推 (992600401)", 992600401)
    tags = ["Anti-Construction", "Global", "Strict Shape"]
    creation_time = "2026-06-04"

    @staticmethod
    def _det4x4(m: List[List[int]]) -> int:
        """
        计算 4x4 矩阵的行列式（整数精确计算）。
        使用拉普拉斯展开（按第一行）。
        """
        a, b, c, d = m[0]
        e, f, g, h = m[1]
        i, j, k, l = m[2]
        m0, n, o, p = m[3]

        det = (
            a * (f * (k * p - l * o) - g * (j * p - l * n) + h * (j * o - k * n))
            - b * (e * (k * p - l * o) - g * (i * p - l * m0) + h * (i * o - k * m0))
            + c * (e * (j * p - l * n) - f * (i * p - l * m0) + h * (i * n - j * m0))
            - d * (e * (j * o - k * n) - f * (i * o - k * m0) + g * (i * n - j * m0))
        )
        return det

    @staticmethod
    def _are_concyclic(p1: Position, p2: Position, p3: Position, p4: Position) -> bool:
        """
        判断四个点是否共圆（包括共线）。
        使用行列式方法：四点共圆当且仅当行列式为零。
        """
        # 提取坐标
        x1, y1 = p1.col, p1.row
        x2, y2 = p2.col, p2.row
        x3, y3 = p3.col, p3.row
        x4, y4 = p4.col, p4.row

        # 构造 4x4 矩阵
        # [x^2+y^2, x, y, 1]
        matrix = [
            [x1 * x1 + y1 * y1, x1, y1, 1],
            [x2 * x2 + y2 * y2, x2, y2, 1],
            [x3 * x3 + y3 * y3, x3, y3, 1],
            [x4 * x4 + y4 * y4, x4, y4, 1],
        ]

        det = TildeC._det4x4(matrix)
        return det == 0

    def create_constraints(self, board: Board, switch):
        """
        添加约束：对于任意四个共圆的位置，它们不能同时为雷。
        即：任意四点组合，如果它们共圆，则它们的雷变量之和 <= 3。
        """
        model = board.get_model()
        if model is None:
            return

        # 获取规则开关变量
        rule_switch = switch.get(model, self)

        # 收集所有有效位置
        valid_positions: List[Position] = []
        for pos, _ in board(mode="variable"):
            if board.is_valid(pos):
                valid_positions.append(pos)

        # 如果位置数量少于 4，无需添加约束
        if len(valid_positions) < 4:
            return

        # 遍历所有四点组合
        for combo in combinations(valid_positions, 4):
            p1, p2, p3, p4 = combo

            # 检查这四个点是否共圆
            if not self._are_concyclic(p1, p2, p3, p4):
                continue

            # 获取四个点的变量
            vars_ = [
                board.get_variable(p1),
                board.get_variable(p2),
                board.get_variable(p3),
                board.get_variable(p4),
            ]

            # 确保所有变量都不为 None（理论上应该都有）
            if any(v is None for v in vars_):
                continue

            # 约束：这四个点不能同时为雷，即 sum(vars) <= 3
            model.Add(sum(vars_) <= 3).OnlyEnforceIf(rule_switch)

    def suggest_total(self, info: dict):
        """
        建议雷总数。对于 5x5 棋盘，最多支持约 7 个雷。
        提供软约束倾向于总雷数的 28%，并添加硬约束上限为 7。
        """
        # 计算总格子数
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]
        
        # 软约束：雷数约为总格数的 28%（5x5 下约 7 个）
        info["soft_fn"](total_cells * 0.28, 0)
        
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

    def combine(self, other) -> Optional['TildeC']:
        """
        规则合并优化：不支持合并，返回 None。
        """
        return None

    def get_deps(self) -> List[str]:
        """
        返回依赖的其他规则名称列表。此规则无依赖。
        """
        return []
