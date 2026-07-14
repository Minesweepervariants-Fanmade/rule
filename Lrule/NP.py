"""
[NP] 负点 (Negative Point)

雷带有正负号，该雷所在的行与列中，雷多则该雷的雷值为 1，非雷多则该雷的雷值为 -1。
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
    lib_only = False
    author = ("740652480", 740652480)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        """注册 type_special 用于显示符号。"""

        def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
            if board.get_type(pos) != 'F':
                return 0

            key = pos.board_key
            boundary = board.boundary(key)
            if boundary.row < 0 or boundary.col < 0:
                return 0
            width = boundary.col + 1
            height = boundary.row + 1

            r, c = pos.row, pos.col
            row_mines = 0
            col_mines = 0

            for col_idx in range(width):
                if board.get_type(Position(col_idx, r, key)) == 'F':
                    row_mines += 1
            for row_idx in range(height):
                if board.get_type(Position(c, row_idx, key)) == 'F':
                    col_mines += 1

            total_mines = row_mines + col_mines - 1
            total_cells = width + height - 1
            total_non_mines = total_cells - total_mines

            if total_mines > total_non_mines:
                return 1
            elif total_mines < total_non_mines:
                return -1
            else:
                return 1

        board.register_type_special('NP', get_type)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        添加 NP 规则的核心约束：
        对每个位置，若为雷，其带符号雷值 det 由行列雷数决定：
            det = 1  当且仅当 2*(row_mines + col_mines) - width - height >= 0
            det = -1 当且仅当 2*(row_mines + col_mines) - width - height < 0
        若非雷，则 det = 0。
        """
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            if boundary.row < 0 or boundary.col < 0:
                continue
            width = boundary.col + 1
            height = boundary.row + 1

            # ---- 创建行雷数变量 ----
            row_mines = {}
            for r in range(height):
                row_mines[r] = model.NewIntVar(0, width, f'NP_row_mines_{key}_{r}')
                model.Add(
                    row_mines[r] == sum(
                        board.get_variable(Position(c, r, key), special="raw")
                        for c in range(width)
                    )
                ).OnlyEnforceIf(s)

            # ---- 创建列雷数变量 ----
            col_mines = {}
            for c in range(width):
                col_mines[c] = model.NewIntVar(0, height, f'NP_col_mines_{key}_{c}')
                model.Add(
                    col_mines[c] == sum(
                        board.get_variable(Position(c, r, key), special="raw")
                        for r in range(height)
                    )
                ).OnlyEnforceIf(s)

            # ---- 对每个位置添加符号约束 ----
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                
                # 创建带符号的雷值变量 det，值为 -1, 0, 1
                det = model.NewIntVar(-1, 1, f'NP_det_{key}_{pos}')
                # 注册为特殊变量，以便后续可以通过 get_variable 获取
                board.register_variable_special('NP', pos, det)

                # diff = 2*(row_mines + col_mines) - width - height
                diff = 2 * (row_mines[pos.row] + col_mines[pos.col]) - width - height

                # b = 1 当且仅当 diff >= 0
                b = model.NewBoolVar(f'NP_b_{key}_{pos}')
                model.Add(diff >= 0).OnlyEnforceIf(b)
                model.Add(diff <= -1).OnlyEnforceIf(b.Not())

                # det = 2*b - 1 当且仅当该位置是雷
                model.Add(det == 2 * b - 1).OnlyEnforceIf(mine)
                model.Add(det == 0).OnlyEnforceIf(mine.Not())
