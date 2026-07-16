#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/17 00:57
# @Author  : Wu_RH
# @FileName: CG.py
from itertools import permutations
from typing import Self

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position import Position
from minesweepervariants.utils.image_template import Element
from minesweepervariants.utils.impl_obj import POSITION_TAG
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import MultiIntValue, Template

DEBUG = True
CG_NAME = "CG"


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


class RuleCG(AbstractClueRule):
    id = "CG"
    name = "Charge"
    name.zh_CN = "电荷"
    doc = ("Mines can have positive/negative/zero charge. Clues give counts of three types (order unknown). Total "
           "charge of each 4-connected mine region is zero.")
    doc.zh_CN = "雷可以带正负电或不带电，三个线索值表示周围八格三种雷的数量（顺序不确定），同一四联通雷区总电荷=0。"
    tags = ["Variant", "Local", "Mine-Value", "Connectivity", "Number Clue"]
    creation_time = "2026-04-30 00:13:13"
    author = ("NT", 2201963934)

    def __init__(self, board: "Board | None" = None, data: str | None = None):
        super().__init__(board, data)
        self.debug_vars = {}

    def fill(self, board: 'Board') -> 'Board':
        from minesweepervariants.impl.summon.solver import get_solver
        logger = get_logger()
        solver = get_solver()
        model = board.get_model().clone()
        for pos, var in board("N", mode="var"):
            model.add(var == 0)
        tmp_vars = []
        for pos, var in board("F", mode="var", special=CG_NAME):
            tmp_var = model.new_bool_var("")
            tmp_vars.append(tmp_var)
            model.add(var != 0).OnlyEnforceIf(tmp_var)
            model.add(var == 0).OnlyEnforceIf(tmp_var.Not())
        model.maximize(sum(tmp_vars))
        _ = solver.solve(model)
        cg_values = {}
        for pos, var in board(mode="var", special=CG_NAME):
            cg_value = solver.Value(var)
            cg_values[pos] = cg_value
        for pos, _ in board("N"):
            obj_values = {-1: 0, 0: 0, 1: 0}
            for _pos in pos.neighbors(2):
                if not board.is_valid(_pos):
                    continue
                if board.get_type(_pos) != "F":
                    continue
                obj_values[cg_values[_pos]] += 1
            logger.debug(f"[CG]{pos}: {obj_values}")
            obj = ValueCG(pos, list(obj_values.values()))
            board[pos] = obj
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        max_var = len([pos for pos, _ in board()])
        id_vars = {pos: model.new_int_var(0, max_var, f"id_{pos}") for pos, _ in board()}
        step_vars = {pos: model.new_int_var(0, max_var, f"step_{pos}") for pos, _ in board()}

        for pos, var in board(mode="var"):
            cg_var = model.new_int_var(-1, 1, f"{pos}_var_{CG_NAME}")
            board.register_variable_special(CG_NAME, pos, cg_var)
            model.add(cg_var == 0).only_enforce_if(var.Not())

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
            for pos, var in board(mode="var"):
                tmp_var = model.new_bool_var(f"{pos}={seed_id}")
                tmp_cg_var = model.new_int_var(-1, 1, f"{pos}={seed_id}")
                cg_var = board.get_variable(pos, special=CG_NAME)
                model.add(id_vars[pos] == seed_id).only_enforce_if(tmp_var)
                model.add(id_vars[pos] != seed_id).only_enforce_if(tmp_var.Not())
                model.add(tmp_cg_var == cg_var).only_enforce_if(tmp_var)
                model.add(tmp_cg_var == 0).only_enforce_if(tmp_var.Not())
                model.add(tmp_var == 0).only_enforce_if(var.Not())
                sum_vars.append(tmp_cg_var)
            model.add(count_var == sum(sum_vars))

        for var in count_vars.values():
            model.add(var == 0).only_enforce_if(s)

        if DEBUG:
            self.debug_vars.update({var.name: var for var in id_vars.values()})
            # self.debug_vars.update({var.name: var for var in count_vars.values()})
            self.debug_vars.update({var.name: var for var in step_vars.values()})
            self.debug_vars.update({var.name: var for _, var in board(mode="var", special=CG_NAME)})


class ValueCG(AbstractClueValue):
    id = RuleCG.id

    def __init__(self, pos: 'Position', value: list[int], *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        value = sorted(value)
        self.value: MultiIntValue = MultiIntValue(value)
        self.values = value
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'Template') -> Self:
        value_data = MultiIntValue.try_from(data)
        return cls(pos, value_data.value)

    def compose(self, board: 'Board') -> Element:
        return self.value.compose()

    def web_component(self, board: 'Board') -> Element:
        return self.value.web_component()

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        poses = self.pos.neighbors(2)
        cg_var_list = board.batch(poses, "var", drop_none=True, special=CG_NAME)
        var_list = board.batch(poses, "var", drop_none=True)

        # 统计正、负、零电荷的雷数（只统计是雷的格子）
        pos_bools = []  # 是雷 且 电荷 == 1
        neg_bools = []  # 是雷 且 电荷 == -1
        zero_bools = []  # 是雷 且 电荷 == 0

        for cg, v in zip(cg_var_list, var_list):
            # 正电荷雷：v == True 且 cg == 1
            p = model.new_bool_var('')
            model.add(cg == 1).only_enforce_if(p)
            model.add(v == 1).only_enforce_if(p)  # 假设 BoolVar 值为 1 表示真
            pos_bools.append(p)

            # 负电荷雷：v == True 且 cg == -1
            n = model.new_bool_var('')
            model.add(cg == -1).only_enforce_if(n)
            model.add(v == 1).only_enforce_if(n)
            neg_bools.append(n)

            # 零电荷雷：v == True 且 cg == 0
            z = model.new_bool_var('')
            model.add(cg == 0).only_enforce_if(z)
            model.add(v == 1).only_enforce_if(z)
            zero_bools.append(z)

            model.add(v == 0).only_enforce_if(
                z.Not(), n.Not(), p.Not()
            )

        count_pos = model.new_int_var(0, len(poses), 'count_pos')
        count_neg = model.new_int_var(0, len(poses), 'count_neg')
        count_zero = model.new_int_var(0, len(poses), 'count_zero')
        model.add(count_pos == sum(pos_bools))
        model.add(count_neg == sum(neg_bools))
        model.add(count_zero == sum(zero_bools))

        # 无序匹配 self.values
        allowed = list(set(permutations(self.values)))
        model.add_allowed_assignments([count_pos, count_neg, count_zero], allowed).only_enforce_if(s)
