#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/11 21:51
# @Author  : Wu_RH
# @FileName: 3E.py

"""
[URB-3E]演化: 每个3x1区域决定其中间下方1格是否为雷，演化被当前题板所有区域共享。
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Size
from minesweepervariants.utils.impl_obj import VALUE_QUESS, MINES_TAG

NAME_3E = ["3E_x", "3E_y"]


class Rule3E(AbstractMinesRule):
    id = "URB-3E"
    name = "Evolution"
    name.zh_CN = "循环演化"
    doc = "Each 3x1 area determines whether the cell below its middle is a mine; the board wraps around at all boundaries, and evolution is shared across all areas of the current board"
    doc.zh_CN = "每个3x1区域决定其中间下方1格是否为雷，题板所有边界均循环，演化被当前题板所有区域共享。"
    tags = ["Creative", "Aux Board", "Extensive Trial", "Local"]
    creation_time = "2025-08-06"
    author = ("哈嘿袁", 2977976933)

    def __init__(self, board: Board, data=None):
        super().__init__(board, data)
        board.generate_board(NAME_3E[0], size=Size(3, 8))
        board.generate_board(NAME_3E[1], size=Size(1, 8))
        board.set_config(NAME_3E[1], "VALUE", VALUE_QUESS)
        board.set_config(NAME_3E[1], "MINES", MINES_TAG)

    @staticmethod
    def get_wrapped_pos(board: Board, row: int, col: int, key):
        boundary = board.boundary(key=key)
        return board.get_pos(
            row % (boundary.row + 1),
            col % (boundary.col + 1),
            key
        )

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()

        # 3 bit 固定对应 8 种状态
        vals_list = []

        for i in range(8):
            x = model.NewIntVar(i, i, f"[3E]{i}_x")
            y = board.get_variable(board.get_pos(i, 0, NAME_3E[1]))
            s_pos = board.get_pos(i, 1, NAME_3E[0])
            s = switch.get(model, s_pos)
            vals_list.append([x, y, s])

        bool_var_index = 0

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            height = boundary.row + 1
            width = boundary.col + 1

            for row_index in range(height):
                for col_index in range(width):
                    # 横向连续三个格子，列方向循环
                    positions = [
                        self.get_wrapped_pos(
                            board, row_index, col_index + offset, key
                        )
                        for offset in range(3)
                    ]

                    variables = board.batch(positions, mode="variable")

                    # 中间格子的下方，行列均循环
                    target = self.get_wrapped_pos(
                        board, row_index + 1, col_index + 1, key
                    )

                    y_variables = board.get_variable(target)

                    if y_variables is None:
                        continue

                    expression = (
                        4 * variables[0]
                        + 2 * variables[1]
                        + variables[2]
                    )

                    for var_x, var_y, s in vals_list:
                        cond = model.NewBoolVar(f"[3E]{bool_var_index}")

                        model.Add(
                            var_x == expression
                        ).OnlyEnforceIf([cond, s])

                        model.Add(
                            var_x != expression
                        ).OnlyEnforceIf([cond.Not(), s])

                        model.Add(
                            y_variables == var_y
                        ).OnlyEnforceIf([cond, s])

                        bool_var_index += 1

    def init_board(self, board: 'Board'):
        # 初始化 8 种三 bit 状态
        for index, pos in enumerate(
            board.get_col_pos(board.get_pos(0, 0, NAME_3E[0]))
        ):
            pos1, pos2, pos3 = board.get_row_pos(pos)

            board.set_value(pos1, MINES_TAG if index & 4 else VALUE_QUESS)
            board.set_value(pos2, MINES_TAG if index & 2 else VALUE_QUESS)
            board.set_value(pos3, MINES_TAG if index & 1 else VALUE_QUESS)

        y_col = board.get_col_pos(board.boundary(key=NAME_3E[1]))

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)

            height = boundary.row + 1
            width = boundary.col + 1

            for row_index in range(height):
                for col_index in range(width):
                    positions = [
                        self.get_wrapped_pos(
                            board, row_index, col_index + offset, key
                        )
                        for offset in range(3)
                    ]

                    types = board.batch(positions, mode="type")

                    target = self.get_wrapped_pos(
                        board, row_index + 1, col_index + 1, key
                    )

                    y_type = board.get_type(target)

                    if y_type == "":
                        continue

                    index = (
                        (4 if types[0] == "F" else 0)
                        + (2 if types[1] == "F" else 0)
                        + (1 if types[2] == "F" else 0)
                    )

                    board.set_value(
                        y_col[index],
                        MINES_TAG if y_type == "F" else VALUE_QUESS
                    )

    def init_clear(self, board: 'Board', vice_board):
        for pos, _ in board("F" if vice_board else "CF", key=NAME_3E[1]):
            board.set_value(pos, None)