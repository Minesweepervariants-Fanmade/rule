#!/usr/bin/env python3

"""
[1X+] 城堡 (Castle)：线索数表示与其同行或同列的所有格子中的雷数
"""
from typing import List

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def _get_row_col_positions(board: 'AbstractBoard', pos: AbstractPosition):
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
    name = ["1X+", "城堡", "Castle"]
    doc = "线索数表示与其同行或同列的所有格子中的雷数"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            # 计算同行和同列所有格子中的雷数
            row_col_positions = _get_row_col_positions(board, pos)
            value = len([_pos for _pos in row_col_positions if board.get_type(_pos) == "F"])
            board.set_value(pos, Value1XPlus(pos, count=value))
            logger.debug(f"Set {pos} to 1X+[{value}]")
        return board


class Value1XPlus(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count

    def _get_row_col_positions(self, board: 'AbstractBoard'):
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

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition']:
        return self._get_row_col_positions(board)

    def __repr__(self):
        return f"{self.count}"

    @classmethod
    def type(cls) -> bytes:
        return Rule1XPlus.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def deduce_cells(self, board: 'AbstractBoard') -> bool:
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
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True

        # 如果已找到的雷数加上未知格子数等于目标数，剩余格子都是雷
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True

        return False

    def create_constraints(self, board: 'AbstractBoard', switch):
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
            model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
