#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/11 16:38
# @Author  : Wu_RH
# @FileName: 2E'.py
"""
[2E'']互指: 如果线索X周围有N个雷 则另一个题板的X=N的格子必定为雷
"""
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG
from ....utils.tool import get_random, get_logger

from ....abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.board import Board, Position, MASTER_BOARD_KEY, Size

ALPHABET = "ABCDEFGHI"
NAME_2Epp = "2E''"


class Rule2Ep(AbstractClueRule):
    id = "2E''"
    name = "Mutual Indication"
    name.zh_CN = "互指"
    doc = "If clue X has N mines around it, then the cell with X=N on the other board must be a mine"
    doc.zh_CN = "如果线索X周围有N个雷 则另一个题板的X=N的格子必定为雷"

    tags = ["Variant", "Local", "Number Clue", "Aux Board", "Extensive Trial"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: Board, data=None):
        super().__init__()
        size = Size(board.boundary().row + 1, board.boundary().col + 1)
        board.set_config(MASTER_BOARD_KEY, "pos_label", True)
        board.generate_board(NAME_2Epp, size)
        board.set_config(NAME_2Epp, "pos_label", True)
        board.set_config(NAME_2Epp, "interactive", True)
        board.set_config(NAME_2Epp, "row_col", True)
        board.set_config(NAME_2Epp, "VALUE", VALUE_QUESS)
        board.set_config(NAME_2Epp, "MINES", MINES_TAG)

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()
        logger = get_logger()
        for (key_a, key_b) in [
            (MASTER_BOARD_KEY, NAME_2Epp),
            (NAME_2Epp, MASTER_BOARD_KEY)
        ]:
            letter_map = {i: [] for i in range(9)}
            for pos, _ in board("F", key=key_a):
                if pos.col > 8:
                    continue
                letter = ALPHABET[pos.col]
                if pos.row not in letter_map:
                    letter_map[pos.row] = []
                letter_map[pos.row].append(letter)

            for pos, _ in board("N", key=key_b):
                positions = pos.neighbors(2)
                value = board.batch(positions, mode="type").count("F")
                if not letter_map[value]:
                    board.set_value(pos, VALUE_QUESS)
                    continue
                letter = random.choice(letter_map[value])
                obj = Value2Ep(pos, bytes([ALPHABET.index(letter)]))
                board.set_value(pos, obj)
                logger.debug(f"[2E''] put {letter}({value}) at {pos}")
        return board


class Value2Ep(AbstractClueValue):
    id = "2Ep"
    def __init__(self, pos: 'Position', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]    # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)
        self.pos = pos

    def __repr__(self) -> str:
        return f"{ALPHABET[self.value]}"

    def high_light(self, board: 'Board') -> list['Position']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule2Ep.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        if self.pos.board_key == MASTER_BOARD_KEY:
            board_key = NAME_2Epp
        else:
            board_key = MASTER_BOARD_KEY
        pos = board.get_pos(0, self.value, board_key)
        line = board.get_col_pos(pos)
        # print(self.pos, self, pos)
        # print(self.neighbors)
        line = board.batch(line, mode="variable")
        sum_vers = sum(board.batch(self.neighbors, mode="variable", drop_none=True))
        model.Add(sum_vers < len(line)).OnlyEnforceIf(s)
        for index in range(min(9, len(line))):
            var = line[index]
            model.Add(sum_vers != index).OnlyEnforceIf(var.Not(), s)
            get_logger().trace(f"[2E'']: {self.pos} != {index} if {var} is 0")
