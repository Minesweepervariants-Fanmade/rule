#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/09 11:37
# @Author  : xxx
# @FileName: 3Ap.py
from itertools import product
from typing import List, Dict, Set, Tuple, Optional, Self

from ortools.sat.python.cp_model import IntVar

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from ....utils.impl_obj import MINES_TAG, VALUE_QUESS


def put(board, pos: 'Position', path):
    value = 0
    while board.in_bounds(pos):
        value += 1
        if board.get_type(pos) == "F":
            path += 1
            path %= 4
        else:
            obj = board.get_value(pos)
            obj: Value3Ap
            obj.append(value)
            path += 3
            path %= 4
        # 0.上 1.右 2.下 3.左
        match path:
            case 0:
                pos = pos.down()
            case 1:
                pos = pos.left()
            case 2:
                pos = pos.up()
            case 3:
                pos = pos.right()


class Rule3Ap(AbstractClueRule):
    id = "3A^"
    name = "Langton's Ant - XOR"
    name.zh_CN = "兰顿蚂蚁·异或"
    doc = "XOR the results of Langton's Ant [3A] in four directions; if the result is infinite, display using complement form"
    doc.zh_CN = "将兰顿蚂蚁[3A]四个方向的结果做异或操作 若结果为无穷大则使用补码形式显示"
    author = ("雾", 3140864122)
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial", "Cryptic"]
    creation_time = "2026-04-19"

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            board.set_value(pos, Value3Ap(pos))
        lines = [
            board.get_row_pos(board.get_pos(0, 0)),
            board.get_col_pos(board.get_pos(-1, -1)),
            board.get_row_pos(board.get_pos(-1, -1)),
            board.get_col_pos(board.get_pos(0, 0)),
        ]
        for index in range(4):
            line = lines[index]
            for pos in line:
                put(board, pos, index)
                # print(pos, index)
                # print(board.show_board())
        for _, obj in board("C", mode="obj"):
            obj: Value3Ap
            obj.end()
        return board


class Value3Ap(AbstractClueValue):
    id = Rule3Ap.id

    def __init__(self, pos: 'Position', value: Optional[int] = None):
        super().__init__(pos)
        self.count = value
        self.data = []

    def __repr__(self):
        return str(self.count)

    def high_light(self, board: 'Board') -> List['Position']:
        pos = self.pos.clone()
        position = []
        for path_dir in range(4):
            path = path_dir
            while True:
                if not board.in_bounds(pos):
                    break
                if board.get_type(pos) == "N":
                    position.append(pos)
                    break
                if pos in position:
                    break
                position.append(pos)
                # 0.上 1.右 2.下 3.左
                if board.get_type(pos) == "F":
                    path += 3
                    path %= 4
                else:
                    path += 1
                    path %= 4
                match path:
                    case 0:
                        pos = pos.down()
                    case 1:
                        pos = pos.left()
                    case 2:
                        pos = pos.up()
                    case 3:
                        pos = pos.right()
                if (
                    pos == self.pos and
                    path == (path_dir + 1) % 4
                ):
                    break
        return position

    def append(self, data):
        self.data.append(data)

    def end(self):
        self.data: list[int]
        self.data += [-1] * (4 - len(self.data))

        # 提取所有首个int值
        self.count = (self.data[0] ^ self.data[1]) ^ (self.data[2] ^ self.data[3])
        # get_logger().debug(f"[3A^] {self.pos} {self.data},value {self.count}")

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError()

        return cls(pos, value=value.value)

    def json(self) -> 'JSONObject':
        return SingleIntValue(self.count).json()

    def _enumerate_direction(
        self, board: 'Board',
        pos_main: 'Position', init_dir: int,
        direction: int, steps: int,
        constraints: Dict['Position', int],
        visited: Set[Tuple['Position', int]],
        result: Dict[int, List[IntVar]],
        all_switch: IntVar
    ):
        visited.add((pos_main, direction))
        pos = self._move(pos_main, direction)

        if pos in [i[0] for i in visited]:  # 循环
            if board.get_type(pos) == "C":
                new_dir = (direction + 1) % 4
            elif board.get_type(pos) == "F":
                new_dir = (direction + 3) % 4
            else:
                new_dir = (direction + 1 + 2 * constraints[pos]) % 4
            if (pos, new_dir) in visited:
                model = board.get_model()
                cond = model.NewBoolVar(f"[3A^]{self.pos}_{init_dir}_-1")
                if -1 not in result:
                    result[-1] = []
                result[-1].append(cond)
                _board = board.clone()
                for pos, val in constraints.items():
                    model.Add(board.get_variable(pos) == val).OnlyEnforceIf(cond, all_switch)
                    _board.set_value(pos, MINES_TAG if val else VALUE_QUESS)
                return

        if not board.in_bounds(pos):    # 出界
            _board = board.clone()
            model = board.get_model()
            cond = model.NewBoolVar(f"[3A^]{self.pos}_{init_dir}_{steps}")
            if steps not in result:
                result[steps] = []
            result[steps].append(cond)
            for pos, val in constraints.items():
                model.Add(board.get_variable(pos) == val).OnlyEnforceIf(cond, all_switch)
                _board.set_value(pos, MINES_TAG if val else VALUE_QUESS)
            return

        cell_type = board.get_type(pos, special='raw')
        if cell_type == "F" or constraints.get(pos, -1) == 1:
            # 雷：左转
            new_dir = (direction + 3) % 4
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir, steps + 1,
                constraints, visited, result,
                all_switch
            )
        elif cell_type == "C" or constraints.get(pos, -1) == 0:
            # 线索格（视为非雷）：右转
            new_dir = (direction + 1) % 4
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir, steps + 1,
                constraints, visited, result,
                all_switch
            )
        else:  # "N"
            # 分支1：假设为雷
            cons_mine = constraints.copy()
            cons_mine[pos] = 1
            new_dir_mine = (direction + 3) % 4
            new_visited = visited.copy()
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir_mine, steps + 1,
                cons_mine, new_visited, result,
                all_switch
            )

            # 分支2：假设为非雷
            cons_non = constraints.copy()
            cons_non[pos] = 0
            new_dir_non = (direction + 1) % 4
            new_visited = visited.copy()
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir_non, steps + 1,
                cons_non, new_visited, result,
                all_switch
            )

    def _move(self, pos, direction) -> 'Position':
        if direction == 0:
            return pos.up()
        elif direction == 1:
            return pos.right()
        elif direction == 2:
            return pos.down()
        else:  # direction == 3
            return pos.left()

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        result: dict[int, dict[int, list[IntVar]]] = dict()
        for dir_path in range(4):
            result[dir_path] = {}
            self._enumerate_direction(
                board, self.pos, dir_path,
                dir_path, 1,
                dict(), set(), result[dir_path],
                s
            )
            # model.AddBoolOr([cond for conds in result[dir_path].values() for cond in conds]).OnlyEnforceIf(s)

        # 枚举所有步数组合，直接生成总变量
        steps_lists = [list(result[d].keys()) for d in range(4)]
        combo_vars = []
        for combo in product(*steps_lists):
            a, b, c, d = combo
            if ((a ^ b) ^ (c ^ d)) != self.count:
                continue
            combo_var = model.NewBoolVar(f"combo_{self.pos}_{a}_{b}_{c}_{d}")
            for idx, step in enumerate(combo):
                model.AddBoolOr(result[idx][step]).OnlyEnforceIf([combo_var, s])
            combo_vars.append(combo_var)
        model.AddBoolOr(combo_vars).OnlyEnforceIf(s)
