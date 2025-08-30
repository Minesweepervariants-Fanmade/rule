#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/03 11:37
# @Author  : Wu_RH
# @FileName: 2I.py
"""
[2I]残缺：数字表示周围8格中某7格的雷数。7格的方位被当前题板所有线索共享
"""

from ....abs.Rrule import AbstractClueValue, AbstractClueRule
from ....abs.board import AbstractPosition, AbstractBoard
from ....utils.impl_obj import VALUE_CROSS, VALUE_CIRCLE
from ....utils.tool import get_random, get_logger

NAME_2I = "2I"


class Rule2I(AbstractClueRule):
    name = ["2I", "残缺"]
    doc = "数字表示周围8格中某7格的雷数。7格的方位被当前题板所有线索共享"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        board.generate_board(NAME_2I, (3, 3))

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        def apply_offsets(_pos: AbstractPosition):
            nonlocal offsets
            result = []
            for dpos in offsets:
                result.append(_pos.deviation(dpos))
            return result

        random = get_random()
        logger = get_logger()
        pos = board.get_pos(1, 1, NAME_2I)
        board[pos] = Value2I_7(pos)

        pos_list = [pos for pos, _ in board("N", key=NAME_2I)]
        pos_list = random.sample(pos_list, 7)
        offsets = []
        for pos in pos_list:
            board[pos] = VALUE_CIRCLE
            offsets.append(pos.up().left())
            logger.debug(f"[2I] put O at {pos}")
        for pos, _ in board("N", key=NAME_2I):
            board[pos] = VALUE_CROSS
            logger.debug(f"[2I] put X at {pos}")

        for pos, _ in board("N"):
            positions = apply_offsets(pos)
            value = board.batch(positions, mode="type", drop_none=True).count("F")
            obj = Value2I(pos, bytes([value]))
            board.set_value(pos, obj)
            logger.debug(f"[2I] put ({value}) at {pos}")

        return board

    def init_clear(self, board: 'AbstractBoard'):
        for pos, obj in board(mode="object", key=NAME_2I):
            if isinstance(obj, Value2I_7):
                continue
            board[pos] = None


class Value2I(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.pos = pos
        self.value = code[0]

    def __repr__(self):
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = []
        for pos, _ in board("NF", key=NAME_2I):
            _pos = self.pos.deviation(pos.shift(1, -1))
            if board.in_bounds(_pos):
                positions.append(_pos)
        return positions

    @classmethod
    def method_choose(cls) -> int:
        return 1

    @classmethod
    def type(cls) -> bytes:
        return Rule2I.name[0].encode("ascii")

    def code(self):
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 初始化对照表
        neighbors = []
        for pos2, obj in board(key=NAME_2I):
            if isinstance(obj, Value2I_7):
                continue
            # 题板上的位置和共享的偏移位置
            _positions = [self.pos.deviation(pos2).up().left(), pos2]
            # 第一个为题板对应的变量 第二个为偏移的变量
            neighbors.append(board.batch(_positions, mode="variable"))

        # 初始化和值
        sum_vers = []
        for var_to_sum, cond in neighbors:
            if var_to_sum is None or cond is None:
                continue
            # 初始化临时变量
            tmp = model.NewBoolVar(f"included_if_{self.pos}_{var_to_sum}")
            # 如果偏移变量为真 那么tmp为题板的值
            model.Add(tmp == var_to_sum).OnlyEnforceIf([cond, s])
            # 如果偏移变量为假 那么tmp为0
            model.Add(tmp == 0).OnlyEnforceIf([cond.Not(), s])
            sum_vers.append(tmp)
            logger.trace(f"[2E'2I] new tempVar: {tmp} = if {cond} -> {var_to_sum}")

        model.Add(sum(sum_vers) == self.value).OnlyEnforceIf(s)


class Value2I_7(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return "7"

    @classmethod
    def method_choose(cls) -> int:
        return 1

    @classmethod
    def type(cls) -> bytes:
        return Rule2I.name[0].encode("ascii") + b"_7"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        model.Add(sum(board.batch(self.neighbors, mode="variable")) == 7).OnlyEnforceIf(s)
