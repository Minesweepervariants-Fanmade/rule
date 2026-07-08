#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[RS'] RedStone Prime: 雷视为红石线，非雷视为实体方块，线索表示与该格连接的红石总格数
使用规则2A修改角格约束：线索值为四方向相邻雷区域的面积之和
"""

from typing import List, cast

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.impl_obj import POSITION_TAG
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template

logger = get_logger(__name__)
DEBUG = True
RS_ID = "RS'_ID"
RS_COUNT = "RS'_COUNT"


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


class RuleRSPrime(AbstractClueRule):
    id = "RS'"
    name = "RedStone Prime"
    name.zh_CN = "红石'"
    doc = ("Mines are redstone wires, clues are solid blocks, clue shows total number of redstone cells connected to "
           "this cell")
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

        max_var = len([pos for pos, _ in board()])
        id_vars = {pos: model.new_int_var(0, max_var, f"id_{pos}") for pos, _ in board()}
        step_vars = {pos: model.new_int_var(0, max_var, f"step_{pos}") for pos, _ in board()}

        for pos, _ in board():
            pos_var = board.get_variable(pos)
            is_root = model.new_bool_var(f"{pos}_is_root")
            nei1_poses = [nei_pos for nei_pos in pos.neighbors(1, 1) if nei_pos in id_vars]
            for nei_pos in nei1_poses:
                # 相邻两格必须id相同
                model.add(id_vars[nei_pos] == id_vars[pos]).OnlyEnforceIf(
                    board.get_variable(pos), board.get_variable(nei_pos)
                )

            # 如果该格是雷
            model.add(id_vars[pos] > 0).only_enforce_if(pos_var)
            model.add(step_vars[pos] > 0).only_enforce_if(pos_var)
            model.add(pos_var == 1).only_enforce_if(is_root)

            # 该格是雷且是root
            model.add(step_vars[pos] == max_var).only_enforce_if(pos_var, is_root)
            model.add(id_vars[pos] == pos2seed(pos, board)).only_enforce_if(pos_var, is_root)

            # 该格是雷且不是root
            model.add(id_vars[pos] > pos2seed(pos, board)).only_enforce_if(pos_var, is_root.Not())

            # 取周围最大的step-1
            model.add_max_equality(
                step_vars[pos],
                [step_vars[nei_pos] - 1 for nei_pos in nei1_poses],
            ).OnlyEnforceIf(pos_var, is_root.Not())
            for nei_pos in nei1_poses:
                tmp_var = model.new_bool_var("")
                model.add(step_vars[pos] == step_vars[nei_pos] - 1).OnlyEnforceIf(tmp_var)
                model.add(step_vars[pos] != step_vars[nei_pos] - 1).OnlyEnforceIf(tmp_var.Not())
                model.add(id_vars[pos] == id_vars[nei_pos]).only_enforce_if(pos_var, tmp_var, is_root.Not())

            # 如果该格非雷
            model.add(id_vars[pos] == 0).only_enforce_if(pos_var.Not())
            model.add(step_vars[pos] == 0).only_enforce_if(pos_var.Not())
            model.add(is_root == 0).only_enforce_if(pos_var.Not())
            if DEBUG:
                self.debug_vars[is_root.name] = is_root

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

        if DEBUG:
            self.debug_vars.update({var.name: var for var in id_vars.values()})
            self.debug_vars.update({var.name: var for var in count_vars.values()})
            self.debug_vars.update({var.name: var for var in step_vars.values()})

        for pos, var in id_vars.items():
            board.register_variable_special(RS_ID, pos, var)

        for seed, var in count_vars.items():
            board.register_variable_special(RS_COUNT, seed2pos(seed, board), var)

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
        if not self.debug_vars:
            print("vars is empty")
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
        directions = self.pos.neighbors(1, 1)
        cond_directions = self.pos.neighbors(2, 2)

        for start in directions:
            if not board.in_bounds(start):
                continue
            if board.get_type(start) == 'C':
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

            while stack:
                current = stack.pop()
                positions.append(current)
                if board.get_type(current) != 'F':
                    continue
                # 四方向扩展
                for neighbor in current.neighbors(1, 1):
                    if not board.in_bounds(neighbor):
                        continue
                    if board.get_type(neighbor) == 'C':
                        continue
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    stack.append(neighbor)
        return positions

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        nei1_pos = [_pos for _pos in self.pos.neighbors(1, 1) if board.is_valid(_pos)]
        nei2_pos = [_pos for _pos in self.pos.neighbors(2, 2) if board.is_valid(_pos)]
        max_var = len([pos for pos, _ in board()])

        nei1_ids = {k: v for k, v in zip(nei1_pos, board.batch(nei1_pos, mode="var", special=RS_ID))}
        nei2_vars = {k: v for k, v in zip(nei2_pos, board.batch(nei2_pos, mode="var"))}
        count_vars = {pos2seed(pos, board): board.get_variable(pos, special=RS_COUNT) for pos, _ in board()}

        id_vars = {}
        for pos, id_var in nei1_ids.items():
            conds = [nei2_vars[_pos].Not() for _pos in pos.neighbors(1, 1) if _pos in nei2_vars]
            tmp_var = model.new_int_var(0, max_var, "")
            id_vars[f"{self.pos}>{pos}_id"] = tmp_var
            model.add(id_var == tmp_var).only_enforce_if(conds + [s])
            for cond in conds:
                model.add(tmp_var == 0).only_enforce_if(cond.Not(), s)

        sum_vars = {}
        for id_num, count_var in count_vars.items():
            nei1_count_var = model.new_int_var(0, count_var.domain.max(), "")
            eq_vars = []
            for nei1_id in id_vars.values():
                ueq_var = model.NewBoolVar(f'{self.pos}_{id_num}={nei1_id}')
                model.add(nei1_id == id_num).only_enforce_if(ueq_var.Not(), s)
                model.add(nei1_id != id_num).only_enforce_if(ueq_var, s)
                eq_vars.append(ueq_var)
                model.add(nei1_count_var == count_var).only_enforce_if(ueq_var.Not(), s)
            model.add(nei1_count_var == 0).only_enforce_if(eq_vars + [s])
            sum_vars[f"{self.pos}_sum_at_{id_num}"] = nei1_count_var

        if not sum_vars:
            raise ValueError("RS'传进来个棍木")

        cond_var = model.new_int_var(0, max_var, "")
        model.add(cond_var == sum(sum_vars.values()))
        if DEBUG:
            self.debug_vars[f"{self.pos}_result_var"] = cond_var
            self.debug_vars.update(sum_vars)
            self.debug_vars.update(id_vars)
        # else:
        model.add(sum(sum_vars.values()) == self.value.value).only_enforce_if(s)

    def debug(self, solver):
        from ortools.sat.python.cp_model import CpSolver
        solver: CpSolver
        if not self.debug_vars:
            print("vars is empty")
        for key, var in self.debug_vars.items():
            print(key, solver.Value(var))
