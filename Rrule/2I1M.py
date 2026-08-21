#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[2I1M] 线索表示周围八格的雷数，但其中某格的雷被视为两个。该格的方向由所有线索共享。
"""
from typing import List, Tuple
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.size import Size
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_random, get_logger
from minesweepervariants.json_object import JSONObject
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch

NAME_SUB = "2I1M"

class Rule2I1M(AbstractClueRule):
    id = "2I1M"
    name = "2I1M"
    name.zh_CN = "2I1M"
    doc = "Clue indicates the number of mines in the surrounding eight cells, but one cell's mine counts as two. The direction of that cell is shared across all clues."
    doc.zh_CN = "线索表示周围八格的雷数，但其中某格的雷被视为两个。该格的方向由所有线索共享。"

    tags = ["Variant", "Local", "Number Clue", "Aux Board"]
    creation_time = "2026-08-21"
    author = ("无言之梦", 2452054817)

    def __init__(self, board: Board = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        # 生成副板
        board.generate_board(NAME_SUB, Size(3, 3))
        # 设置副板标签等（可选）
        board.set_config(NAME_SUB, "pos_label", False)

    def fill(self, board: Board) -> Board:
        # 清空副板
        for pos, _ in board(key=NAME_SUB):
            board.set_value(pos, None)

        random = get_random()
        # 随机选择8个方向之一 (dx, dy) from -1,0,1 except (0,0)
        directions = [(dx, dy) for dx in (-1,0,1) for dy in (-1,0,1) if not (dx == 0 and dy == 0)]
        dx, dy = random.choice(directions)
        # 设置副板：对应位置为CIRCLE，其余为CROSS
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                pos = board.get_pos(1+dr, 1+dc, NAME_SUB)  # 副板中心为(1,1)
                if dr == dx and dc == dy:
                    board.set_value(pos, VALUE_CIRCLE)
                else:
                    board.set_value(pos, VALUE_CROSS)
        logger = get_logger()
        logger.debug(f"[2I1M] selected offset ({dx}, {dy})")

        # 为每个非雷格设置线索值
        for pos, _ in board("N", special='raw'):
            # 计算周围八格雷数
            neighbor_mines = 0
            for neighbor in pos.neighbors(2):
                if board.in_bounds(neighbor) and board.get_type(neighbor, special='raw') == "F":
                    neighbor_mines += 1
            # 检查偏移位置是否在边界内且是雷
            offset_pos = pos.shift(dx, dy)
            extra = 0
            if board.in_bounds(offset_pos) and board.get_type(offset_pos, special='raw') == "F":
                extra = 1
            total = neighbor_mines + extra
            board.set_value(pos, Value2I1M(pos, count=total))
        return board

    def create_constraints(self, board: Board, switch: Switch) -> None:
        model = board.get_model()
        s = switch.get(model, self)  # 规则开关

        # 获取副板所有位置的变量
        sub_vars = {}
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                pos = board.get_pos(1+dr, 1+dc, NAME_SUB)
                var = board.get_variable(pos)
                if var is not None:
                    sub_vars[(dr, dc)] = var
        # 约束只有一个为真，且中心为0
        all_vars = list(sub_vars.values())
        model.Add(sum(all_vars) == 1).OnlyEnforceIf(s)
        # 中心位置 (0,0) 必须为0
        center_var = sub_vars.get((0,0))
        if center_var is not None:
            model.Add(center_var == 0).OnlyEnforceIf(s)

        # 对于每个线索格，添加值约束
        for pos, obj in board("C", mode="obj"):
            if not isinstance(obj, Value2I1M):
                continue
            # 线索格自身必须为非雷
            mine_self = board.get_variable(pos, special='raw')
            if mine_self is not None:
                model.Add(mine_self == 0).OnlyEnforceIf(s)

            # 计算周围八格雷数之和
            neighbor_sum = 0
            for neighbor in pos.neighbors(2):
                if board.in_bounds(neighbor):
                    nvar = board.get_variable(neighbor, special='raw')
                    if nvar is not None:
                        neighbor_sum += nvar

            # 计算偏移贡献：对于每个方向 (dx,dy)，如果该方向被选中且偏移位置是雷，则加1
            extra_sum = 0
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    if dx == 0 and dy == 0:
                        continue
                    sel = sub_vars.get((dx, dy))
                    if sel is None:
                        continue
                    offset_pos = pos.shift(dx, dy)
                    off_var = board.get_variable(offset_pos, special='raw') if board.in_bounds(offset_pos) else None
                    if off_var is not None:
                        # 贡献 = sel AND off_var
                        contrib = model.NewBoolVar(f"contrib_{pos}_{dx}_{dy}")
                        model.Add(contrib <= sel).OnlyEnforceIf(s)
                        model.Add(contrib <= off_var).OnlyEnforceIf(s)
                        model.Add(contrib >= sel + off_var - 1).OnlyEnforceIf(s)
                        extra_sum += contrib

            total_var = model.NewIntVar(0, 9, f"total_{pos}")
            model.Add(total_var == neighbor_sum + extra_sum).OnlyEnforceIf(s)
            # 约束总变量等于线索值
            model.Add(total_var == obj.count).OnlyEnforceIf(s)

    def init_clear(self, board: Board) -> None:
        # 清除副板
        for pos, _ in board(key=NAME_SUB):
            board.set_value(pos, None)


class Value2I1M(AbstractClueValue):
    id = Rule2I1M.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.pos = pos
        self.value = SingleIntValue(count)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractValue':
        _data = data.get_data() if hasattr(data, 'get_data') else data
        if not is_value_template(_data):
            raise TypeError("Invalid value template")
        single = SingleIntValue.try_from(_data)
        if single is None:
            raise ValueError("Invalid data for Value2I1M")
        return cls(pos, count=single.value)

    def create_constraints(self, board: Board, switch: Switch) -> None:
        # 约束由规则类统一处理，此处留空
        pass

    def __repr__(self):
        return str(self.count)

    def tag(self, board: Board) -> bytes:
        return b"2I1M"
