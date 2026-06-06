#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/26 16:44
# @Author  : Wu_RH
# @FileName: FN.py
from typing import Union, List

from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.board import Board, JSONObject, ImmutableDict, Position, Size
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS


def get_nei(pos: Position, board: Board) -> List[Position]:
    """
    获取 pos 的八邻域坐标（包含对角线），超出 bound 范围时循环到另一侧。

    参数:
        pos: 对象，有 row, col 属性（假设值为整数）
        bound: 整数，网格尺寸为 bound x bound，坐标范围 0 ~ bound-1

    返回:
        list of (row, col) 八邻域坐标（顺序：右下、下、左下、右、左、右上、上、左上）
    """
    # 八方向偏移（行列顺序）
    directions = [
        (1, 1), (1, 0), (1, -1),
        (0, 1), (0, -1),
        (-1, 1), (-1, 0), (-1, -1)
    ]

    neighbors = []
    for dr, dc in directions:
        nr = (pos.row + dr) % (board.boundary(pos.board_key).row + 1)
        nc = (pos.col + dc) % (board.boundary(pos.board_key).col + 1)
        neighbors.append(board.get_pos(nr, nc, pos.board_key))

    return neighbors


FN_NAME = "FN"
NUM_RANGE = lambda x: ((9 - x) // 2, 9 - (10 - x) // 2)


class RuleFN(AbstractClueRule):
    id = "FN"
    name = "FloatNumber"
    name.zh_CN = "浮数"
    doc = "For each cell, displayed +N/-N = (8-neighbor mines(cyclic indices.)) − (unfixed global standard value (range: [0-8]))."
    doc.zh_CN = "周围八格(题板于边界循环)的雷数被一个全局的标准值进行做差 标准值不固定(范围0-8) 所显示的数字表示为+N或-N 与标准值运算后得到实际雷值"
    tags = ['Creative', 'Global', 'Mine-Counting']
    author = ("雾", 3140864122)
    creation_time = "2026-05-26 16:37:56"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        num_size = min(9, max(board.boundary(key).row + 1 for key in board.get_interactive_keys()))
        self.num_range = NUM_RANGE(num_size)
        board.generate_board(FN_NAME, size=Size(1, num_size), labels=[str(i) for i in range(*self.num_range)])
        board.set_config(FN_NAME, "pos_label", True)
        self.total = 0

    def init_board(self, board: 'Board') -> None:
        for pos, _ in board(key=FN_NAME):
            board[pos] = VALUE_CROSS
        board[board.get_col_pos(board.boundary(FN_NAME))[self.total - self.num_range[0]]] = VALUE_CIRCLE

    def init_clear(self, board: 'Board') -> None:
        for pos, _ in board(key=FN_NAME):
            board[pos] = None

    def fill(self, board: 'Board') -> 'Board':
        sum_num = 0
        len_num = 0
        for pos, _ in board("N", mode="none"):
            sum_num += board.batch(get_nei(pos, board), "type").count("F")
            len_num += 1
        self.total = max(min(self.num_range[1] - 1, int(sum_num / len_num)), self.num_range[0])
        for pos, _ in board("N", mode="none"):
            value = board.batch(get_nei(pos, board), "type").count("F") - self.total
            obj = ValueFN.from_json(pos, {"value": value})
            board[pos] = obj
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        model.add(sum(board.batch(board.get_col_pos(board.boundary(FN_NAME)), 'var')) == 1).OnlyEnforceIf(
            switch.get(model, self))


class ValueFN(AbstractClueValue):
    id = "FN"
    def __init__(self, pos: 'Position', value: int) -> None:
        super().__init__(pos)
        self.value = value

    def __repr__(self) -> str:
        return ("+" + str(self.value)) if self.value > 0 else str(self.value)

    def high_light(self, board: 'Board') -> List['Position'] | None:
        return get_nei(self.pos, board)

    @classmethod
    def from_json(cls, pos: 'Position', data: Union['JSONObject', dict]) -> 'ValueFN':
        return ValueFN(pos, data["value"])

    def json(self) -> 'JSONObject':
        return ImmutableDict({"value": self.value})

    @classmethod
    def type(cls) -> bytes:
        return RuleFN.id.encode("ascii")

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        global_var = model.new_int_var(0, 8, "global")
        s = switch.get(model, self)
        model.add(
            sum(
                board.batch(get_nei(self.pos, board), "var", drop_none=True)
            ) == global_var + self.value
        ).only_enforce_if(s)
        FN_Bound = board.boundary(FN_NAME)
        col_var = board.batch(board.get_col_pos(FN_Bound), "var")
        range_start = NUM_RANGE(FN_Bound.row + 1)[0]
        for i in range(FN_Bound.row + 1):
            taget_num = range_start + i
            model.add(global_var == taget_num).OnlyEnforceIf(col_var[i], s)
            model.add(global_var != taget_num).OnlyEnforceIf(col_var[i].Not(), s)
