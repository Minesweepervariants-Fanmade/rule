#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/24 19:40
# @Author  : Wu_RH
# @FileName: RL325.py
from typing import Dict

from ortools.sat.python.cp_model import IntVar, CpModel

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position import Position


class RuleRL325(AbstractMinesRule):
    id = "RL325"
    name = "RL325"
    name.zh_CN = "RL325"  # 或中文名
    doc = "四联通的雷区形状将会恰好组成数个3,2,5"
    doc.zh_CN = "四联通的雷区形状将会恰好组成数个3,2,5"
    author = ("雾", 3140864122)
    tags = ["Variant", "Global", "Connectivity", "Construction"]
    creation_time = "2026-08-24 06:42:37"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        self.debug_vars = {}

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        mines_type: Dict[Position, IntVar] = {
            pos: model.new_int_var(0, 3, f"TYPE[{pos}]")
            for pos, _ in board()
        }

        pos_type: Dict[Position, IntVar] = {
            pos: model.new_int_var(0, 8, f"POS[{pos}]")
            for pos, _ in board()
        }
        up_next_map: Dict[Position, IntVar] = {
            pos: model.new_int_var(2, 9, f"UP[{pos}]")
            for pos, _ in board()
        }
        left_next_map: Dict[Position, IntVar] = {
            pos: model.new_int_var(2, 9, f"LEFT[{pos}]")
            for pos, _ in board()
        }

        for pos, var in board(mode="var"):
            model.add(mines_type[pos] == 0).only_enforce_if(var.Not())
            model.add(mines_type[pos] > 0).only_enforce_if(var)

            self.__create_constraints_pos_type(
                board, model, pos, s, mines_type, pos_type
            )
            self.__create_constraints_pos(
                board, model, pos, s, mines_type, pos_type,
                up_next_map, left_next_map
            )

        self.debug_vars.update({var.name: var for var in mines_type.values()})
        self.debug_vars.update({var.name: var for var in pos_type.values()})
        self.debug_vars.update({var.name: var for var in up_next_map.values()})
        self.debug_vars.update({var.name: var for var in left_next_map.values()})

    def debug(self, solver):
        from ortools.sat.python.cp_model import CpSolver
        solver: CpSolver
        if not self.debug_vars:
            print("vars is empty")
        for key, var in self.debug_vars.items():
            print(key, solver.Value(var))

    def __create_constraints_pos_type(
        self, board: Board, model: CpModel,
        pos: Position, switch: IntVar,
        mines_type: Dict[Position, IntVar],
        pos_type: Dict[Position, IntVar]
    ):
        # 0 左,右 -
        # 1 上,下 |
        # 2 右端点 **O.
        # 3 左端点 .O**
        # 4 上,右 ▙
        # 5 下,右 ▛
        # 6 下,左 ▜
        # 7 上,左 ▟
        # 8 上左下 ┫
        nei1_pos = [pos.left(), pos.up(), pos.down(), pos.right()]
        nei1_var = board.batch(nei1_pos, drop_none=False, mode="var")
        pos_type_var = pos_type[pos]
        # [左, 上, 下, 右]
        pos_type_map = [
            (0, 1, 0, 0, 1),   # 0 左,右 -
            (1, 0, 1, 1, 0),   # 1 上,下 |
            (2, 1, 0, 0, 0),   # 2 右端点 --O
            (3, 0, 0, 0, 1),   # 3 左端点 O--
            (4, 0, 1, 0, 1),   # 4 上,右 ▙
            (5, 0, 0, 1, 1),   # 5 下,右 ▛
            (6, 1, 0, 1, 0),   # 6 下,左 ▜
            (7, 1, 1, 0, 0),   # 7 上,左 ▟
            (8, 1, 1, 1, 0),   # 8 上左下 ┫
        ]
        for type_val, *sides_val in pos_type_map:
            conds = []
            for index in range(4):
                if sides_val[index] == 1:
                    conds.append(None if nei1_var[index] is None else nei1_var[index].Not())
                else:
                    conds.append(0 if nei1_var[index] is None else nei1_var[index])
            if any(cond is None for cond in conds):
                model.add(pos_type_var != type_val).only_enforce_if(switch, board.get_variable(pos))
            else:
                for cond in conds:
                    model.add(pos_type_var != type_val).only_enforce_if(switch, cond, board.get_variable(pos))
        for side, side_var in zip(nei1_pos, nei1_var):
            if side_var is None:
                continue
            model.add(mines_type[pos] == mines_type[side]).only_enforce_if(switch, side_var, board.get_variable(pos))
            model.add(0 == mines_type[side]).only_enforce_if(switch, side_var.Not(), board.get_variable(pos))

    def __create_constraints_pos(
        self, board: Board, model: CpModel,
        pos: Position, switch: IntVar,
        mines_type: Dict[Position, IntVar],
        pos_type: Dict[Position, IntVar],
        up_next_map: Dict[Position, IntVar],
        left_next_map: Dict[Position, IntVar],
    ):
        # 0: 非雷
        # 1: 5
        # 2: 2
        # 3: 3
        self_pos_type = pos_type[pos]
        self_mines_type = mines_type[pos]
        self_up_next_type = up_next_map[pos]
        self_left_next_type = left_next_map[pos]

        self_pos_type_list = []
        for index in range(9):
            tmp_var = model.new_bool_var("")
            model.add(self_pos_type == index).only_enforce_if(tmp_var)
            model.add(self_pos_type != index).only_enforce_if(tmp_var.Not())
            self_pos_type_list.append(tmp_var)

        self_mines_is_3 = model.new_bool_var("")
        self_mines_is_2 = model.new_bool_var("")
        self_mines_is_5 = model.new_bool_var("")
        model.add(self_mines_type == 2).only_enforce_if(self_mines_is_2)
        model.add(self_mines_type != 2).only_enforce_if(self_mines_is_2.Not())
        model.add(self_mines_type == 3).only_enforce_if(self_mines_is_3)
        model.add(self_mines_type != 3).only_enforce_if(self_mines_is_3.Not())
        model.add(self_mines_type == 1).only_enforce_if(self_mines_is_5)
        model.add(self_mines_type != 1).only_enforce_if(self_mines_is_5.Not())

        before_up_type = up_next_map[pos.down()] if board.is_valid(pos.down()) else None
        before_left_type = left_next_map[pos.right()] if board.is_valid(pos.right()) else None

        if before_left_type is None:
            model.add(self_pos_type != 0).only_enforce_if(switch)
        else:
            model.add(
                self_left_next_type == before_left_type
            ).only_enforce_if(self_pos_type_list[0], switch)
            model.add(
                self_pos_type == before_left_type
            ).only_enforce_if(
                self_pos_type_list[1].Not(),
                self_pos_type_list[0].Not(), switch
            )

        if before_up_type is None:
            model.add(self_pos_type != 1).only_enforce_if(switch)
        else:
            model.add(
                self_up_next_type == before_up_type
            ).only_enforce_if(self_pos_type_list[1], switch)
            model.add(
                self_pos_type == before_up_type
            ).only_enforce_if(
                self_pos_type_list[1].Not(),
                self_pos_type_list[0].Not(), switch
            )


        # 0 左,右 -
        # 1 上,下 |
        # 2 右端点 **O.
        # 3 左端点 .O**
        # 4 上,右 ▙
        # 5 下,右 ▛
        # 6 下,左 ▜
        # 7 上,左 ▟
        # 8 上左下 ┫
        model.add_bool_and(
            [self_pos_type_list[index].Not()
             for index in [2, 4, 5]]
        ).only_enforce_if(self_mines_is_3, switch)
        model.add_bool_and(
            self_pos_type_list[8].Not()
        ).only_enforce_if(self_mines_is_2, switch)
        model.add_bool_and(
            self_pos_type_list[8].Not()
        ).only_enforce_if(self_mines_is_5, switch)

        # 3
        model.add(self_left_next_type == 3).only_enforce_if(
            self_mines_is_3, self_pos_type_list[8], switch
        )
        model.add(self_up_next_type == 6).only_enforce_if(
            self_mines_is_3, self_pos_type_list[8], switch
        )
        model.add(self_left_next_type == 3).only_enforce_if(
            self_mines_is_3, self_pos_type_list[6], switch
        )
        model.add(self_up_next_type == 8).only_enforce_if(
            self_mines_is_3, self_pos_type_list[7], switch
        )
        model.add(self_left_next_type == 3).only_enforce_if(
            self_mines_is_3, self_pos_type_list[7], switch
        )

        # 2
        model.add(self_left_next_type == 3).only_enforce_if(
            self_mines_is_2, self_pos_type_list[6], switch
        )
        model.add(self_up_next_type == 6).only_enforce_if(
            self_mines_is_2, self_pos_type_list[7], switch
        )
        model.add(self_left_next_type == 5).only_enforce_if(
            self_mines_is_2, self_pos_type_list[7], switch
        )
        model.add(self_left_next_type == 4).only_enforce_if(
            self_mines_is_2, self_pos_type_list[2], switch
        )
        model.add(self_up_next_type == 5).only_enforce_if(
            self_mines_is_2, self_pos_type_list[4], switch
        )

        # 5
        model.add(self_left_next_type == 5).only_enforce_if(
            self_mines_is_5, self_pos_type_list[2], switch
        )
        model.add(self_left_next_type == 4).only_enforce_if(
            self_mines_is_5, self_pos_type_list[6], switch
        )
        model.add(self_left_next_type == 3).only_enforce_if(
            self_mines_is_5, self_pos_type_list[7], switch
        )
        model.add(self_up_next_type == 6).only_enforce_if(
            self_mines_is_5, self_pos_type_list[7], switch
        )
        model.add(self_up_next_type == 5).only_enforce_if(
            self_mines_is_5, self_pos_type_list[4], switch
        )
