#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/19 20:34
# @Author  : Wu_RH
# @FileName: 2D.py
"""
[2D]偏移: 线索表示上方一格为中心的3x3区域内的总雷数
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

from ....utils.tool import get_logger


def get_pos_box(board: AbstractBoard, top_left: AbstractPosition, bottom_right: AbstractPosition) -> list[AbstractPosition]:
        positions = []
        for x in range(top_left.x, bottom_right.x + 1):
            for y in range(top_left.y, bottom_right.y + 1):
                pos = board.get_pos(x, y, top_left.board_key)
                if pos is not None:
                    positions.append(pos)
        return positions

class Rule2D(AbstractClueRule):
    name = ["2D^", "偏移^", "Deviation^"]
    doc = "线索表示以 Nx3 范围内的雷数，N 为正上连续非雷格数量"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            upwards = 0
            upPos = pos.up()
            while board.in_bounds(upPos) and board.get_type(upPos) != "F":
                upwards += 1
                upPos = upPos.up()
            value = board.batch(get_pos_box(board, pos.left().up(upwards), pos.right()), mode="type").count("F")  # 计算 Nx3 范围内的雷数
            board.set_value(pos, Value2D(pos, count=value))
        return board


class Value2D(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count

    def __repr__(self):
        return f"{self.count}"

    @classmethod
    def type(cls) -> bytes:
        return Rule2D.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def create_constraints(self, board: AbstractBoard, switch):
        def collect_side_vars(board: AbstractBoard, pos: AbstractPosition, step: int, cont_var, switch):
            for i, _pos in enumerate([pos.left(), pos.right()]):
                if not board.in_bounds(_pos):
                    model.Add(collect_vars[step * 2 + i] == 0).OnlyEnforceIf(switch)
                else:
                    model.Add(collect_vars[step * 2 + i] == board.get_variable(_pos)).OnlyEnforceIf([cont_var, switch])
                    model.Add(collect_vars[step * 2 + i] == 0).OnlyEnforceIf([cont_var.Not(), switch])
                
        model = board.get_model()
        s = switch.get(model, self)

        curr = self.pos
        
        upwards = 0
        while board.in_bounds(curr):
            upwards += 1
            curr = curr.up()

        collect_vars = [model.NewBoolVar(f"2D^_collect_{i}_{self.pos}") for i in range(upwards * 2)]

        curr = self.pos
        prev_cont_var = model.NewConstant(1)

        step = 0
        while board.in_bounds(curr):
            cont_var = model.NewBoolVar(f"cont_{curr}_{self.pos}")
            model.Add(cont_var == 1).OnlyEnforceIf([prev_cont_var, board.get_variable(curr).Not(), s])
            model.Add(cont_var == 0).OnlyEnforceIf([prev_cont_var.Not(), s])
            model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), s])
            collect_side_vars(board, curr, step, cont_var, s)
            prev_cont_var = cont_var
            curr = curr.up()
            step += 1

        model.Add(sum(collect_vars) == self.count).OnlyEnforceIf(s)