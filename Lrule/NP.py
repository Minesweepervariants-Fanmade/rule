"""
[NP] 负点 (Negative Point)：雷带有正负号，该雷所在的行与列中，雷多则该雷的雷值为1，非雷多则该雷的雷值为-1。
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel


class RuleNP(AbstractMinesRule):
    id = "NP"
    aliases = ()
    name = "Negative Point"
    name.zh_CN = "负点"
    doc = "Mine value is 1 if there are more mines than non-mines in its row and column, otherwise -1"
    doc.zh_CN = "雷带有正负号，该雷所在的行与列中，雷多则该雷的雷值为1，非雷多则该雷的雷值为-1"
    tags = ["Variant", "Mine-Value", "Global"]
    creation_time = "2026-07-14"
    lib_only = True
    author = ("", 740652480)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'Board'):
        def get_np_type(board: 'Board', pos: 'Position', *args, **kwargs):
            # 检查是否为雷
            if board.get_type(pos, special='raw') != 'F':
                return 0
            # 计算行和列的雷数
            N = board.boundary().row + 1
            row_count = sum(1 for c in range(N) if board.get_type(Position(c, pos.row, pos.board_key), special='raw') == 'F')
            col_count = sum(1 for r in range(N) if board.get_type(Position(pos.col, r, pos.board_key), special='raw') == 'F')
            total_mines = row_count + col_count - 1  # 减去自身重复
            total_cells = 2 * N - 1
            return 1 if 2 * total_mines > total_cells else -1
        board.register_type_special('NP', get_np_type)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        # 获取题板尺寸（假设为正方形）
        boundary = board.boundary()
        N = boundary.row + 1  # 行数（也是列数）
        T = 2 * N - 1  # 行和列的总格子数

        # 遍历所有交互键（通常是'raw'）
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")

                # 获取该位置所在行的所有位置
                row_positions = [Position(pos.col, r, pos.board_key) for r in range(N)]
                # 获取所在列的所有位置
                col_positions = [Position(c, pos.row, pos.board_key) for c in range(N)]

                # 计算行和列中雷的总数（包括自身，但自身被重复计算，所以需要减去一次）
                R = (sum(board.get_variable(p, special="raw") for p in row_positions) +
                     sum(board.get_variable(p, special="raw") for p in col_positions) -
                     mine)

                # 创建布尔变量 gt，表示 2*R > T
                gt = model.NewBoolVar(f'gt_{pos}')
                model.Add(2 * R > T).OnlyEnforceIf(gt)
                model.Add(2 * R <= T).OnlyEnforceIf(gt.Not())

                # 获取 NP 雷值变量
                np_val = board.get_variable(pos, special='NP')

                # 如果该位置是雷，则根据 gt 设置 np_val 为 1 或 -1
                model.Add(np_val == 1).OnlyEnforceIf([mine, gt])
                model.Add(np_val == -1).OnlyEnforceIf([mine, gt.Not()])
                # 如果该位置不是雷，则 np_val 为 0
                model.Add(np_val == 0).OnlyEnforceIf(mine.Not())

    def get_deps(self) -> list[str]:
        # NP 不依赖其他规则
        return []
