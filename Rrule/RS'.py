#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[RS'] RedStone Prime: 雷视为红石线，非雷视为实体方块，线索表示与该格连接的红石总格数
使用规则2A修改角格约束：线索值为四方向相邻雷区域的面积之和
"""

from typing import List, Tuple, Optional, cast, Dict

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template

logger = get_logger(__name__)
DEBUG = False


class RuleRSPrime(AbstractClueRule):
    id = "RS'"
    name = "RedStone Prime"
    name.zh_CN = "红石'"
    doc = "Mines are redstone wires, clues are solid blocks, clue shows total number of redstone cells connected to this cell"
    doc.zh_CN = "雷视为红石线，线索视为实体方块，线索表示与该格连接的红石总格数"
    author = ("NT", 2201963934)
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial", "Weak"]
    creation_time = "2026-07-06"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        self.debug_vars = {}

    def fill(self, board: 'Board') -> 'Board':
        """
        为所有未定义格设置线索值：
        线索值 = 四方向相邻雷区域的面积之和
        """
        for pos, _ in board("N"):
            count = self._compute_area_sum(board, pos)
            board.set_value(pos, ValueRSPrime(pos, count))
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        clue_map = {}
        for pos, clue in board(mode="obj"):
            if not isinstance(clue, ValueRSPrime):
                continue
            clue_map[pos] = clue
        if not clue_map:
            return

        def pos2seed(input_pos: Position, bound: Position):
            return input_pos.row * (bound.col + 1) + input_pos.col + 1

        pos_bound = board.boundary()
        max_var = len([pos for pos, _ in board()])
        id_vars = {pos: model.new_int_var(0, max_var, f"id_{pos}") for pos, _ in board()}
        for pos, _ in board():
            model.add_max_equality(
                id_vars[pos], [
                    id_vars[nei_pos] for nei_pos in pos.neighbors(1, 1)
                    if nei_pos in id_vars
                ] + [pos2seed(pos, pos_bound)]
            ).OnlyEnforceIf(board.get_variable(pos))
            model.add(id_vars[pos] == 0).OnlyEnforceIf(board.get_variable(pos).Not())
        count_vars = {}
        for seed_id in range(1, max_var + 1):
            count_var = model.new_int_var(0, max_var, f"id{seed_id}Cound")
            count_vars[seed_id] = count_var
            sum_vars = []
            for pos, _ in board():
                tmp_var = model.new_bool_var(f"{pos}={seed_id}")
                model.add(id_vars[pos] == seed_id).only_enforce_if(tmp_var)
                model.add(id_vars[pos] != seed_id).only_enforce_if(tmp_var.Not())
                sum_vars.append(tmp_var)
            model.add(count_var == sum(sum_vars))

        for pos, clue in clue_map.items():
            nei1 = [_pos for _pos in pos.neighbors(1, 1) if board.is_valid(_pos)]
            nei2 = [_pos for _pos in pos.neighbors(2, 2) if board.is_valid(_pos)]
            clue.create_constraints_rs(
                board, {_pos: id_vars[_pos] for _pos in nei1},
                {_pos: board.get_variable(_pos) for _pos in nei2},
                count_vars, switch
            )

        self.debug_vars = {var.name: var for var in id_vars.values()}
        self.debug_vars.update({var.name: var for var in count_vars.values()})

    @staticmethod
    def _compute_area_sum(board, pos):
        """
        计算与pos格四方向相邻的所有雷组的面积之和。
        使用DFS遍历四个方向的雷组。
        """
        # 使用一个集合来跟踪已访问的雷格，避免重复计算
        visited = set()
        total = 0

        # 四个方向：左、右、上、下
        directions = pos.neighbors(1, 1)
        cond_directions = pos.neighbors(2, 2)

        for start in directions:
            if not board.in_bounds(start):
                continue
            if board.get_type(start) != 'F':
                continue
            if start in visited:
                continue
            if [
                board.get_type(pos)
                for pos in start.neighbors(1, 1)
                if pos in cond_directions
            ].count("F"):
                continue

            # BFS/DFS遍历该雷组
            stack = [start]
            visited.add(start)
            area = 0

            while stack:
                current = stack.pop()
                area += 1
                # 四方向扩展
                for neighbor in [current.up(1), current.down(1), current.left(1), current.right(1)]:
                    if not board.in_bounds(neighbor):
                        continue
                    if board.get_type(neighbor) != 'F':
                        continue
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    stack.append(neighbor)

            total += area

        return total

    def debug(self, solver):
        from ortools.sat.python.cp_model import CpSolver
        solver: CpSolver
        for key, var in self.debug_vars.items():
            print(key, solver.Value(var))


class ValueRSPrime(AbstractClueValue):
    id = RuleRSPrime.id

    def __init__(self, pos: Position, value: int, *args, **kwargs):
        super().__init__(pos, value, *args, **kwargs)
        self.pos = pos
        self.value: SingleIntValue = SingleIntValue(value)
        self.debug_vars = {}

    @classmethod
    def from_json(cls, pos: Position, data):
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        value_obj = SingleIntValue.try_from(template_data)
        if value_obj is None:
            raise ValueError("value is empty")
        return cls(pos, value_obj.value)

    def high_light(self, board: 'Board') -> List['Position'] | None:
        """
        高亮与线索格四方向相邻的所有雷组。
        """
        visited = set()
        positions = []

        # 四个方向：左、右、上、下
        directions = [self.pos.left(1), self.pos.right(1), self.pos.up(1), self.pos.down(1)]

        for start in directions:
            if not board.in_bounds(start):
                continue
            if board.get_type(start) != 'F':
                continue
            if start in visited:
                continue

            # BFS/DFS遍历该雷组
            stack = [start]
            visited.add(start)

            while stack:
                current = stack.pop()
                positions.append(current)
                # 四方向扩展
                for neighbor in [current.up(1), current.down(1), current.left(1), current.right(1)]:
                    if not board.in_bounds(neighbor):
                        continue
                    if board.get_type(neighbor) != 'F':
                        continue
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    stack.append(neighbor)

        return positions if positions else None

    def create_constraints_rs(
        self, board: 'Board',
        nei1_ids: Dict[Position, IntVar],
        nei2_vars: Dict[Position, IntVar],
        count_vars: Dict[int, IntVar],
        switch: "Switch",
    ):
        model = board.get_model()
        s = switch.get(model, self)

        id_vars = []
        for pos, id_var in nei1_ids.items():
            conds = [nei2_vars[_pos].Not() for _pos in pos.neighbors(1, 1) if _pos in nei2_vars]
            tmp_var = model.new_int_var(0, id_var.domain.max(), "")
            id_vars.append(tmp_var)
            model.add(id_var == tmp_var).only_enforce_if(conds + [s])
            for cond in conds:
                model.add(tmp_var == 0).only_enforce_if(cond.Not(), s)

        sum_vars = []
        for id_num, count_var in count_vars.items():
            nei1_count_var = model.new_int_var(0, count_var.domain.max(), "")
            ueq_vars = []
            for nei1_id in id_vars:
                eq_var = model.NewBoolVar('')
                model.add(nei1_id == id_num).only_enforce_if(eq_var, s)
                model.add(nei1_id != id_num).only_enforce_if(eq_var.Not(), s)
                ueq_vars.append(eq_var.Not())
                model.add(nei1_count_var == count_var).only_enforce_if(eq_var, s)
            model.add(nei1_count_var == 0).only_enforce_if(ueq_vars + [s])
            sum_vars.append(nei1_count_var)

        if not sum_vars:
            raise ValueError("RS'传进来个棍木")

        if DEBUG:
            cond_var = model.new_int_var(0, sum_vars[0].domain.max(), "")
            model.add(cond_var == sum(sum_vars))
            self.debug_vars["result_var"] = cond_var
        else:
            model.add(sum(sum_vars) == self.value.value).only_enforce_if(s)

    def debug(self, solver):
        from ortools.sat.python.cp_model import CpSolver
        solver: CpSolver
        for key, var in self.debug_vars.items():
            print(key, solver.Value(var))