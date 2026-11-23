#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/12 15:52
# @Author  : mabopei1 (81500378)
# @FileName: 5Q.py
"""
[5Q]正方形顶点: 题板上存在R/4个顶点互不重合的、方向及大小任意的正方形，
每个雷表示这些正方形的顶点。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


def _square_vertices(pos, dx: int, dy: int) -> tuple:
    """
    以 pos 为一个顶点、以 (dx, dy) 和其顺时针旋转 90 度后的 (dy, -dx)
    为两条邻边构造正方形，返回四个顶点。
    """
    return (
        pos,
        pos.shift(dx, dy),
        pos.shift(dy, -dx),
        pos.shift(dx + dy, dy - dx),
    )


def _enumerate_squares(board: Board, key: str) -> list[tuple]:
    """
    枚举题板上所有由合法格子构成的、方向及大小任意的正方形。

    每个正方形用四个坐标的规范元组表示，并按其坐标排序去重。
    坐标约定与 Position 一致: shift(col, row)。
    """
    size = board.get_config(key, "size")
    positions = [pos for pos, _ in board(key=key)]
    squares: dict[tuple, tuple] = {}

    for pos in positions:
        for dx in range(size.cols):
            for dy in range(size.rows):
                if dx == 0 and dy == 0:
                    continue
                vertices = _square_vertices(pos, dx, dy)
                if any(not board.is_valid(vertex) for vertex in vertices):
                    continue
                if len(set(vertices)) != 4:
                    continue
                canonical = tuple(sorted(vertices, key=lambda p: (p.col, p.row)))
                squares[canonical] = vertices

    return list(squares.values())


class Rule5Q(AbstractMinesRule):
    id = "5Q"
    name = "Square Vertex"
    name.zh_CN = "正方形顶点"
    doc = (
        "There are R/4 squares of arbitrary orientation and size whose vertices "
        "are pairwise disjoint; every mine is a vertex of these squares."
    )
    doc.zh_CN = (
        "题板上存在R/4个顶点互不重合的、方向及大小任意的正方形，"
        "每个雷表示这些正方形的顶点"
    )
    author = ("mabopei1", 81500378)
    tags = ["Creative", "Global", "Construction"]
    creation_time = "2026-05-12"

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            squares = _enumerate_squares(board, key)
            square_vars = [
                model.new_bool_var(f"5Q_square_{key}_{index}")
                for index in range(len(squares))
            ]

            # 先按格子收集包含它的所有候选正方形。
            incident: dict = {pos: [] for pos, _ in board(key=key)}
            for square_var, vertices in zip(square_vars, squares):
                for vertex in vertices:
                    incident[vertex].append(square_var)

            # 精确覆盖: 每个雷恰好是一个被选中正方形的顶点，
            # 非雷不能是任何被选中正方形的顶点。
            # 由于每个正方形有 4 个互不相同的顶点，这同时保证选中的
            # 正方形数量为 R/4，且所有正方形的顶点互不重合。
            for pos, mine_var in board(key=key, mode="variable"):
                model.add(sum(incident[pos]) == mine_var).only_enforce_if(s)

    def suggest_total(self, info: dict):
        # 每个正方形恰有 4 个雷作为顶点，因此总雷数必须是 4 的倍数。
        def total_multiple_of_four(model, total):
            model.add_modulo_equality(0, total, 4)

        ub = 0
        for key in info["interactive"]:
            ub += info["total"][key]

        info["soft_fn"](ub * 0.4, 0)
        info["hard_fns"].append(total_multiple_of_four)
