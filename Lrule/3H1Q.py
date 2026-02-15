"""
[3H1Q]六角无方: 每个互相相邻的三个格必有一个雷
"""

from typing import List, Tuple

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractPosition, AbstractBoard


def get_hex_neighbors(pos: AbstractPosition, board: AbstractBoard) -> List[AbstractPosition]:
    x, y = pos.x, pos.y
    board_key = pos.board_key
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # 上下左右
    if y % 2 == 1:
        directions += [(-1, -1), (-1, 1)]  # 奇数列 左上右上
    else:
        directions += [(1, -1), (1, 1)]    # 偶数列 左下右下
    neighbors = []
    for dx, dy in directions:
        npos = type(pos)(x + dx, y + dy, board_key)
        if board.in_bounds(npos):
            neighbors.append(npos)
    return neighbors


def is_hex_adjacent(a: AbstractPosition, b: AbstractPosition, board: AbstractBoard) -> bool:
    for npos in get_hex_neighbors(a, board):
        if npos == b:
            return True
    return False


def triad_key(positions: List[AbstractPosition]) -> Tuple[Tuple[int, int, str], ...]:
    return tuple(sorted((p.x, p.y, p.board_key) for p in positions))


class Rule3H1Q(AbstractMinesRule):
    name = ["3H1Q", "Hex1Q", "六角无方"]
    doc = "六角无方: 每个互相相邻的三个格必有一个雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        for key in board.get_board_keys():
            board.set_config(key, "grid_type", "hex")

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        triads = set()

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            for col_pos in board.get_col_pos(boundary):
                for pos in board.get_row_pos(col_pos):
                    neighbors = get_hex_neighbors(pos, board)
                    if len(neighbors) < 2:
                        continue

                    for i in range(len(neighbors)):
                        for j in range(i + 1, len(neighbors)):
                            n1 = neighbors[i]
                            n2 = neighbors[j]
                            if not is_hex_adjacent(n1, n2, board):
                                continue
                            triads.add(triad_key([pos, n1, n2]))

        for triad in triads:
            positions = [board.get_pos(x, y, key) for x, y, key in triad]
            var_list = [board.get_variable(p) for p in positions]
            model.AddBoolOr(var_list).OnlyEnforceIf(s)
