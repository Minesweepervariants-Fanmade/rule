#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/09
# @Author  : NT
# @FileName: RM2.py
'''
[RM2] 雷区遥测：一个雷线索格中有若干个线索数，其中每个对应一行中，该线索格所在四联通雷区中位于此行的雷数。这些线索数的顺序不确定。
'''
from functools import cache
from typing import List, Dict, Tuple
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.position_set import PositionSet
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, MultiIntValue
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.impl_obj import VALUE_QUESS, MINES_TAG



def get_direction_positions(board: Board, pos: Position) -> Dict[str, PositionSet]:
    '''
    获取指定位置四个方向的3个格子（3x3区域内对应方向）
    返回：{'up': PositionSet, 'down': PositionSet, 'left': PositionSet, 'right': PositionSet}
    已过滤越界位置
    '''
    row, col = pos.row, pos.col
    board_key = pos.board_key
    bound = board.boundary(board_key)

    # 定义四个方向的位置（不包含自身）
    # 上：上一行三个
    up_positions = [Position(row - 1, col - 1, board_key),
                    Position(row - 1, col, board_key),
                    Position(row - 1, col + 1, board_key)]
    # 下：下一行三个
    down_positions = [Position(row + 1, col - 1, board_key),
                      Position(row + 1, col, board_key),
                      Position(row + 1, col + 1, board_key)]
    # 左：左一列三个
    left_positions = [Position(row - 1, col - 1, board_key),
                      Position(row, col - 1, board_key),
                      Position(row + 1, col - 1, board_key)]
    # 右：右一列三个
    right_positions = [Position(row - 1, col + 1, board_key),
                       Position(row, col + 1, board_key),
                       Position(row + 1, col + 1, board_key)]

    # 过滤有效位置
    def valid(p): return p.in_bounds(bound)
    positions = {
        'up': PositionSet([p for p in up_positions if valid(p)]),
        'down': PositionSet([p for p in down_positions if valid(p)]),
        'left': PositionSet([p for p in left_positions if valid(p)]),
        'right': PositionSet([p for p in right_positions if valid(p)])
    }

    return positions


class RuleRM2(AbstractClueRule):
    id = 'RM2'
    name = 'Remote Sensing 2'
    name.zh_CN = '雷区遥测'
    doc = 'A clue cell contains several numbers, each corresponding to a row, indicating the number of mines in the four-connected region of the clue cell located in that row. The order of these numbers is uncertain.'
    doc.zh_CN = '一个雷线索格中有若干个线索数，其中每个对应一行中，该线索格所在四联通雷区中位于此行的雷数。这些线索数的顺序不确定。'
    tags = ['Local', 'Number Clue', 'Variant']
    creation_time = '2026-07-09'
    author = ('NT', 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        '''填充所有未定义格子的线索值'''
        logger = get_logger()
        for pos, _ in board('N', special='raw'):
            direction_positions = get_direction_positions(board, pos)
            for direction in direction_positions:
                direction_positions[direction].to_board(pos.board_key)

            counts = {'up': 0, 'down': 0, 'left': 0, 'right': 0}
            for direction in counts:
                positions = direction_positions[direction]
                if positions:
                    type_list = board.batch(positions=positions, mode='type')
                    counts[direction] = type_list.count('F')

            board.set_value(
                pos,
                ValueRM2(
                    pos,
                    up=counts['up'],
                    down=counts['down'],
                    left=counts['left'],
                    right=counts['right'],
                    direction_positions=direction_positions
                )
            )
            logger.trace(f'[RM2] Filled {pos}: up={counts["up"]}, down={counts["down"]}, left={counts["left"]}, right={counts["right"]}')

        return board


class ValueRM2(AbstractClueValue):
    id = RuleRM2.id

    def __init__(self, pos: Position, up: int = 0, down: int = 0, left: int = 0, right: int = 0,
                 direction_positions: Dict[str, PositionSet] = None):
        super().__init__(pos, b'')
        self.up = up
        self.down = down
        self.left = left
        self.right = right

        if direction_positions is not None:
            self.direction_positions = direction_positions
        else:
            self.direction_positions = {}

        self.value = MultiIntValue([self.up, self.down, self.left, self.right])

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError(f'Expected value template, got {type(_data)}')

        values = MultiIntValue.try_from(_data)
        if values is not None and len(values.value) == 4:
            return cls(pos, up=values.value[0], down=values.value[1],
                       left=values.value[2], right=values.value[3])

        single = SingleIntValue.try_from(_data)
        if single is not None:
            val = single.value
            up = val // 4
            down = val // 4
            left = val // 4
            right = val - up - down - left
            return cls(pos, up=up, down=down, left=left, right=right)

        raise ValueError(f'Cannot parse RM2 value from data: {_data}')

    def high_light(self, board: 'Board') -> List['Position']:
        highlighted = []
        for direction in self.direction_positions:
            highlighted.extend(self.direction_positions[direction])
        return highlighted

    def invalid(self, board: 'Board') -> bool:
        all_positions = PositionSet()
        for direction in self.direction_positions:
            all_positions.update(self.direction_positions[direction])
        return board.batch(all_positions, mode='type', special='raw').count('N') == 0

    def deduce_cells(self, board: 'Board') -> bool:
        modified = False
        for direction, count in [('up', self.up), ('down', self.down), ('left', self.left), ('right', self.right)]:
            positions = self.direction_positions[direction]
            if not positions:
                continue

            type_dict: Dict[str, List[Position]] = {'N': [], 'F': []}
            for p in positions:
                t = board.get_type(p)
                if t in ('', 'C'):
                    continue
                type_dict[t].append(p)

            n_num = len(type_dict['N'])
            f_num = len(type_dict['F'])

            if n_num == 0:
                continue

            if f_num == count:
                for p in type_dict['N']:
                    board.set_value(p, VALUE_QUESS)
                    modified = True
                continue

            if f_num + n_num == count:
                for p in type_dict['N']:
                    board.set_value(p, MINES_TAG)
                    modified = True
                continue

        return modified

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        logger = get_logger()
        # 不再使用开关变量，直接添加约束

        # 如果 direction_positions 为空或缺少键，重新计算
        if not self.direction_positions or not all(k in self.direction_positions for k in ['up', 'down', 'left', 'right']):
            self.direction_positions = get_direction_positions(board, self.pos)
            for direction in self.direction_positions:
                self.direction_positions[direction].to_board(self.pos.board_key)

        directions = [('up', self.up), ('down', self.down), ('left', self.left), ('right', self.right)]

        for direction, target_count in directions:
            positions = self.direction_positions[direction]
            if not positions:
                if target_count != 0:
                    model.add(0 == 1)  # 直接添加矛盾
                    logger.warning(f'[RM2] Direction {direction} has no cells but target count is {target_count}')
                continue

            neighbor_vars: List[IntVar] = []
            for neighbor in positions:
                if (var := board.get_variable(neighbor)) is not None:
                    neighbor_vars.append(var)

            if not neighbor_vars:
                if target_count != 0:
                    model.add(0 == 1)
                    logger.warning(f'[RM2] Direction {direction} has no variables but target count is {target_count}')
                continue

            if len(neighbor_vars) == 1:
                model.add(neighbor_vars[0] == target_count)
            else:
                model.add(sum(neighbor_vars) == target_count)

            logger.trace(f'[RM2] Value[{self.pos}] direction {direction}: sum({neighbor_vars}) == {target_count}')
