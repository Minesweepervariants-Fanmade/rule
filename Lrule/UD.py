"""
[UD] 双子: 1.有且仅有两行雷数相等。2.有且仅有两列雷数相等
"""
from typing import Optional
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class UD(AbstractMinesRule):
    """
    双子规则：恰好有两行雷数相等，且恰好有两列雷数相等。
    """
    id = "UD"
    name = "Twin"
    name.zh_CN = "双子"
    doc = "1. Exactly two rows have the same mine count. 2. Exactly two columns have the same mine count."
    doc.zh_CN = "1. 有且仅有两行雷数相等。2. 有且仅有两列雷数相等。"
    author = ("未知 (740652480)", 740652480)
    tags = ["Original", "Global", "Strict R"]
    creation_time = "2026-08-01"

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        # 获取开关变量（用于启用/禁用此规则）
        s1 = switch.get(model, self)  # 行约束开关
        s2 = switch.get(model, self)  # 列约束开关

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            # 获取所有行位置和列位置（参考1B.py）
            row_positions = board.get_row_pos(boundary_pos)
            col_positions = board.get_col_pos(boundary_pos)

            # ---------- 计算每行雷数 ----------
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]

            # 行约束：恰好有一对行雷数相等
            n_rows = len(row_sums)
            if n_rows >= 2:
                row_eq_vars = []
                for i in range(n_rows):
                    for j in range(i + 1, n_rows):
                        eq = model.NewBoolVar(f"row_eq_{i}_{j}")
                        model.Add(row_sums[i] == row_sums[j]).OnlyEnforceIf(eq)
                        model.Add(row_sums[i] != row_sums[j]).OnlyEnforceIf(eq.Not())
                        row_eq_vars.append(eq)
                # 使用开关变量 s1 控制行约束
                model.Add(sum(row_eq_vars) == 1).OnlyEnforceIf(s1)

            # ---------- 计算每列雷数 ----------
            col_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_row_pos(pos))
                for pos in col_positions
            ]

            # 列约束：恰好有一对列雷数相等
            n_cols = len(col_sums)
            if n_cols >= 2:
                col_eq_vars = []
                for i in range(n_cols):
                    for j in range(i + 1, n_cols):
                        eq = model.NewBoolVar(f"col_eq_{i}_{j}")
                        model.Add(col_sums[i] == col_sums[j]).OnlyEnforceIf(eq)
                        model.Add(col_sums[i] != col_sums[j]).OnlyEnforceIf(eq.Not())
                        col_eq_vars.append(eq)
                # 使用开关变量 s2 控制列约束
                model.Add(sum(col_eq_vars) == 1).OnlyEnforceIf(s2)

    def suggest_total(self, info: dict):
        """
        建议总雷数范围。根据纯CP模型测试，4x4可行总雷数为5，5x5可行总雷数为9。
        """
        def add_constraints(model, total_var):
            for interactive in info["interactive"]:
                size = info["size"][interactive]
                rows, cols = size
                # 根据尺寸指定已知可行的总雷数
                if rows == 4 and cols == 4:
                    model.Add(total_var == 5)
                elif rows == 5 and cols == 5:
                    model.Add(total_var == 9)
                else:
                    # 通用范围：至少2，不超过总格子数的一半加2
                    model.Add(total_var >= 2)
                    model.Add(total_var <= (rows * cols) // 2 + 2)

        info["hard_fns"].append(add_constraints)

    def init_board(self, board: Board) -> bool:
        """初始化题板时无需特殊操作。"""
        return True

    def init_clear(self, board: Board) -> None:
        """清除阶段无需特殊操作。"""
        pass

    def combine(self, other) -> Optional['UD']:
        """不支持规则合并。"""
        return None

    def get_deps(self) -> list[str]:
        """无依赖。"""
        return []
