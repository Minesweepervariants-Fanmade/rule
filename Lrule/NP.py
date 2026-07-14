"""
[NP] 负点 (Negative Point)：雷带有正负号，由行列雷数决定。
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel
from minesweepervariants.utils.tool import get_logger

logger = get_logger()


class RuleNP(AbstractMinesRule):
    id = "NP"
    aliases = ()
    name = "Negative Point"
    name.zh_CN = "负点"
    doc = "雷带有正负号，该雷所在的行与列中，雷多则为正号，非雷多则为负号。"
    doc.zh_CN = "雷带有正负号，该雷所在的行与列中，雷多则为正号，非雷多则为负号。"
    tags = ["Variant", "Mine-Value", "Global", "Local"]
    creation_time = "2026-07-14"
    lib_only = True
    author = ("740652480", 740652480)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        """注册一个特殊类型函数，用于获取带有符号的雷值。"""
        def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
            # 直接使用 pos 自带的键（主键）获取原始类型，不使用 special
            # 检查该位置是否为雷
            if board.get_type(pos) == 'F':
                # 使用 pos 的键作为键
                key = pos.board_key
                # 计算该雷所在行和列的雷数
                boundary_pos = board.boundary(key)
                if boundary_pos.row < 0 or boundary_pos.col < 0:
                    return 0
                width = boundary_pos.col + 1
                height = boundary_pos.row + 1

                row_mines = 0
                col_mines = 0
                r, c = pos.row, pos.col

                # 统计该行的雷数
                for col_idx in range(width):
                    p = Position(col_idx, r, key)
                    if board.get_type(p) == 'F':
                        row_mines += 1

                # 统计该列的雷数
                for row_idx in range(height):
                    p = Position(c, row_idx, key)
                    if board.get_type(p) == 'F':
                        col_mines += 1

                # 行列中雷的总数（去掉自身重复）
                total_mines = row_mines + col_mines - 1
                total_cells = width + height - 1
                total_non_mines = total_cells - total_mines

                # 决定符号：雷多则正，非雷多则负
                if total_mines > total_non_mines:
                    return 1   # 正号
                elif total_mines < total_non_mines:
                    return -1  # 负号
                else:
                    return 1   # 平局时按正号处理
            return 0

        board.register_type_special('NP', get_type)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        此规则不直接添加约束，符号在获取雷值时动态计算。
        """
        pass
