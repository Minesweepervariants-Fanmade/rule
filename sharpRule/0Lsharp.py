from typing import List, Tuple, Optional

from ....abs.Rrule import AbstractClueRule
from ....abs.board import AbstractBoard
from ....abs.rule import AbstractRule
from ....utils.tool import get_random, get_logger
from ...impl_obj import get_rule
from ....utils.impl_obj import VALUE_QUESS

from . import AbstractClueSharp

class Rule0LSharp(AbstractClueSharp):
    name = ["0L#", "标签", "Tag"]
    doc = "包含以下规则: [1L], [1L1L], [1L1N], [1L1X], [1L1P], [1L1X'], [1L1K], [1L1W'], [1L1E'], [1L2D], [1L2M], [1L2X']。线索值只有零。"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        rules_name = ["1L", "1L1L", "1L1N", "1L1X", "1L1P", "1L1X'", "1L1K", "1L1W'", "1L1E'", "1L2D", "1L2M", "1L2X'"]
        super().__init__(rules_name, board, data)
        self.rules = data

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        boards : list[AbstractBoard] = []
        random = get_random()
        for rule in self.shape_rule.rules:
            boards.append(rule.fill(board.clone()))
        for key in board.get_board_keys():
            for pos, _ in board("N", key=key):
                values = [_board.get_value(pos) for _board in boards if _board.get_value(pos).__repr__() == '0']
                if not values:
                    board.set_value(pos, VALUE_QUESS)
                else:
                    board.set_value(pos, random.choice(values))
        return board
