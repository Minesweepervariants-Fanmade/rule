#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/20 23:00
# @Author  : Wu_RH
# @FileName: 3B.py
"""
[3B]二进(Binary):无雷是0，有雷是1，线索代表每行（左起）和每列（上起）对应两个二进制数的按位异或值
"""
from typing import List

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.tool import get_logger


def encode_bools_7bit(bools: list[bool]) -> bytes:
    # 编码头部：原始长度（用 4 字节 big-endian 表示）
    original_len = len(bools)
    length_bytes = [
        (original_len >> 24) & 0xFF,
        (original_len >> 16) & 0xFF,
        (original_len >> 8) & 0xFF,
        original_len & 0xFF
    ]

    # 编码主体：每 7 位布尔值 -> 1 字节（bit6~bit0，bit7固定为0）
    payload = []
    i = 0
    while i < len(bools):
        byte = 0
        for j in range(7):
            if i + j < len(bools) and bools[i + j]:
                byte |= 1 << (6 - j)
        payload.append(byte)  # bit7 默认为0
        i += 7

    return bytes(length_bytes + payload)


def decode_bools_7bit(data: bytes) -> list[bool]:
    if len(data) < 4:
        raise ValueError("数据不足4字节")

    # 解码头部长度信息（4字节 big-endian）
    original_len = (
            (data[0] << 24) |
            (data[1] << 16) |
            (data[2] << 8) |
            data[3]
    )

    # 解码主体数据
    bools = []
    for byte in data[4:]:
        for shift in range(6, -1, -1):
            bit = (byte >> shift) & 1
            bools.append(bool(bit))
            if len(bools) == original_len:
                return bools
    return bools[:original_len]  # 万一补了太多 false


class Rule3B(AbstractClueRule):
    name = ["3B", "二进", "Binary"]
    doc = "无雷是0，有雷是1，线索代表每行（左起）和每列（上起）对应两个二进制数的按位异或值"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            col = board.get_col_pos(pos)
            row = board.get_row_pos(pos)
            col = ["N" if i == "C" else i for i in board.batch(col, mode="type")]
            row = ["N" if i == "C" else i for i in board.batch(row, mode="type")]
            bools = [col[index] != row[index] for index in range(len(col))]
            obj = Value3B(pos, encode_bools_7bit(bools))
            board.set_value(pos, obj)
            logger.debug(f"Set {pos} [3B]{obj}")
        return board


class Value3B(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.bools = decode_bools_7bit(code)
        self.__code = code

    def __repr__(self) -> str:
        result = 0
        for b in self.bools:
            result = (result << 1) | int(b)
        return f"{result}"

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition']:
        return board.get_row_pos(self.pos) + board.get_col_pos(self.pos)

    @classmethod
    def type(cls) -> bytes:
        return Rule3B.name[0].encode("ascii")

    def code(self) -> bytes:
        return self.__code

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        col = board.get_col_pos(self.pos)
        row = board.get_row_pos(self.pos)
        col = board.batch(col, mode="variable")
        row = board.batch(row, mode="variable")
        for index in range(len(self.bools)):
            if self.bools[index]:
                model.AddBoolOr([col[index].Not(), row[index].Not()]).OnlyEnforceIf(s)
                model.AddBoolOr([col[index], row[index]]).OnlyEnforceIf(s)
            else:
                model.AddBoolOr([col[index].Not(), row[index]]).OnlyEnforceIf(s)
                model.AddBoolOr([col[index], row[index].Not()]).OnlyEnforceIf(s)
