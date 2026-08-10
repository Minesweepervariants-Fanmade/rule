#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/10
# @Author  : DeepSeek Agent
# @FileName: 2A+.py
"""
[2A+] 线索表示1X'范围4格中雷的雷值之和，其中非雷格雷值为0，每一个雷的雷值等于所在四联通雷区的总面积
"""

from typing import List, Dict, Tuple, Optional, Self, cast
from collections import deque

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.value_template import SingleIntValue, Template
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.impl_obj import POSITION_TAG
from ...rule.Lrule.connect import connect


ID_AREA = "2A+_AREA"
COUNT_AREA = "2A+_COUNT"
DEBUG = False


def pos2seed(input_pos: Position, board: Board) -> int:
    bound = board.boundary(input_pos.board_key)
    offset = 0
    for board_key in board.get_board_keys():
        if board_key == input_pos.board_key:
            break
        offset += len([pos for pos, _ in board(key=board_key)])
    return input_pos.row * (bound.col + 1) + input_pos.col + 1 + offset


def seed2pos(input_seed: int, board: Board) -> Position:
    board_key = None
    for board_key in board.get_board_keys():
        total = len([pos for pos, _ in board(key=board_key)])
        if input_seed < total:
            break
        input_seed -= total
    if board_key is None:
        return POSITION_TAG
    bound = board.boundary(board_key)
    return board.get_pos(
        (input_seed - 1) // (bound.col + 1),
        (input_seed - 1) % (bound.col + 1),
        board_key
    )


