#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/04 16:36
# @Author  : Wu_RH
# @FileName: LO.py

from typing import TYPE_CHECKING, Dict, Tuple, Optional, List

from ortools.sat.python import cp_model

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.Mrule import AbstractMinesValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.summon import GenerateError
from minesweepervariants.utils.impl_obj import VALUE_CROSS, VALUE_CIRCLE
from minesweepervariants.utils.tool import get_logger

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


def solver_lightsOut(
    game_state: Dict[Position, bool],
    board: Board
) -> Tuple[
    Optional[cp_model.CpModel],
    Optional[cp_model.CpSolver],
    Dict[Position, cp_model.IntVar]
]:
    model = cp_model.CpModel()
    # 为每个位置创建一个布尔变量，表示是否按下该按钮
    switch_vars = {pos: model.NewBoolVar(f"switch_{pos}") for pos in game_state}

    for pos, init in game_state.items():
        # 收集自身及四个方向上有效邻居的变量
        neighbors = [pos, pos.up(), pos.down(), pos.left(), pos.right()]
        neighbor_vars = [switch_vars[n] for n in neighbors if board.is_valid(n)]
        n_neighbors = len(neighbor_vars)
        # 最终灯全灭的条件：初始状态 = 所有相关按钮按下的奇偶性

        if init:  # 需要奇数 -> 禁止所有偶数
            for even in range(0, n_neighbors + 2, 2):
                model.Add(sum(neighbor_vars) != even)
        else:     # 需要偶数 -> 禁止所有奇数
            for odd in range(1, n_neighbors + 2, 2):
                model.Add(sum(neighbor_vars) != odd)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        get_logger().warn("点灯游戏无解")
        raise GenerateError("点灯游戏无解")
    else:
        # 增加约束：至少有一个位置与当前解的值不同（禁止当前解）
        literals = [var.Not() if solver.Value(var) else var for var in switch_vars.values()]
        model2 = model.clone()
        model2.AddBoolOr(literals)

        result = {pos: solver.Value(var) for pos, var in switch_vars.items()}
        solver2 = cp_model.CpSolver()
        status2 = solver2.Solve(model2)
        logger = get_logger()
        if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if logger.print_level == logger.TRACE:
                from minesweepervariants.utils.impl_obj import MINES_TAG, VALUE_QUESS
                logger.trace(result)
                _board = board.clone()
                for pos, var in result.items():
                    _board.set_value(pos, MINES_TAG if var else VALUE_QUESS)
                logger.trace("\n" + str(_board))
                result = {pos: solver2.Value(var) for pos, var in switch_vars.items()}
                logger.trace(result)
                _board = board.clone()
                for pos, var in result.items():
                    _board.set_value(pos, MINES_TAG if var else VALUE_QUESS)
                logger.trace("\n" + str(_board))
            logger.warn("点灯游戏多解")
            raise GenerateError("点灯游戏多解")
    return model, solver, switch_vars


class RuleLO(AbstractClueRule):
    id = "LO"
    name = "LightsOut"
    doc = ("The clue represent the number of switches activated within a 3x3 area of the board, "
           "after switches activated all board is left empty finally. "
           "(The clue also show whether the switch at this clue location is activated.)")
    name.zh_CN = "点灯游戏"
    doc.zh_CN = "数字表示的是按照点灯游戏将题板点成空题板的3x3范围内打开的开关的数量 (数字也可以看到自己位置的开关是否打开)"
    author = ("雾", 3140864122)
    tags = ["Global", "Local", "Creative", "Construction", "Vanilla Variant"]
    creation_time = "2026-05-05"

    def fill(self, board: 'Board') -> 'Board':
        state = {pos: isinstance(obj, AbstractMinesValue) for pos, obj in board("always")}
        model, solver, switch_var = solver_lightsOut(state, board)
        result = {pos: solver.Value(var) for pos, var in switch_var.items()}
        _board = board.clone()
        for pos, var in result.items():
            _board.set_value(pos, VALUE_CIRCLE if var else VALUE_CROSS)
        get_logger().info("点灯唯一解结果")
        get_logger().info("\n" + str(_board))
        for pos, _ in board("N"):
            value = sum(result[_pos] for _pos in pos.neighbors(0, 2) if board.is_valid(_pos))
            obj = ValueL0(pos, code=bytes([value]))
            board.set_value(pos, obj)
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)  # 规则激活条件

        # 创建每个位置的开关变量
        switch_vars = {pos: model.new_bool_var(f"switch_{pos}") for pos, _ in board("always")}

        # 添加灯全灭约束（周围按下次数为偶数），仅当 s 为真时生效
        for pos, var in board("always", mode="var"):
            neighbors = [pos, pos.up(), pos.down(), pos.left(), pos.right()]
            neighbor_vars = [switch_vars[n] for n in neighbors if board.is_valid(n)] + [var]
            n = len(neighbor_vars)
            total = sum(neighbor_vars)
            # 要求偶数 → 禁止所有奇数
            for odd in range(1, n + 1, 2):
                model.add(total != odd).OnlyEnforceIf(s)

        # 处理数字格子 ValueL0 的约束
        for pos, obj in board("always"):
            if not isinstance(obj, ValueL0):
                continue
            # 计算 3x3 范围内的开关变量
            obj: ValueL0
            obj.create_constraints_(switch_vars, switch, board)


class ValueL0(AbstractClueValue):
    @classmethod
    def type(cls) -> bytes:
        return RuleLO.id.encode("ascii")

    def __init__(self, pos: Position, code: bytes = None):
        super().__init__(pos, code)
        self.value = code[0]
        self.neighbor = self.pos.neighbors(0, 2)

    def __repr__(self):
        return f"{self.value}"

    def high_light(self, board: 'Board') -> List['Position'] | None:
        return self.neighbor

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints_(
        self, switch_vars: Dict[Position, cp_model.IntVar],
        switch: 'Switch', board: Board
    ):
        model = board.get_model()
        s = switch.get(model, self)
        model.add(sum([switch_vars[pos] for pos in self.neighbor if board.is_valid(pos)]) == self.value).OnlyEnforceIf(s)
