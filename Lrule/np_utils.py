"""
NP' 规则的工具函数，用于注册命名空间
"""
from minesweepervariants.board import Board, Position


def get_np_prime_type(board: 'Board', pos: 'Position', *args, **kwargs):
    """计算 NP' 雷值：
    如果位置是雷：
        - 行雷数 == 列雷数 => 1
        - 行雷数 != 列雷数 => -1
    如果不是雷：0
    """
    # 检查是否为雷
    if board.get_type(pos, special='raw') != 'F':
        return 0

    # 计算行和列的雷数（纯数量，不考虑雷值）
    N = board.boundary().row + 1
    row_count = sum(1 for c in range(N) if board.get_type(Position(c, pos.row, pos.board_key), special='raw') == 'F')
    col_count = sum(1 for r in range(N) if board.get_type(Position(pos.col, r, pos.board_key), special='raw') == 'F')

    # 行雷数 == 列雷数 则雷值为 1，否则为 -1
    return 1 if row_count == col_count else -1


def register_np_prime_type(board: 'Board'):
    """注册 NP' 命名空间"""
    board.register_type_special("NP'", get_np_prime_type)