class Rule2Ap(AbstractClueRule):
    """
    [2A+] 右线规则：线索值 = 上下左右四格中雷的雷值之和，雷的雷值 = 所在四联通雷区面积
    """
    id = "2A+"
    aliases = ()
    name = "Area Sum Plus"
    name.zh_CN = "面积和加"
    doc = "Clue value equals sum of mine values in the four orthogonal adjacent cells, where each mine's value is the area of its 4-connected mine region."
    doc.zh_CN = "线索表示1X'范围4格中雷的雷值之和，其中非雷格雷值为0，每一个雷的雷值等于所在四联通雷区的总面积"
    tags = ["Creative", "Local", "Number Clue", "Mine-Value", "Connectivity"]
    creation_time = "2026-08-10"
    author = ("咸鱼isbvoh", 3898637422)

    def __init__(self, board: "Board" = None, data=None):
        super().__init__(board, data)
        self.debug_vars = {}

    def fill(self, board: 'Board') -> 'Board':
        """
        根据完整答案板填充所有非雷格为线索值。
        1. 计算每个雷所在雷区的面积。
        2. 对于每个非雷格，计算其上下左右四个邻居中雷的雷值之和。
        """
        logger = get_logger()
        # 1. 收集所有雷的位置，并计算每个雷所属的连通块面积
        mines = list(board("F", special='raw', mode="pos"))
        area_map: Dict[Position, int] = {}

        if not mines:
            # 没有雷，所有线索值为0
            for pos, _ in board("N", special='raw'):
                board.set_value(pos, Value2Ap(pos, 0))
            return board

        # BFS 分组雷格，计算每个连通块的面积
        mine_set = set(mines)
        visited = set()
        for start in mines:
            if start in visited:
                continue
            # BFS 获取当前连通块的所有雷格
            queue = deque([start])
            visited.add(start)
            component = []
            while queue:
                cur = queue.popleft()
                component.append(cur)
                for neighbor in cur.neighbors(1):  # 四连通
                    if neighbor in visited or neighbor not in mine_set:
                        continue
                    if not board.in_bounds(neighbor):
                        continue
                    visited.add(neighbor)
                    queue.append(neighbor)
            area = len(component)
            for pos in component:
                area_map[pos] = area

        # 2. 为每个非雷格计算线索值
        for pos, _ in board("N", special='raw'):
            total = 0
            for neighbor in [pos.up(), pos.down(), pos.left(), pos.right()]:
                if board.in_bounds(neighbor) and board.get_type(neighbor, special='raw') == 'F':
                    total += area_map.get(neighbor, 0)
            board.set_value(pos, Value2Ap(pos, total))
            logger.trace(f"[2A+] {pos}: total={total}")

        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        创建约束：
        1. 使用 connect 函数为雷格分配连通块 ID，并计算每个连通块的面积。
        2. 将面积存储为 special 变量 AREA。
        3. 对于每个线索格，约束其上下左右邻居的 AREA 变量之和等于线索值。
        """
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 1. 收集所有位置及其变量
        positions_vars = [(pos, var) for pos, var in board("always", mode="variable", special='raw')]
        if not positions_vars:
            return

        pos_list, var_list = zip(*positions_vars)
        n = len(pos_list)

        # 2. 使用 connect 为雷格分配连通块 ID
        component_ids = connect(
            model=model,
            board=board,
            switch=s,
            component_num=None,
            ub=False,
            connect_value=1,  # 雷连通
            nei_value=1,      # 四连通
            positions_vars=positions_vars,
            special='raw'
        )

        # 3. 计算每个连通块的面积，并存储为 AREA 变量
        # 首先为每个位置创建 AREA 变量
        area_vars: Dict[Position, IntVar] = {}
        for pos, _ in board("always", mode="variable", special='raw'):
            # 对于非雷格，AREA 为 0
            # 对于雷格，稍后会被约束为其所在连通块的面积
            max_area = len(pos_list)
            area_var = model.NewIntVar(0, max_area, f"2A+_area_{pos}")
            area_vars[pos] = area_var
            board.register_variable_special(ID_AREA, pos, area_var)

        # 为每个连通块计算面积
        for seed_id in range(1, n + 1):
            # 该连通块的大小
            size_var = model.NewIntVar(0, n, f"2A+_size_{seed_id}")
            # 收集属于该连通块的位置
            member_vars = []
            for i, pos in enumerate(pos_list):
                # 该位置属于连通块 seed_id
                is_member = model.NewBoolVar(f"2A+_member_{pos}_{seed_id}")
                model.Add(component_ids[i] == seed_id).OnlyEnforceIf([is_member, s])
                model.Add(component_ids[i] != seed_id).OnlyEnforceIf([is_member.Not(), s])
                # 该位置必须是雷
                mine_var = board.get_variable(pos, special='raw')
                model.Add(is_member <= mine_var).OnlyEnforceIf(s)
                member_vars.append(is_member)
            model.Add(size_var == sum(member_vars)).OnlyEnforceIf(s)

            # 对于该连通块中的每个雷格，其 AREA 变量等于 size_var
            for i, pos in enumerate(pos_list):
                mine_var = board.get_variable(pos, special='raw')
                is_member = member_vars[i]
                area_var = area_vars[pos]
                # 如果该位置是雷且属于该连通块，则 area_var = size_var
                model.Add(area_var == size_var).OnlyEnforceIf([mine_var, is_member, s])

        # 4. 为每个线索格创建约束
        for pos, obj in board("C", mode="obj", special='raw'):
            if not isinstance(obj, Value2Ap):
                continue
            # 线索格本身必须是非雷
            mine_var = board.get_variable(pos, special='raw')
            if mine_var is not None:
                model.Add(mine_var == 0).OnlyEnforceIf(s)

            # 获取上下左右四个邻居的 AREA 变量
            neighbor_area_vars = []
            for neighbor in [pos.up(), pos.down(), pos.left(), pos.right()]:
                if board.in_bounds(neighbor):
                    area_var = board.get_variable(neighbor, special=ID_AREA)
                    if area_var is not None:
                        neighbor_area_vars.append(area_var)

            if neighbor_area_vars:
                model.Add(sum(neighbor_area_vars) == obj.count).OnlyEnforceIf(s)
                logger.trace(f"[2A+] {pos}: {obj.count} = sum({neighbor_area_vars})")

        if DEBUG:
            # 记录调试变量
            for pos, var in area_vars.items():
                self.debug_vars[f"area_{pos}"] = var
            for i, var in enumerate(component_ids):
                self.debug_vars[f"component_{pos_list[i]}"] = var


class Value2Ap(AbstractClueValue):
    """
    [2A+] 线索值类
    """
    id = Rule2Ap.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.pos = pos
        self.value = SingleIntValue(count)

    def __repr__(self) -> str:
        return str(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not isinstance(_data, dict) or not _data.get("_SingleIntValue", False):
            raise TypeError("Invalid value template for 2A+")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Failed to parse 2A+ clue value from JSON")
        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> List['Position']:
        """高亮显示上下左右四个邻居"""
        neighbors = [self.pos.up(), self.pos.down(), self.pos.left(), self.pos.right()]
        return [n for n in neighbors if board.in_bounds(n)]

    def invalid(self, board: 'Board') -> bool:
        """如果上下左右四个邻居都已确定（非'N'），则线索可验证"""
        neighbors = self.high_light(board)
        return board.batch(neighbors, mode="type", special='raw').count("N") == 0

    def create_constraints(self, board: 'Board', switch: Switch):
        """线索值约束已在 Rule2Ap 中统一构建，此处为空实现"""
        pass
