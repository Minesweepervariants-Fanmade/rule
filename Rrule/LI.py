#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : DeepSeek Agent
# @FileName: LI.py
"""
[LI] 连线规则：线索表示将任意两雷连线，经过该格的线的数量，包含边界和四角
"""

from functools import lru_cache
from typing import List, Tuple

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template


def segment_intersects_rect(
    x1: float, y1: float, x2: float, y2: float,
    xmin: float, ymin: float, xmax: float, ymax: float
) -> bool:
    """判断线段与轴对齐矩形是否相交（包含边界）"""
    dx = x2 - x1
    dy = y2 - y1
    t0 = 0.0
    t1 = 1.0
    for p, q in [(-dx, x1 - xmin), (dx, xmax - x1), (-dy, y1 - ymin), (dy, ymax - y1)]:
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                if t > t0:
                    t0 = t
            else:
                if t < t1:
                    t1 = t
    return t0 <= t1


def compute_segment_cells(
    r1: int, c1: int, r2: int, c2: int,
    rows: int, cols: int, board_key: str
) -> List[Position]:
    """计算两个格子中心连线所经过的所有格子（包含边界和角点）"""
    x1 = c1 + 0.5
    y1 = r1 + 0.5
    x2 = c2 + 0.5
    y2 = r2 + 0.5
    cells: List[Position] = []
    for r in range(rows):
        for c in range(cols):
            if segment_intersects_rect(x1, y1, x2, y2, c, r, c + 1, r + 1):
                cells.append(Position(c, r, board_key))
    return cells


@lru_cache(maxsize=None)
def get_path_pairs_for_size(rows: int, cols: int) -> dict[Tuple[int, int], List[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    """预计算所有位置对及其路径覆盖的格子，返回每个格子坐标到位置对列表的映射"""
    positions = [(r, c) for r in range(rows) for c in range(cols)]
    pairs = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            pairs.append((positions[i], positions[j]))
    mapping: dict[Tuple[int, int], List[Tuple[Tuple[int, int], Tuple[int, int]]]] = {}
    for (r1, c1), (r2, c2) in pairs:
        # 计算路径上的所有格子
        path_cells = compute_segment_cells(r1, c1, r2, c2, rows, cols, "")  # board_key 不用
        for pos in path_cells:
            key = (pos.row, pos.col)
            mapping.setdefault(key, []).append(((r1, c1), (r2, c2)))
    return mapping


class RuleLI(AbstractClueRule):
    id = "LI"
    name = "Line"
    name.zh_CN = "连线"  # type: ignore[attr-defined]
    doc = "Each number indicates the number of lines connecting any two mines that pass through this cell, including boundaries and corners."
    doc.zh_CN = "线索表示将任意两雷连线，经过该格的线的数量，包含边界和四角。"  # type: ignore[attr-defined]
    tags = ["Local", "Number Clue"]
    creation_time = "2026-07-09"
    author = ("小绿草", 3021857082)

    def fill(self, board: 'Board') -> 'Board':
        """填充题板：根据雷的位置计算每个格子的连线数"""
        bound = board.boundary()
        rows = bound.row + 1
        cols = bound.col + 1
        keys = board.get_board_keys()
        board_key = keys[0] if keys else ""

        # 获取所有雷的位置
        mine_positions = [pos for pos, t in board("F", special='raw')]
        # 统计每个格子的连线数
        counts = {}
        for i in range(len(mine_positions)):
            for j in range(i + 1, len(mine_positions)):
                p1 = mine_positions[i]
                p2 = mine_positions[j]
                path = compute_segment_cells(p1.row, p1.col, p2.row, p2.col, rows, cols, board_key)
                if path:
                    for pos in path:
                        counts[pos] = counts.get(pos, 0) + 1
        # 设置线索值（非雷位置）
        for r in range(rows):
            for c in range(cols):
                pos = Position(c, r, board_key)
                if board.in_bounds(pos) and board.get_type(pos) != 'F':
                    count = counts.get(pos, 0)
                    board.set_value(pos, ValueLI(pos, count))
        return board


class ValueLI(AbstractClueValue):
    id = RuleLI.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractClueValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid value template for LI clue")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Failed to parse LI clue value from JSON")
        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> List['Position']:
        # 返回自身即可，也可返回经过该格的所有雷对？但为简化，返回None表示不高亮
        return None

    def invalid(self, board: 'Board') -> bool:
        """如果经过该格的所有位置对中的两个位置都已确定（非'N'），则认为该线索无效（可被移除）"""
        bound = board.boundary()
        rows = bound.row + 1
        cols = bound.col + 1
        mapping = get_path_pairs_for_size(rows, cols)
        pos_key = (self.pos.row, self.pos.col)
        pairs = mapping.get(pos_key, [])
        if not pairs:
            return True
        keys = board.get_board_keys()
        board_key = keys[0] if keys else ""
        for (r1, c1), (r2, c2) in pairs:
            p1 = Position(c1, r1, board_key)
            p2 = Position(c2, r2, board_key)
            if board.get_type(p1) == 'N' or board.get_type(p2) == 'N':
                return False
        return True

    def deduce_cells(self, board: 'Board') -> bool:
        # 快速推理：暂无实现
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束: 经过此格子的连线数等于count"""
        model = board.get_model()
        logger = get_logger()
        bound = board.boundary()
        rows = bound.row + 1
        cols = bound.col + 1
        keys = board.get_board_keys()
        board_key = keys[0] if keys else ""

        mapping = get_path_pairs_for_size(rows, cols)
        pos_key = (self.pos.row, self.pos.col)
        pairs = mapping.get(pos_key, [])
        if not pairs:
            return

        # 用于缓存AND变量，避免重复创建
        if not hasattr(board, '_li_and_cache'):
            board._li_and_cache = {}
        and_vars: List[IntVar] = []
        for (r1, c1), (r2, c2) in pairs:
            p1 = Position(c1, r1, board_key)
            p2 = Position(c2, r2, board_key)
            v1 = board.get_variable(p1)
            v2 = board.get_variable(p2)
            if v1 is None or v2 is None:
                continue
            pair_key = ((r1, c1), (r2, c2))
            if pair_key not in board._li_and_cache:
                and_var = model.NewBoolVar(f'li_and_{r1}_{c1}_{r2}_{c2}')
                model.Add(and_var <= v1)
                model.Add(and_var <= v2)
                model.Add(and_var >= v1 + v2 - 1)
                board._li_and_cache[pair_key] = and_var
            and_vars.append(board._li_and_cache[pair_key])

        if and_vars:
            s = switch.get(model, self.pos)
            model.Add(sum(and_vars) == self.count).OnlyEnforceIf(s)
            logger.trace(f"[LI] Value[{self.pos}: {self.count}] add: {len(and_vars)} pairs sum == {self.count}")
