#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09 17:29
# @Author  : NT (2201963934)
# @FileName: 1E_.py
"""
[1E>] 透视：线索表示四方向上穿过遇到的第一个雷格后能看到的非雷格数量。雷会阻挡视线。
"""

from functools import cache
from typing import List, Tuple

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def get_directions() -> List[Tuple[int, int]]:
    """返回四个方向的方向向量 (列偏移, 行偏移)"""
    return [(0, -1), (0, 1), (-1, 0), (1, 0)]  # 上, 下, 左, 右


def get_cells_in_direction(board: Board, pos: Position, dx: int, dy: int) -> List[Position]:
    """获取从pos开始沿指定方向的连续格子列表（直到边界）"""
    cells = []
    col = pos.col + dx
    row = pos.row + dy
    while board.in_bounds(Position(col, row, pos.board_key)):
        cells.append(Position(col, row, pos.board_key))
        col += dx
        row += dy
    return cells


def count_visible_cells(board: Board, pos: Position) -> int:
    """计算在四个方向上穿过第一个雷后能看到的非雷格子数量（用于填充）"""
    total = 0
    directions = get_directions()
    logger = get_logger()
    
    for dx, dy in directions:
        cells = get_cells_in_direction(board, pos, dx, dy)
        
        # 找到第一个雷的位置
        first_mine_idx = -1
        for i, p in enumerate(cells):
            if board.get_type(p) == "F":
                first_mine_idx = i
                break
        
        if first_mine_idx != -1:
            # 从雷后面的格子开始，直到遇到第二个雷或边界
            for p in cells[first_mine_idx + 1:]:
                if board.get_type(p) == "F":
                    break
                total += 1
    
    logger.debug(f"[1E>] count_visible_cells({pos}) = {total}")
    return total


class Rule1E(AbstractClueRule):
    id = "1E>"
    name = "Perspective"
    name.zh_CN = "透视"  # type: ignore[attr-defined]
    doc = "The clue indicates the number of non-mine cells visible in the four cardinal directions after passing through the first mine encountered. Mines block line of sight."
    doc.zh_CN = "线索表示四方向上穿过遇到的第一个雷格后能看到的非雷格数量。雷会阻挡视线。"  # type: ignore[attr-defined]
    tags = ["Original", "Local", "Vanilla Variant", "Number Clue", "Arrow Clue"]
    creation_time = "2026-07-09"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """填充所有未定义的格子为线索值"""
        for pos, _ in board("N", special='raw'):
            count = count_visible_cells(board, pos)
            board.set_value(pos, Value1E(pos, count=count))
        return board


class Value1E(AbstractClueValue):
    id = Rule1E.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.value = SingleIntValue(self.count)
        self.directions = get_directions()

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        template_data = _data
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError()

        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> List['Position']:
        """高亮显示所有可能影响的格子：四个方向上的所有格子"""
        positions = []
        for dx, dy in self.directions:
            cells = get_cells_in_direction(board, self.pos, dx, dy)
            positions.extend(cells)
        return positions

    def invalid(self, board: 'Board') -> bool:
        """如果所有可能影响的格子都已翻开（非'N'），则判定为无效"""
        for dx, dy in self.directions:
            cells = get_cells_in_direction(board, self.pos, dx, dy)
            for p in cells:
                if board.get_type(p) == "N":
                    return False
        return True

    def deduce_cells(self, board: 'Board') -> bool:
        """快速推理：根据当前已知信息进行推断（暂时禁用）"""
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束：四个方向上穿过第一个雷后看到的非雷格子总数为count
        
        对于每个方向：
        1. 找到第一个雷的位置（如果有）
        2. 从第一个雷后面的格子开始，直到遇到第二个雷或边界，所有非雷格子都可见
        
        实现方式：使用前缀和和辅助变量
        - 对于方向上的每个位置 i，如果前缀和 pref[i] == 1 且 vars_list[i] == 0，
          且下一个位置（如果有）不是雷，则计数加1（其实只要pref[i]==1且当前不是雷即可）
        - 但实际上我们需要更精确：从第一个雷后面开始计数，直到第二个雷或边界
        """
        model = board.get_model()
        logger = get_logger()
        
        # 获取四个方向上的所有格子变量
        direction_vars = []
        for dx, dy in self.directions:
            cells = get_cells_in_direction(board, self.pos, dx, dy)
            vars_in_dir = []
            for p in cells:
                var = board.get_variable(p)
                if var is not None:
                    vars_in_dir.append(var)
            direction_vars.append(vars_in_dir)
        
        if not any(direction_vars):
            return
        
        s = switch.get(model, self.pos)
        
        # 存储每个方向的计数变量
        dir_counts = []
        
        for idx, vars_list in enumerate(direction_vars):
            dx, dy = self.directions[idx]
            n = len(vars_list)
            
            # 该方向上的计数变量
            count_var = model.NewIntVar(0, n, f'count_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
            dir_counts.append(count_var)
            
            if n == 0:
                model.Add(count_var == 0)
                continue
            
            # 前缀和 pref[i] = sum(vars_list[0..i-1])
            pref = []
            for i in range(n + 1):
                p = model.NewIntVar(0, i, f'pref_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                pref.append(p)
            model.Add(pref[0] == 0)
            for i in range(n):
                model.Add(pref[i+1] == pref[i] + vars_list[i])
            
            # 现在计算可见格子数量
            # 可见格子必须满足：在第一个雷之后，且在第二个雷之前（或边界）
            # 即：pref[i] == 1 且 vars_list[i] == 0
            # 且如果 i+1 < n，则 pref[i+1] <= 1（表示还没有遇到第二个雷）
            # 但如果 vars_list[i] == 0，pref[i+1] == pref[i] == 1，所以自动满足
            # 因此只需要条件：pref[i] == 1 且 vars_list[i] == 0
            
            conditions = []
            for i in range(n):
                # pref[i] == 1（恰好有一个雷在当前位置之前）
                pref_eq_1 = model.NewBoolVar(f'pref_eq_1_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                model.Add(pref[i] == 1).OnlyEnforceIf(pref_eq_1)
                model.Add(pref[i] != 1).OnlyEnforceIf(pref_eq_1.Not())
                
                # not_mine: vars_list[i] == 0 (当前位置不是雷)
                not_mine = model.NewBoolVar(f'not_mine_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                model.Add(vars_list[i] == 0).OnlyEnforceIf(not_mine)
                model.Add(vars_list[i] >= 1).OnlyEnforceIf(not_mine.Not())
                
                # cond = pref_eq_1 AND not_mine
                cond = model.NewBoolVar(f'cond_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                model.Add(cond <= pref_eq_1)
                model.Add(cond <= not_mine)
                model.Add(cond >= pref_eq_1 + not_mine - 1)
                conditions.append(cond)
            
            # 计数 = 所有条件的和
            model.Add(count_var == sum(conditions))
        
        # 总计数等于线索值，且仅在开关为真时生效
        total_count = sum(dir_counts)
        model.Add(total_count == self.count).OnlyEnforceIf(s)
        logger.trace(f"[1E>] Value[{self.pos}: {self.count}] add constraint: total_count == {self.count} (enforced by switch {s})")
