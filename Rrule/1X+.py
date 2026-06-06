#!/usr/bin/env python3

"""
[1X+] 城堡 (Castle)：线索数表示与其同行或同列的所有格子中的雷数
"""
from typing import List

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def _get_row_col_positions(board: 'Board', pos: Position):
    """获取与给定位置同行或同列的所有位置"""
    positions = []
    # 获取棋盘的边界
    boundary = board.boundary()
    max_x, max_y = boundary.x, boundary.y

    # 同行的所有位置（相同x，不同y）
    for y in range(max_y + 1):
        other_pos = type(pos)(pos.x, y, pos.board_key)
        if other_pos != pos and board.in_bounds(other_pos):
            positions.append(other_pos)

    # 同列的所有位置（相同y，不同x）
    for x in range(max_x + 1):
        other_pos = type(pos)(x, pos.y, pos.board_key)
        if other_pos != pos and board.in_bounds(other_pos):
            positions.append(other_pos)

    return positions


class Rule1XPlus(AbstractClueRule):
    id = "1X+"
    aliases = ("X+",)
    name = "Castle"
    name.zh_CN = "城堡"
    doc = "Clue shows the number of mines in all cells in the same row or column"
    doc.zh_CN = "线索数表示与其同行或同列的所有格子中的雷数"
    tags = ["Local", "Number Clue", "Weak", "Creative"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            # 计算同行和同列所有格子中的雷数
            row_col_positions = _get_row_col_positions(board, pos)
            value = len([_pos for _pos in row_col_positions if board.get_type(_pos) == "F"])
            board.set_value(pos, Value1XPlus(pos, value))
            logger.debug(f"Set {pos} to 1X+[{value}]")
        return board


class Value1XPlus(AbstractClueValue):
    id = Rule1XPlus.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def _get_row_col_positions(self, board: 'Board'):
        """获取与给定位置同行或同列的所有位置"""
        positions = []
        # 获取棋盘的边界
        boundary = board.boundary()
        max_x, max_y = boundary.x, boundary.y

        # 同行的所有位置（相同x，不同y）
        for y in range(max_y + 1):
            other_pos = type(self.pos)(self.pos.x, y, self.pos.board_key)
            if other_pos != self.pos and board.in_bounds(other_pos):
                positions.append(other_pos)

        # 同列的所有位置（相同y，不同x）
        for x in range(max_x + 1):
            other_pos = type(self.pos)(x, self.pos.y, self.pos.board_key)
            if other_pos != self.pos and board.in_bounds(other_pos):
                positions.append(other_pos)

        return positions

    def high_light(self, board: 'Board') -> List['Position']:
        return self._get_row_col_positions(board)

    @classmethod
    def type(cls) -> bytes:
        return Rule1XPlus.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value.value])

    def deduce_cells(self, board: 'Board') -> bool:
        row_col_positions = self._get_row_col_positions(board)
        type_dict = {"N": [], "F": []}

        for pos in row_col_positions:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)

        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])

        if n_num == 0:
            return False

        # 如果已找到的雷数等于目标数，剩余格子都是安全的
        if f_num == self.value.value:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True

        # 如果已找到的雷数加上未知格子数等于目标数，剩余格子都是雷
        if f_num + n_num == self.value.value:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True

        return False

    def create_constraints(self, board: 'Board', switch):
        """创建CP-SAT约束：同行或同列的雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集同行或同列格子的布尔变量
        row_col_positions = self._get_row_col_positions(board)
        neighbor_vars = []

        for neighbor in row_col_positions:
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor)
                neighbor_vars.append(var)

        # 添加约束：同行或同列的雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.value.value).OnlyEnforceIf(s)
