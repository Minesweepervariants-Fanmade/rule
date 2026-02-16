from typing import Dict, List
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.board.version3 import Board
from . import AbstractClueSharp, ClueSharp
from minesweepervariants.impl.summon.solver import Switch
from ....utils.tool import get_random, get_logger
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from ....impl.impl_obj import get_rule
from ....utils.image_create import get_text, get_image, get_dummy, get_col
from ....utils.web_template import Number
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

right_rules = [
    "V", "1L", "2M", "1W'", "1X'",
    "2I", "1M", "1K", "2X", "2E'-",
    "2P", "1E", "V", "1E'", "2A",
    "3S", "2X'", "1X", "1N", "2E^",
    "2E", "1W", "2D", "1P", "4Q"
]

class RuleHorseYear(AbstractClueSharp):
    name = ["HY", "马年"]

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(rules=right_rules, board=board, data=data)
        self.shape_rule.rules[12] = ClueSharp(board=board, data=[
            board.get_rule_instance("1M1N"),
            board.get_rule_instance("1M1X"),
            board.get_rule_instance("1N1X"),
            board.get_rule_instance("1L1M"),
            board.get_rule_instance("1X2X"),
        ])
        labels = {}
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for pos in board.get_pos_box(board.get_pos(9, 4 * 9), board.get_pos(9 * 2 - 1, 5 * 9 - 1)):
            labels[pos] = alphabet[pos.y - 4 * 9] + "=" + str(pos.x - 9)
        board.set_config("1", "labels", labels)
        for pos, _ in board():
            if (
                (pos.x >= 8 and pos.x <= 18 and pos.y >= 8 and pos.y <= 18) or
                (pos.x >= 26 and pos.x <= 36 and pos.y >= 8 and pos.y <= 18) or
                (pos.x >= 8 and pos.x <= 18 and pos.y >= 26 and pos.y <= 36) or
                (pos.x >= 26 and pos.x <= 36 and pos.y >= 26 and pos.y <= 36) or
                (pos.x >= 16 and pos.x <= 27 and pos.y >= 16 and pos.y <= 27)
            ):
                if ((pos.x + pos.y) % 2 == 1):
                    board.set_dyed(pos, True)
        # board.set_config("1", "by_mini", False)
        # board.set_config("mimi_area", ())

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        boards = []
        for rule in self.shape_rule.rules:
            boards.append(rule.fill(board.clone()))
        letter_map = {i: [] for i in range(9)}
        for key in board.get_board_keys(): 
            for pos, _ in board("N", key=key):
                index = pos.x // 9 * 5 + pos.y // 9
                _board = boards[index]
                if (index == 9):
                    positions = pos.neighbors(2)
                    value = board.batch(positions, mode="type", drop_none=True).count("F")
                    letter_scan = board.batch(
                        board.get_pos_box(board.get_pos(value + 9, 4 * 9), board.get_pos(value + 9, 5 * 9 - 1)),
                        mode="object"
                    )
                    possible_letters = []
                    for i, obj in enumerate(letter_scan):
                        if obj == MINES_TAG:
                            possible_letters.append(i)
                    if not possible_letters:
                        board.set_value(pos, VALUE_QUESS)
                    else:
                        letter_index = get_random().choice(possible_letters)
                        board.set_value(pos, Value2EpOffset(pos, bytes([letter_index])))
                else:
                    board.set_value(pos, _board.get_value(pos))
        return board
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        b = switch.get(model, self)
        for pos, var in board(mode="variable"):
            pos_list = [
                pos.left(2).up(1),
                pos.left(2).down(1),
                pos.down(2).left(1),
                pos.down(2).right(1)
            ]
            var_list = board.batch(pos_list, mode="variable", drop_none=True)
            for _var in var_list:
                model.AddBoolOr([_var.Not(), var.Not()]).OnlyEnforceIf(b)

    def distinct(self, pos: AbstractPosition) -> tuple[int, int]:
        return (pos.x // 9, pos.y // 9)

def alpha(n: int) -> str:
    alpha_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if n < 26:
        return alpha_map[n]
    return alpha_map[n // 26 - 1] + alpha_map[n % 26]

class Value2EpOffset(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]  # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{alpha(self.value)}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return "2E'".encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        pos = board.get_pos(0, self.value)
        line = board.get_col_pos(pos)
        line = board.batch(line, mode="variable")
        sum_vers = sum(board.batch(self.neighbors, mode="variable", drop_none=True))
        for index in range(min(9, len(line))):
            var = board.get_variable(board.get_pos(index + 9, self.value + 4 * 9))
            model.Add(sum_vers != index).OnlyEnforceIf(var.Not()).OnlyEnforceIf(s)
    