"""
[NP'] 负标 (Negative Prime)：雷带有正负号，该雷所在的行与列中，
若行雷数 ≠ 列雷数（纯数量，不考虑雷值），则该雷的雷值为 -1；
若行雷数 = 列雷数，则该雷的雷值为 1。
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel
from .np_utils import register_np_prime_type


class RuleNP_(AbstractMinesRule):
    id = "NP'"
    aliases = ("NP_",)
    name = "Negative Prime"
    name.zh_CN = "负标"
    doc = "Mine value is 1 if row mine count equals column mine count, otherwise -1"
    doc.zh_CN = "雷带有正负号，该雷所在的行与列中，若行雷数=列雷数，则雷值为1，否则为-1"
    tags = ["Variant", "Mine-Value", "Global"]
    creation_time = "2026-08-04"
    lib_only = False  # 不依赖 lib_only 机制，直接依赖 V_NP
    author = ("", 740652480)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        # 固定使用 NP' 命名空间
        self.rule = "NP'"
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        """注册 NP' 类型特殊函数，用于计算该位置的雷值（显示用）"""
        register_np_prime_type(board)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """创建 CP-SAT 约束：
        对于每个位置，如果是雷：
            - 行雷数 == 列雷数 => 雷值 = 1
            - 行雷数 != 列雷数 => 雷值 = -1
        如果不是雷：雷值 = 0
        """
        model = board.get_model()
        # 获取题板尺寸（假设为正方形，行数和列数相同）
        boundary = board.boundary()
        N = boundary.row + 1  # 行数（也是列数）

        # 遍历所有交互键（通常是 'raw'）
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")

                # 获取该位置所在行的所有位置
                row_positions = [Position(c, pos.row, pos.board_key) for c in range(N)]
                # 获取所在列的所有位置
                col_positions = [Position(pos.col, r, pos.board_key) for r in range(N)]

                # 计算行雷数（纯数量）
                R_row = sum(board.get_variable(p, special="raw") for p in row_positions)
                # 计算列雷数（纯数量）
                R_col = sum(board.get_variable(p, special="raw") for p in col_positions)

                # 创建布尔变量 eq，表示 R_row == R_col
                eq = model.NewBoolVar(f'eq_{pos}')
                model.Add(R_row == R_col).OnlyEnforceIf(eq)
                model.Add(R_row != R_col).OnlyEnforceIf(eq.Not())

                # 获取 NP' 雷值变量
                np_prime_val = board.get_variable(pos, special="NP'")

                # 如果该位置是雷且行雷数 == 列雷数，雷值为 1
                model.Add(np_prime_val == 1).OnlyEnforceIf([mine, eq])
                # 如果该位置是雷且行雷数 != 列雷数，雷值为 -1
                model.Add(np_prime_val == -1).OnlyEnforceIf([mine, eq.Not()])
                # 如果该位置不是雷，雷值为 0
                model.Add(np_prime_val == 0).OnlyEnforceIf(mine.Not())

    def get_deps(self) -> list[str]:
        """NP' 直接依赖 V_NP 规则，不依赖 raw"""
        return ["V_NP"]

    # 不需要 companion_id，因为 lib_only=False
