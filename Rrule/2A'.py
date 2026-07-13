#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 2A.py
"""
[2A']面积: 线索表示它所在的四连通非雷区的面积。
(注:如果出现大数字则速率极度底下)
"""
import itertools
import time
from typing import List, Tuple, Optional, Self

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractRule
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import VALUE_QUESS, POSITION_TAG
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.utils.value_template import Template, SingleIntValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger

ID_2A = "ID_2A'"
COUNT_2A = "COUNT_2A'"
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


class Rule2A(AbstractClueRule):
    id = "2A'"
    name = "Area'"
    name.zh_CN = "面积'"
    doc = "Clue shows the area of its 4-connected non-mine region"
    doc.zh_CN = "线索表示它所在的四连通非雷区的面积。"
    tags = ["Local", "Number Clue", "Extensive Trial", "Creative"]
    creation_time = "2025-08-17"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None):
        super().__init__(board, data)
        self.debug_vars = {}
        self.flag = None

    def combine(self, rules: List[Tuple['AbstractRule', Optional[str]]]):
        """
        合并规则：
        - 如果存在 (rule, data)，其中 rule 的 name 是 '1S'
        - 并且 data 满足以下之一：
            * None
            * "1"
            * "1;1;...;1"（由一个或多个 '1' 组成，中间以分号分隔）
        则将 self.flag_1S 设为 True。
        """
        for rule, data in rules:
            name = getattr(rule, "name", None)
            if isinstance(name, list):
                name = name[0] if name else None

            if (name in ["1D'", "1O"] and
               (data is None or all(x == "1" or "1:1" in x for x in data.split(";")))):
                self.flag = True

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for key in board.get_interactive_keys():
            size = board.get_config(key, "size")
            for pos, _ in board("N", key=key):
                if self.flag:
                    board[pos] = VALUE_QUESS
                    continue
                checked = [[False for _ in range(size[0])] for _ in range(size[1])]

                def dfs(p: 'Position', _checked):
                    if not board.in_bounds(p): return None
                    if board.get_type(p) == "F": return None
                    if _checked[p.x][p.y]: return None
                    _checked[p.x][p.y] = True
                    dfs(p.left(1), _checked)
                    dfs(p.right(1), _checked)
                    dfs(p.up(1), _checked)
                    dfs(p.down(1), _checked)
                    return None

                checked[pos.x][pos.y] = True
                dfs(pos.left(1), checked)
                dfs(pos.right(1), checked)
                dfs(pos.up(1), checked)
                dfs(pos.down(1), checked)
                cnt = 0
                for i in range(size[0]):
                    for j in range(size[1]):
                        if checked[i][j]:
                            cnt += 1
                board.set_value(pos, Value2A(pos, cnt))
                logger.debug(f"Set {pos} to 2A'[{cnt}]")
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()

        max_var = len([pos for pos, _ in board()])
        id_vars = {pos: model.new_int_var(0, max_var, f"id_{pos}") for pos, _ in board()}
        step_vars = {pos: model.new_int_var(0, max_var, f"step_{pos}") for pos, _ in board()}

        for pos, _ in board():
            pos_var = board.get_variable(pos).Not()
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
            board.register_variable_special(ID_2A, pos, var)

        for seed, var in count_vars.items():
            board.register_variable_special(COUNT_2A, seed2pos(seed, board), var)


class Value2A(AbstractClueValue):
    id = Rule2A.id

    def __init__(self, pos: 'Position', value: int):
        super().__init__(pos)
        self.debug_vars = {}
        self.value: SingleIntValue = SingleIntValue(value)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'Template') -> Self:
        value_data = SingleIntValue.try_from(data)
        return cls(pos, value_data.value)

    def create_constraints(self, board: 'Board', switch):
        # 跳过已有的线索格
        model = board.get_model()
        s = switch.get(model, self)

        id_var: IntVar = board.get_variable(self.pos, special=ID_2A)
        count_vars = {pos2seed(pos, board): board.get_variable(pos, special=COUNT_2A) for pos, _ in board()}

        all_count_var = model.new_int_var(id_var.domain.min(), id_var.domain.max(), f"{self.pos} id count")
        for id_num, count_var in count_vars.items():
            eq_var = model.NewBoolVar(f'{self.pos}_{id_num}={id_var}')
            model.add(id_var != id_num).only_enforce_if(eq_var.Not(), s)
            model.add(id_var == id_num).only_enforce_if(eq_var, s)
            model.add(all_count_var == count_var).only_enforce_if(eq_var, s)

        model.add(all_count_var == self.value.value).only_enforce_if(s)

