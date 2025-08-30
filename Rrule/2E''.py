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
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD

ALPHABET = "ABCDEFGHI"
NAME_2Epp = "2E''"


class Rule2Ep(AbstractClueRule):
    name = ["2E''", "互指"]
    doc = "如果线索X周围有N个雷 则另一个题板的X=N的格子必定为雷"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__()
        size = (board.boundary().x + 1, board.boundary().y + 1)
        board.set_config(MASTER_BOARD, "pos_label", True)
        board.generate_board(NAME_2Epp, size)
        board.set_config(NAME_2Epp, "pos_label", True)
        board.set_config(NAME_2Epp, "interactive", True)
        board.set_config(NAME_2Epp, "row_col", True)
        board.set_config(NAME_2Epp, "VALUE", VALUE_QUESS)
        board.set_config(NAME_2Epp, "MINES", MINES_TAG)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        logger = get_logger()
        for (key_a, key_b) in [
            (MASTER_BOARD, NAME_2Epp),
            (NAME_2Epp, MASTER_BOARD)
        ]:
            letter_map = {i: [] for i in range(9)}
            for pos, _ in board("F", key=key_a):
                if pos.y > 8:
                    continue
                letter = ALPHABET[pos.y]
                if pos.x not in letter_map:
                    letter_map[pos.x] = []
                letter_map[pos.x].append(letter)

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
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]    # 实际为第几列的字母
        self.neighbors = pos.neighbors(2)
        self.pos = pos

    def __repr__(self) -> str:
        return f"{ALPHABET[self.value]}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule2Ep.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        if self.pos.board_key == MASTER_BOARD:
            board_key = NAME_2Epp
        else:
            board_key = MASTER_BOARD
        pos = board.get_pos(0, self.value, board_key)
        line = board.get_col_pos(pos)
        # print(self.pos, self, pos)
        # print(self.neighbors)
        line = board.batch(line, mode="variable")
        sum_vers = sum(board.batch(self.neighbors, mode="variable", drop_none=True))
        for index in range(min(9, len(line))):
            var = line[index]
            model.Add(sum_vers != index).OnlyEnforceIf(var.Not()).OnlyEnforceIf(s)
            get_logger().trace(f"[2E'']: {self.pos} != {index} if {var} is 0")
