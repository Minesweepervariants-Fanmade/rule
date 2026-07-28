#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[9V] 圆规则(右线): 线索表示以该格中心为中心, 面积为9的圆内雷格所占的面积。
以格式 xi+yj+zk 展示三个线性无关权重 {w₂,w₃,w₄} 上的系数,
其中 i/j/k 为权重符号, 满足 i+j+2k=1 (即 w₁=w₂+w₃+2w₄)。
令 (n₀,n₁,n₂,n₃,n₄) 为各类雷数, n₀=0, 则 x=n₁+n₂, y=n₁+n₃, z=2n₁+n₄。
给定 (x,y,z), 解族为 (w, x-w, y-w, z-2w), w 为合法 n₁ 的任意取值。
"""
from __future__ import annotations

from ortools.sat.python.cp_model import IntVar
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.board import Board, Position
from ....abs.Rrule import AbstractClueRule, AbstractClueValue

# 21-cell neighborhood in 5 symmetry classes touched by circle r=√(9/π)≈1.693
CLASS_OFFSETS = [
    [(0, 0)],                                          # C0: center (1 cell, always N)
    [(1, 0), (-1, 0), (0, 1), (0, -1)],                # C1: cardinal (4 cells, weight w₁=1)
    [(1, 1), (1, -1), (-1, 1), (-1, -1)],              # C2: diagonal (4 cells, weight w₂≈0.796)
    [(2, 0), (-2, 0), (0, 2), (0, -2)],                # C3: dist-2 cardinal (4 cells, weight w₃≈0.168)
    [(2, 1), (2, -1), (-2, 1), (-2, -1),               # C4: knight (8 cells, weight w₄≈0.018)
     (1, 2), (1, -2), (-1, 2), (-1, -2)],
]


class Rule9V(AbstractClueRule):
    id = "9V"
    name = "Circle"
    name.zh_CN = "圆"  # type: ignore[attr-defined]
    doc = "Right-line rule: clue shows area within circle r=√(9/π) as xi+yj+zk (3 independent weights) where i = -5/4 - 9*asin(sqrt(4 - pi)/2)/(2*pi) + 9*sqrt(4 - pi)/(4*sqrt(pi)) + 9*asin(sqrt(pi)/2)/(2*pi), j = -3/2 + sqrt(36 - pi)/(4*sqrt(pi)) + 9*asin(sqrt(pi)/6)/pi, k = (-pi*(sqrt(36 - pi) + 9*sqrt(4 - pi)) + 36*sqrt(pi)*(-asin(sqrt(pi)/2) + asin(sqrt(36 - pi)/6)) + 6*pi**(3/2))/(8*pi**(3/2))"
    doc.zh_CN = "右线规则: 以格式 xi+yj+zk 表示以该格为中心、面积为9的圆内雷格所占的面积, 其中i = -5/4 - 9*asin(sqrt(4 - pi)/2)/(2*pi) + 9*sqrt(4 - pi)/(4*sqrt(pi)) + 9*asin(sqrt(pi)/2)/(2*pi), j = -3/2 + sqrt(36 - pi)/(4*sqrt(pi)) + 9*asin(sqrt(pi)/6)/pi, k = (-pi*(sqrt(36 - pi) + 9*sqrt(4 - pi)) + 36*sqrt(pi)*(-asin(sqrt(pi)/2) + asin(sqrt(36 - pi)/6)) + 6*pi**(3/2))/(8*pi**(3/2))"  # type: ignore[attr-defined]
    tags = ["Creative", "Local", "Number Clue", "Variant"]
    creation_time = "2026-04-10"
    author = ("NT", 2201963934)

    def __init__(self, board: Board = None, data=None) -> None:
        super().__init__(board, data)

    def fill(self, board: Board) -> Board:
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key, special="raw"):
                ns = [0, 0, 0, 0, 0]  # n0-n4, n0 always 0
                for ci in range(5):
                    for dx, dy in CLASS_OFFSETS[ci]:
                        _p = Position(pos.col + dx, pos.row + dy, pos.board_key)
                        if board.in_bounds(_p) and board.get_type(_p, special="raw") == "F":
                            ns[ci] += 1
                # Encode: (n₁,n₂,n₃,n₄) → x=n₁+n₂, y=n₁+n₃, z=2n₁+n₄
                x = ns[1] + ns[2]          # n₁+n₂
                y = ns[1] + ns[3]          # n₁+n₃
                z = 2 * ns[1] + ns[4]      # 2n₁+n₄
                board.set_value(pos, Value9V(pos, bytes([x, y, z])))
        return board


class Value9V(AbstractClueValue):
    id = Rule9V.id

    def __init__(self, pos: Position, code: bytes = None):
        super().__init__(pos, code)
        self.x = code[0] if code else 0  # n₁+n₂
        self.y = code[1] if code else 0  # n₁+n₃
        self.z = code[2] if code else 0  # 2n₁+n₄

    @classmethod
    def type(cls) -> bytes:
        return Rule9V.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.x, self.y, self.z])

    def __repr__(self) -> str:
        parts: list[str] = []
        if self.x:
            parts.append(f"{self.x}i")
        if self.y:
            parts.append(f"{self.y}j")
        if self.z:
            parts.append(f"{self.z}k")
        return "+".join(parts) if parts else "0"

    def high_light(self, board: Board) -> list[Position]:
        result: list[Position] = []
        for ci in range(5):
            for dx, dy in CLASS_OFFSETS[ci]:
                _p = Position(self.pos.col + dx, self.pos.row + dy, self.pos.board_key)
                if board.in_bounds(_p):
                    result.append(_p)
        return result

    def create_constraints(self, board: Board, switch: Switch):
        model = board.get_model()
        s = switch.get(model, self.pos)

        def _vars(cls_idx: int) -> list[IntVar]:
            positions = [
                Position(self.pos.col + dx, self.pos.row + dy, self.pos.board_key)
                for dx, dy in CLASS_OFFSETS[cls_idx]
            ]
            return board.batch(positions, mode="variable", drop_none=True, special="raw")

        def _add_sum(target: int, *var_lists: list[IntVar]):
            terms = [sum(v) for v in var_lists if v]
            if terms:
                model.add(sum(terms) == target).OnlyEnforceIf(s)

        v1 = _vars(1)  # C1: cardinal
        v2 = _vars(2)  # C2: diagonal
        v3 = _vars(3)  # C3: dist-2 cardinal
        v4 = _vars(4)  # C4: knight

        _add_sum(self.x, v1, v2)           # sum(C1) + sum(C2) = x
        _add_sum(self.y, v1, v3)           # sum(C1) + sum(C3) = y
        _add_sum(self.z, v1, v1, v4)       # 2·sum(C1) + sum(C4) = z

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if "code" in _data:
            return cls(pos, bytes(_data["code"]))
        raise TypeError("9V value requires code bytes")

    def weaker(self, board: Board) -> AbstractValue:
        return self

    def weaker_times(self) -> int:
        return 0
