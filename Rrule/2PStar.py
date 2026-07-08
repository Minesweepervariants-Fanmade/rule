#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : Agent
# @FileName: 2PStar.py
"""
[2P*] 线索表示距离该格最近的两个雷的切比雪夫距离之和
"""

from typing import List
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger


def chebyshev_neighbors(pos: Position, distance: int) -> List[Position]:
    """返回距离当前位置切比雪夫距离为 distance 的所有位置（环），不进行边界过滤"""
    neighbors = []
    if distance == 0:
        return [pos.clone()]
    for dx in range(-distance, distance + 1):
        neighbors.append(pos.up(distance).right(dx))   # 上边
        neighbors.append(pos.down(distance).right(dx)) # 下边
    for dy in range(-distance + 1, distance):
        neighbors.append(pos.left(distance).down(-dy)) # 左边
        neighbors.append(pos.right(distance).down(-dy))# 右边
    return neighbors


def chebyshev_neighbors_range(pos: Position, from_dist: int, to_dist: int) -> List[Position]:
    result = []
    for d in range(from_dist, to_dist + 1):
        result.extend(chebyshev_neighbors(pos, d))
    return result


class Rule2PStar(AbstractClueRule):
    id = "2P*"
    name = "Two Point Star"
    name.zh_CN = "两点星"
    doc = "Each number indicates the sum of Chebyshev distances to the two nearest mines"
    doc.zh_CN = "线索表示距离该格最近的两个雷的切比雪夫距离之和"
    tags = ["Local", "Number Clue", "Variant"]
    creation_time = "2026-03-01"
    author = ("咸鱼", 3898637422)

    def fill(self, board: Board) -> Board:
        if len([_ for _ in board("F")]) < 2:
            return board
        for pos, _ in board("N"):
            a_lay = b_lay = -1
            r = 0
            while b_lay == -1:
                r += 1
                ring = chebyshev_neighbors(pos, r)
                valid_ring = [p for p in ring if board.in_bounds(p)]
                if not valid_ring:
                    continue
                count = board.batch(valid_ring, mode="type").count("F")
                if count >= 2:
                    if a_lay == -1:
                        a_lay = b_lay = r
                    else:
                        b_lay = r
                elif count == 1:
                    if a_lay == -1:
                        a_lay = r
                    else:
                        b_lay = r
            board.set_value(pos, Value2PStar(pos, bytes([a_lay + b_lay])))
        return board


class Value2PStar(AbstractClueValue):
    id = Rule2PStar.id

    def __init__(self, pos: Position, code: bytes):
        super().__init__(pos, code)
        self.value = SingleIntValue(code[0])
        self.pos = pos

    def __repr__(self) -> str:
        return f"{self.value.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule2PStar.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value.value])

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid value template")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Cannot parse SingleIntValue")
        return cls(pos, bytes([value.value]))

    def high_light(self, board: Board) -> List[Position]:
        n = 1
        v = 0
        positions = []
        while True:
            ring = chebyshev_neighbors(self.pos, n)
            ring = [p for p in ring if board.in_bounds(p)]
            if not ring:
                break
            types = board.batch(ring, mode="type")
            v += types.count("F") + types.count("N")
            for p, t in zip(ring, types):
                if t in ("F", "N"):
                    positions.append(p)
            if v >= 2:
                break
            n += 1
        return positions

    def invalid(self, board: Board) -> bool:
        return board.batch(self.high_light(board), mode="type", special='raw').count("N") == 0

    def deduce_cells(self, board: Board) -> bool:
        return False

    def create_constraints(self, board: Board, switch: Switch):
        model = board.get_model()
        logger = get_logger()
        s = switch.get(model, self)  # 使用 self 作为键

        total_value = self.value.value
        if total_value <= 0:
            model.Add(sum([]) == 1).OnlyEnforceIf(s)
            return

        # 枚举所有可能的 (a, b) 其中 a <= b 且 a + b = total_value
        possible_pairs = []
        for a in range(1, total_value // 2 + 1):
            b = total_value - a
            if a <= b:
                possible_pairs.append((a, b))
        if not possible_pairs:
            model.Add(sum([]) == 1).OnlyEnforceIf(s)
            return

        sub_vars = []
        for a, b in possible_pairs:
            var = model.NewBoolVar(f"2P*_{self.pos}_{a}_{b}")
            if a == b:
                ring_a = chebyshev_neighbors(self.pos, a)
                valid_a = [p for p in ring_a if board.in_bounds(p)]
                vars_a = board.batch(valid_a, mode="variable", drop_none=True)
                if vars_a:
                    model.Add(sum(vars_a) >= 2).OnlyEnforceIf([var, s])
                else:
                    model.Add(sum([]) == 1).OnlyEnforceIf([var, s])
                    continue
                inner = chebyshev_neighbors_range(self.pos, 1, a - 1)
                valid_inner = [p for p in inner if board.in_bounds(p)]
                vars_inner = board.batch(valid_inner, mode="variable", drop_none=True)
                if vars_inner:
                    model.Add(sum(vars_inner) == 0).OnlyEnforceIf([var, s])
            else:
                ring_a = chebyshev_neighbors(self.pos, a)
                valid_a = [p for p in ring_a if board.in_bounds(p)]
                vars_a = board.batch(valid_a, mode="variable", drop_none=True)
                if vars_a:
                    model.Add(sum(vars_a) == 1).OnlyEnforceIf([var, s])
                else:
                    model.Add(sum([]) == 1).OnlyEnforceIf([var, s])
                    continue
                ring_b = chebyshev_neighbors(self.pos, b)
                valid_b = [p for p in ring_b if board.in_bounds(p)]
                vars_b = board.batch(valid_b, mode="variable", drop_none=True)
                if vars_b:
                    model.Add(sum(vars_b) >= 1).OnlyEnforceIf([var, s])
                else:
                    model.Add(sum([]) == 1).OnlyEnforceIf([var, s])
                    continue
                inner = chebyshev_neighbors_range(self.pos, 1, a - 1)
                valid_inner = [p for p in inner if board.in_bounds(p)]
                vars_inner = board.batch(valid_inner, mode="variable", drop_none=True)
                if vars_inner:
                    model.Add(sum(vars_inner) == 0).OnlyEnforceIf([var, s])
                middle = chebyshev_neighbors_range(self.pos, a + 1, b - 1)
                valid_middle = [p for p in middle if board.in_bounds(p)]
                vars_middle = board.batch(valid_middle, mode="variable", drop_none=True)
                if vars_middle:
                    model.Add(sum(vars_middle) == 0).OnlyEnforceIf([var, s])
            sub_vars.append(var)

        if sub_vars:
            model.AddBoolOr(sub_vars).OnlyEnforceIf(s)
            logger.trace(f"[2P*] pos {self.pos} value[{self.value.value}] added {len(sub_vars)} cases")
        else:
            model.Add(sum([]) == 1).OnlyEnforceIf(s)
