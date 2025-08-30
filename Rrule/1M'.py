#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/10 18:09
# @Author  : Wu_RH
# @FileName: 1M.py
"""
[1M']多雷': 每个线索的多雷位置相对于线索固定 且位置全盘共享(总雷数不受限制)
"""

from ....abs.board import AbstractBoard, AbstractPosition
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_random
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS

BOARD_NAME = "1M'"


class Rule1M(AbstractClueRule):
    name = ["1M'", "多雷'"]
    doc = "每个线索的多雷位置相对于线索固定 且位置全盘共享(总雷数不受限制)"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        board.generate_board(BOARD_NAME, (3, 3))
        if data is None:
            self.value = 4
        else:
            self.value = data

    def fill(self, board: 'AbstractBoard'):
        def apply_offsets(_pos: AbstractPosition):
            nonlocal offsets
            result = []
            for dpos in offsets:
                result.append(_pos.deviation(dpos))
            return result
        random = get_random()
        pos = board.get_pos(1, 1, BOARD_NAME)

        if self.value is None:
            board[pos] = Value2I_7(pos, bytes([4]))
        elif self.value == "":
            board[pos] = Value2I_7(pos, bytes([9]))
        else:
            board[pos] = Value2I_7(pos, bytes([int(self.value)]))

        pos_list = [pos for pos, _ in board("N", key=BOARD_NAME)]

        if self.value == "":
            pos_list = random.sample(pos_list, int(random.random() * 9))
        else:
            pos_list = random.sample(pos_list, int(self.value))
        offsets = []
        for pos in pos_list:
            board[pos] = VALUE_CIRCLE
            offsets.append(pos.up().left())
        for pos, _ in board("N", key=BOARD_NAME):
            board[pos] = VALUE_CROSS

        for pos, _ in board("N"):
            positions = pos.neighbors(2)
            offset_poses = apply_offsets(pos)
            value = board.batch(positions, mode="type").count("F")
            value += board.batch(offset_poses, mode="type").count("F")
            obj = Value1M(pos, code=bytes([value]))
            board.set_value(pos, obj)
        return board

    def init_clear(self, board: 'AbstractBoard'):
        for pos, obj in board(mode="object", key=BOARD_NAME):
            if isinstance(obj, Value2I_7):
                continue
            board[pos] = None


class Value1M(AbstractClueValue):
    value: int
    neighbors: list

    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = self.neighbors[:]
        neighbors = []
        for pos2, obj in board(key=BOARD_NAME):
            if isinstance(obj, Value2I_7):
                continue
            neighbors.append([self.pos.deviation(pos2).up().left(), pos2])
        for pos, pos2 in neighbors:
            if board.get_type(pos) == "F":
                positions.append(pos2)
        return positions

    @classmethod
    def type(cls) -> bytes:
        return Rule1M.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        var_list = board.batch(self.neighbors, mode="variable", drop_none=True)

        # 初始化对照表
        neighbors = []
        for pos2, obj in board(key=BOARD_NAME):
            if isinstance(obj, Value2I_7):
                continue
            # 题板上的位置和共享的偏移位置
            _positions = [self.pos.deviation(pos2).up().left(), pos2]
            # 第一个为题板对应的变量 第二个为偏移的变量
            neighbors.append(board.batch(_positions, mode="variable"))

        # 初始化和值
        for var_to_sum, cond in neighbors:
            if var_to_sum is None or cond is None:
                continue
            # 初始化临时变量
            tmp = model.NewBoolVar(f"included_if_{self.pos}_{var_to_sum}")
            # 如果偏移变量为真 那么tmp为题板的值
            model.Add(tmp == var_to_sum).OnlyEnforceIf([cond, s])
            # 如果偏移变量为假 那么tmp为0
            model.Add(tmp == 0).OnlyEnforceIf([cond.Not(), s])
            var_list.append(tmp)

        model.Add(sum(var_list) == self.value).OnlyEnforceIf(s)


class Value2I_7(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.neighbors = pos.neighbors(2)
        self.value = code[0]

    def __repr__(self) -> str:
        return str(self.value) if self.value < 9 else "?"

    @classmethod
    def type(cls) -> bytes:
        return Rule1M.name[0].encode("ascii") + b"_n"

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        if self.value > 8:
            return
        model = board.get_model()
        s = switch.get(model, self)
        model.Add(sum(board.batch(self.neighbors, mode="variable")) == self.value).OnlyEnforceIf(s)
