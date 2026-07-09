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
        """快速推理：根据当前已知信息进行推断"""
        unknown_positions = []
        known_non_mine_count = 0
        
        for dx, dy in self.directions:
            cells = get_cells_in_direction(board, self.pos, dx, dy)
            
            # 找到第一个雷的位置
            first_mine_idx = -1
            for i, p in enumerate(cells):
                t = board.get_type(p)
                if t == "F":
                    first_mine_idx = i
                    break
                elif t == "N":
                    # 在第一个雷之前出现未知格子，无法确定
                    break
            
            if first_mine_idx != -1:
                # 统计雷后面的格子（直到第二个雷或边界）
                for p in cells[first_mine_idx + 1:]:
                    t = board.get_type(p)
                    if t == "F":
                        break
                    if t == "N":
                        unknown_positions.append(p)
                    else:
                        known_non_mine_count += 1
        
        if not unknown_positions:
            return False
        
        needed = self.count - known_non_mine_count
        
        if needed == 0:
            for p in unknown_positions:
                board.set_value(p, VALUE_QUESS)
            return True
        elif needed == len(unknown_positions):
            for p in unknown_positions:
                board.set_value(p, MINES_TAG)
            return True
        
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建CP-SAT约束：四个方向上穿过第一个雷后看到的非雷格子总数为count
        
        使用前缀和方法：
        - pref[i] = sum(vars[0..i-1]) 表示到位置 i 之前（不含 i）已经看到的雷数
        - 对于位置 i，如果 pref[i] == 1 且 vars[i] == 0，则计数加1
        - 这表示已经看到第一个雷，且当前格子不是雷，所以当前格子被计数
        - 如果 pref[i] >= 2，说明已经看到第二个雷，之后不再计数
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
        
        dir_counts = []
        
        for idx, vars_list in enumerate(direction_vars):
            dx, dy = self.directions[idx]
            n = len(vars_list)
            if n == 0:
                # 该方向没有格子，计数固定为0
                count_var = model.NewIntVar(0, 0, f'count_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
                dir_counts.append(count_var)
                continue
            
            # 该方向上的计数变量
            count_var = model.NewIntVar(0, n, f'count_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
            dir_counts.append(count_var)
            
            # 前缀和 pref[i] = sum(vars_list[0..i-1])，pref[0] = 0
            pref = []
            for i in range(n + 1):
                p = model.NewIntVar(0, i, f'pref_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                pref.append(p)
            model.Add(pref[0] == 0)
            for i in range(n):
                model.Add(pref[i+1] == pref[i] + vars_list[i])
            
            # 对于每个位置 i，创建布尔变量 pref_eq_1[i] 表示 pref[i] == 1
            pref_eq_1 = []
            for i in range(n):
                b = model.NewBoolVar(f'pref1_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}')
                pref_eq_1.append(b)
                # b == (pref[i] == 1)
                # 使用两个不等式约束
                # 当 b 为真时：pref[i] >= 1 且 pref[i] <= 1
                model.Add(pref[i] >= 1).OnlyEnforceIf(b)
                model.Add(pref[i] <= 1).OnlyEnforceIf(b)
                # 当 b 为假时：pref[i] <= 0 或 pref[i] >= 2
                # 更简单：使用线性约束确保 b 与 pref[i] 的关系
                # 实际上，用两个约束可能不够，因为 pref[i] 是整数，b 是布尔
                # 更好的方法是使用加和约束：pref[i] == b + extra，其中 extra 是整数 >= 0
                # 但为了简化，我采用另一种方法：
                # 直接使用 channeling 约束：pref[i] == 1 * b + extra，其中 extra 是 0 或 >=2
                # 但 CP-SAT 不直接支持这种情况，我们使用 Add 约束 + 枚举
                # 这里简单起见，使用上述两个 OnlyEnforceIf 约束，配合 b 的取值
                # 对于 b=0，pref[i] 可以是 0 或 >=2，这由条件 pref[i] <= 0 或 pref[i] >= 2 决定
                # 但我们的约束只有 b=0 时 pref[i] <= 0 或 pref[i] >= 2，这会导致模型无法同时满足两个分支
                # 所以需要使用重写
            
            # 由于上述方法复杂，改用另一种方式：引入变量表示 "pref[i] >= 1" 和 "pref[i] <= 1"
            # 然后 b = (pref[i] >= 1) AND (pref[i] <= 1)
            # 但 AND 在 CP-SAT 中需要用辅助变量
            # 实际上，更简单的方法是直接使用线性约束：
            # b <= pref[i] (因为如果 b=1，则 pref[i] >= 1)
            # b >= pref[i] - 1 (因为如果 pref[i] >= 2，则 b 必须为0；如果 pref[i]=0，b=0)
            # 即 b >= (pref[i] - 1) / 1，但 CP-SAT 支持整数除法，但效率低
            # 最可靠的方法是枚举所有可能的状态，所以我回到枚举状态方法
        
        # 由于前缀和约束在 CP-SAT 中实现 channeling 比较复杂，
        # 我们采用枚举状态的方法（第一个雷和第二个雷的位置），这是最可靠的
        # 重新使用枚举状态方法
        
        # 清空 dir_counts 并重新计算
        dir_counts = []
        for idx, vars_list in enumerate(direction_vars):
            dx, dy = self.directions[idx]
            n = len(vars_list)
            if n == 0:
                count_var = model.NewIntVar(0, 0, f'count_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
                dir_counts.append(count_var)
                continue
            
            count_var = model.NewIntVar(0, n, f'count_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
            dir_counts.append(count_var)
            
            # 状态枚举
            states = []
            # 有第一个雷的状态：i 是第一个雷，j 是第二个雷（j==n 表示没有第二个雷）
            for i in range(n):
                for j in range(i+1, n+1):
                    state = model.NewBoolVar(f'state_{self.pos.col}_{self.pos.row}_{dx}_{dy}_{i}_{j}')
                    states.append(state)
                    # 约束条件
                    model.Add(vars_list[i] == 1).OnlyEnforceIf(state)
                    if i > 0:
                        model.Add(sum(vars_list[:i]) == 0).OnlyEnforceIf(state)
                    if j > i+1:
                        model.Add(sum(vars_list[i+1:j]) == 0).OnlyEnforceIf(state)
                    if j < n:
                        model.Add(vars_list[j] == 1).OnlyEnforceIf(state)
                    model.Add(count_var == (j - i - 1)).OnlyEnforceIf(state)
            
            # 无雷状态
            no_mine = model.NewBoolVar(f'no_mine_{self.pos.col}_{self.pos.row}_{dx}_{dy}')
            for k in range(n):
                model.Add(vars_list[k] == 0).OnlyEnforceIf(no_mine)
            model.Add(count_var == 0).OnlyEnforceIf(no_mine)
            
            # 确保恰好一个状态为真
            all_states = states + [no_mine]
            model.Add(sum(all_states) == 1)
        
        # 总计数等于线索值
        total_count = sum(dir_counts)
        model.Add(total_count == self.count).OnlyEnforceIf(s)
        logger.trace(f"[1E>] Value[{self.pos}: {self.count}] add constraint: total_count == {self.count}")
