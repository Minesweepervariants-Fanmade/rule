#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/12 19:40
# @Author  : Wu_RH
# @FileName: 2Z'.py
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import POSITION_TAG

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


class Rule2Zp(AbstractMinesRule):
    id = "2Z'"
    name = "Zero-Sum'"
    name.zh_CN = "零和雷组"
    doc = "For all 4-connected mine regions, the Gray number of dyed cells equals that of undyed cells."
    doc.zh_CN = "所有四连通的雷区域染色格雷数与非染色格雷数相同"

    tags = ["Global", "Connectivity", "Dyed"]
    creation_time = "2026-06-08 21:02:23"
    author = ("mabopei1", 81500378)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        self.debug_vars = {}

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

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

        for seed_id in range(1, max_var + 1):
            dye_sum_vars = []
            undye_sum_vars = []
            for pos, dye in board(mode="dye"):
                tmp_var = model.new_bool_var(f"{pos}={seed_id}")
                model.add(id_vars[pos] == seed_id).only_enforce_if(tmp_var)
                model.add(id_vars[pos] != seed_id).only_enforce_if(tmp_var.Not())
                if dye:
                    dye_sum_vars.append(tmp_var)
                else:
                    undye_sum_vars.append(tmp_var)
            model.add(sum(undye_sum_vars) == sum(dye_sum_vars))
