#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/14 12:00
# @Author  : NT (2201963934)
# @FileName: 3XM.py
"""
[3XM] 十字雷：雷值等于其对角接触的四个格雷数
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch


class Rule3XM(AbstractMinesRule):
    id = "3XM"
    name = "Cross-Mine"
    name.zh_CN = "十字雷"
    doc = "Mine value equals the number of mines in the four diagonally adjacent cells"
    doc.zh_CN = "雷值等于其对角接触的四个格雷数"
    tags = ["Variant", "Mine-Value", "Local"]
    creation_time = "2026-10-14"
    lib_only = True
    author = ("NT", 2201963934)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        board.register_type_special('3XM', self.get_type)

    @staticmethod
    def _diagonal_positions(pos: 'Position') -> list['Position']:
        """返回当前格的对角四个相邻位置（左上、右上、左下、右下）"""
        return [
            pos.up().left(),
            pos.up().right(),
            pos.down().left(),
            pos.down().right(),
        ]

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special='3XM')
                diag_vars = board.batch(
                    self._diagonal_positions(pos),
                    mode="variable",
                    drop_none=True,
                    special='raw',
                )
                # 雷值 = 对角四格雷数（边界外视为非雷，drop_none 已过滤）
                model.add(det == sum(diag_vars)).only_enforce_if(mine)
                # 非雷格雷值为 0
                model.add(det == 0).only_enforce_if(mine.Not())

    @staticmethod
    def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
        value = board.get_type(pos, special='raw')
        if value != "F":
            return 0
        count = 0
        for _pos in Rule3XM._diagonal_positions(pos):
            if board.in_bounds(_pos) and board.get_type(_pos, special='raw') == "F":
                count += 1
        return count
