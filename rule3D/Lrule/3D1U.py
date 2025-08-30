#!/usr/bin/env python3
"""
[3D1U] 三维一元 (Unary)：所有雷不能与其他雷相邻
(3维一元?那你这一维多少元)
"""
from .....abs.board import AbstractBoard
from .. import Abstract3DMinesRule


class Rule3D1U(Abstract3DMinesRule):
    name = ["3D1U", "3DU", "三维一元"]
    doc = "所有雷不能与其他雷相邻"

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, var in board(mode="variable"):
            if board.in_bounds(pos.down()):
                model.Add(board.get_variable(pos.down()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.up()):
                model.Add(board.get_variable(pos.up()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.right()):
                model.Add(board.get_variable(pos.right()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.left()):
                model.Add(board.get_variable(pos.left()) == 0).OnlyEnforceIf([var, s])
            if Abstract3DMinesRule.up(board, pos, n=1):
                model.Add(board.get_variable(self.up(board, pos, n=1)) == 0).OnlyEnforceIf([var, s])
            if Abstract3DMinesRule.down(board, pos, n=1):
                model.Add(board.get_variable(self.down(board, pos, n=1)) == 0).OnlyEnforceIf([var, s])
