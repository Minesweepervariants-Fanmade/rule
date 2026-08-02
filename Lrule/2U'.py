#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/29 02:42
# @Author  : Wu_RH
# @FileName: 2U.py
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, MASTER_BOARD_KEY
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.size import Size

NAME_2U = "2U'"


class Rule2U(AbstractMinesRule):
    id = "2U'"
    name = "失衡"
    doc = "The number of mines in each column is different."
    doc.zh_CN = "每列的雷数不相同"
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        pos_bound = board.boundary()
        labels = {}
        for pos in board(mode="pos"):
            pos.board_key = NAME_2U
            labels[pos] = f"R{pos.row + 1}={pos.col}"
        board.generate_board(
            NAME_2U, labels=labels,
            size=Size(pos_bound.row + 1, pos_bound.col + 1)
        )
        board.set_config(NAME_2U, "pos_label", True)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for pos in board.get_col_pos(board.boundary(NAME_2U)):
            model.add(sum(board.batch(board.get_row_pos(pos), mode="var")) == 1).OnlyEnforceIf(s)
        for pos in board.get_row_pos(board.boundary(NAME_2U)):
            model.add(sum(board.batch(board.get_col_pos(pos), mode="var")) == 1).OnlyEnforceIf(s)

        # 转置：原编码每行雷数改为编码每列雷数
        for pos, pos_2u in zip(
            board.get_row_pos(board.boundary(MASTER_BOARD_KEY)),
            board.get_row_pos(board.boundary(NAME_2U)),
        ):
            col = board.get_col_pos(pos)
            col_2u = board.get_col_pos(pos_2u)
            col_var = board.batch(col, mode="var")
            col_2u_var = board.batch(col_2u, mode="var")
            for index in range(len(col_2u_var)):
                model.add(sum(col_var) == index).only_enforce_if(col_2u_var[index], s)

    def init_clear(self, board: 'Board') -> None:
        for pos in board(mode="pos", key=NAME_2U):
            board[pos] = None

    def suggest_total(self, info: dict):
        sizes = [info["size"][interactive] for interactive in info["interactive"]]

        total = 0

        for size in sizes:
            # 转置：行列互换
            total += int((size[1] - 1) * size[0] / 2)

        def a(model, total_var):
            model.Add(total == total_var)

        info["hard_fns"].append(a)

