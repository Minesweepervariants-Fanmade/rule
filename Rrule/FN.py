#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/26 16:44
# @Author  : Wu_RH
# @FileName: FN.py
from typing import Union, List, Self, cast

from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.board import Board, Position, Size
from minesweepervariants.utils.value_template import SingleIntValue, Template
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS, VALUE_QUESS


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
NUM_RANGE = lambda x: (4 // (x + 1), x - 1 + 4 // (x + 1))


class DataFN(SingleIntValue):
    def __init__(self, value: int, flag: bool, is_mine: bool = False):
        super().__init__(value, is_mine)
        self.flag = flag

    def _template(self) -> Template:
        result = super()._template()
        result["flag"] = self.flag
        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        value = cast(int, data["data"])
        flag = cast(bool, data["flag"])
        return cls(value, flag)


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
        if data is not None and any(i not in "NFC" for i in data):
            raise ValueError("参数选项:N:不使用循环题板;F:禁止在题板的角落放置线索;C:禁止在题板贴边放置线索")
        self.fn_flag = data is None or (data is not None and "N" not in data)
        self.put_F_flag = data is not None and "F" in data
        self.put_C_flag = data is not None and "C" in data
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
        def check_pos(_pos: Position, _board: 'Board') -> bool:
            flag = 0
            if _pos.row in [0, _board.boundary(_pos.board_key).row]:
                flag += 1
            if _pos.col in [0, _board.boundary(_pos.board_key).col]:
                flag += 1
            if flag == 2 and self.put_F_flag:
                return True
            if flag == 1 and self.put_C_flag:
                return True
            return False
        sum_num = 0
        len_num = 0
        for pos, _ in board("N", mode="none"):
            if check_pos(pos, board):
                continue
            sum_num += board.batch(
                get_nei(pos, board) if self.fn_flag else pos.neighbors(2),
                "type").count("F")
            len_num += 1
        self.total = max(min(self.num_range[1] - 1, int(sum_num / len_num)), self.num_range[0])
        for pos, _ in board("N", mode="none"):
            if check_pos(pos, board):
                board[pos] = VALUE_QUESS
                continue
            value = board.batch(
                get_nei(pos, board) if self.fn_flag else pos.neighbors(2),
                "type").count("F") - self.total
            obj = ValueFN(pos, value, self.fn_flag)
            board[pos] = obj
        return board


class ValueFN(AbstractClueValue):
    id = RuleFN.id

    def __init__(self, pos: 'Position', value: int, flag: bool) -> None:
        super().__init__(pos)
        self.value: DataFN = DataFN(value, flag)
        self.flag = flag

    def __repr__(self) -> str:
        return ("+" + str(self.value.value)) if self.value.value > 0 else str(self.value.value)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'Template') -> Self:
        value_data = DataFN.try_from(data)
        return cls(pos, value_data.value, value_data.flag)

    def high_light(self, board: 'Board') -> List['Position'] | None:
        return get_nei(self.pos, board) if self.flag else self.pos.neighbors(2)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        global_var = model.new_int_var(0, 8, "global")
        s = switch.get(model, self)
        model.add(
            sum(
                board.batch(
                    get_nei(self.pos, board) if self.flag else self.pos.neighbors(2),
                    "var", drop_none=True)
            ) == global_var + self.value.value
        ).only_enforce_if(s)
        FN_Bound = board.boundary(FN_NAME)
        col_var = board.batch(board.get_col_pos(FN_Bound), "var")
        range_start = NUM_RANGE(FN_Bound.row + 1)[0]
        for i in range(FN_Bound.row + 1):
            taget_num = range_start + i
            model.add(global_var == taget_num).OnlyEnforceIf(col_var[i], s)
            model.add(global_var != taget_num).OnlyEnforceIf(col_var[i].Not(), s)
        model.add(sum(board.batch(board.get_col_pos(board.boundary(FN_NAME)), 'var')) == 1).OnlyEnforceIf(s)

