#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/03
# @Author  : muratsubo
# @FileName: 2U''.py
"""
[2U''] 每行每列恰有一个符合1U的雷

1U条件：雷的上下左右四个方向均不能有雷（即孤立雷）
本规则约束：每行每列恰好有一个孤立雷（符合1U条件的雷）。
其他非孤立雷可以存在，但不计入每行每列的计数。
"""
import math
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.size import Size
from minesweepervariants.position import Position

NAME_2U = "2U''"


class Rule2U(AbstractMinesRule):
    id = "2U''"
    aliases = ("2U",)
    name = "Two Unary"
    name.zh_CN = "双一元"
    doc = "Exactly one mine per row and column that satisfies Unary (isolated mine)"
    doc.zh_CN = "每行每列恰有一个符合1U的雷（孤立雷，上下左右无雷）"

    tags = ["Creative", "Anti-Construction", "Global", "Strict R"]
    creation_time = "2026-08-01"
    author = ("muratsubo", 0)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        # 获取主交互式键
        interactive_keys = board.get_interactive_keys()
        if not interactive_keys:
            interactive_keys = board.get_board_keys()
        if not interactive_keys:
            return
        main_key = interactive_keys[0]
        pos_bound = board.boundary(main_key)
        height = pos_bound.row + 1
        width = pos_bound.col + 1
        # 创建辅助子板，尺寸与主棋盘相同
        labels = {}
        for pos in board(mode="pos", key=main_key):
            aux_pos = Position(pos.col, pos.row, NAME_2U)
            labels[aux_pos] = f"U{pos.row + 1},{pos.col + 1}"
        board.generate_board(
            NAME_2U,
            labels=labels,
            size=Size(height, width)
        )
        board.set_config(NAME_2U, "pos_label", True)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        interactive_keys = board.get_interactive_keys()
        if not interactive_keys:
            interactive_keys = board.get_board_keys()
        if not interactive_keys:
            return
        main_key = interactive_keys[0]
        boundary_pos = board.boundary(main_key)
        height = boundary_pos.row + 1
        width = boundary_pos.col + 1

        if height != width:
            model.Add(0 == 1).OnlyEnforceIf(s)
            return

        # 为每个位置创建孤立雷辅助变量
        unary_vars = {}
        for row in range(height):
            for col in range(width):
                pos = board.get_pos(row, col, main_key)
                var = board.get_variable(pos)
                unary = model.NewBoolVar(f"unary_{row}_{col}")
                unary_vars[pos] = unary

                # unary => var
                model.AddImplication(unary, var)
                # unary => 邻居不是雷
                for d in [pos.up(), pos.down(), pos.left(), pos.right()]:
                    if board.in_bounds(d):
                        nv = board.get_variable(d)
                        model.AddImplication(unary, nv.Not())
                # 如果 var 且所有邻居为0，则 unary 为真
                neighbor_vars = []
                for d in [pos.up(), pos.down(), pos.left(), pos.right()]:
                    if board.in_bounds(d):
                        neighbor_vars.append(board.get_variable(d))
                bool_or_literals = [var.Not()] + neighbor_vars + [unary]
                model.AddBoolOr(bool_or_literals).OnlyEnforceIf(s)

        # 每行恰好一个孤立雷，并将行计数存入辅助子板
        for row in range(height):
            row_unaries = [unary_vars[board.get_pos(row, col, main_key)] for col in range(width)]
            model.Add(sum(row_unaries) == 1).OnlyEnforceIf(s)
            # 在辅助子板的 (row,0) 位置存储1表示该行满足
            aux_pos = board.get_pos(row, 0, NAME_2U)
            aux_var = board.get_variable(aux_pos)
            model.Add(aux_var == 1).OnlyEnforceIf(s)

        # 每列恰好一个孤立雷，并将列计数存入辅助子板
        for col in range(width):
            col_unaries = [unary_vars[board.get_pos(row, col, main_key)] for row in range(height)]
            model.Add(sum(col_unaries) == 1).OnlyEnforceIf(s)
            aux_pos = board.get_pos(0, col, NAME_2U)
            aux_var = board.get_variable(aux_pos)
            model.Add(aux_var == 1).OnlyEnforceIf(s)

    def init_clear(self, board: 'Board') -> None:
        for pos in board(mode="pos", key=NAME_2U):
            board[pos] = None

    def suggest_total(self, info: dict):
        for key in info["interactive"]:
            max_mines = info["total"].get(key, 0)
            if max_mines > 0:
                side = int(math.sqrt(max_mines))
                if side * side == max_mines:
                    info["soft_fn"](side, 0)
                    return
