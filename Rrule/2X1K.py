#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/12
# @Author  : NT (2201963934)
# @FileName: 2X1K.py
"""
[2X1K] 马步十字：两个线索数表示，反正分成两份
"""
from typing import Dict, List

from minesweepervariants.utils.web_template import MultiNumber
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, SingleIntValue
from minesweepervariants.board import Board, Position
from ....utils.image_template import get_text, get_row
from ....utils.tool import get_logger, get_random


class Rule2X1K(AbstractClueRule):
    id = "2X1K"
    name = "Knight Cross"
    name.zh_CN = "马步十字"
    doc = "Clue shows the number of mines in dyed and undyed cells within knight-move area (order is not fixed)"
    doc.zh_CN = "线索表示马步范围内染色格和非染色格的雷数（顺序不确定）"
    tags = ["Variant", "Local", "Number Clue", "Dyed", "Untagged"]
    creation_time = "2026-07-12"
    author = ("NT", 2201963934)

    @staticmethod
    def get_knight_neighbors(pos: Position, board: Board) -> List[Position]:
        """返回马步（骑士步）的8个方向位置"""
        x, y = pos.x, pos.y
        board_key = pos.board_key
        # 马步的8个方向: (±2, ±1) 和 (±1, ±2)
        knight_moves = [
            (-2, -1), (-2, 1),
            (-1, -2), (-1, 2),
            (1, -2), (1, 2),
            (2, -1), (2, 1)
        ]
        neighbors = []
        for dx, dy in knight_moves:
            npos = type(pos)(x + dx, y + dy, board_key)
            if board.in_bounds(npos):
                neighbors.append(npos)
        return neighbors

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        r = get_random()
        for pos, _ in board("N"):
            neighbors = self.get_knight_neighbors(pos, board)
            value1 = len([p for p in neighbors if board.get_type(p) == "F" and board.get_dyed(p)])
            value2 = len([p for p in neighbors if board.get_type(p) == "F" and not board.get_dyed(p)])
            # 随机交换顺序（与2X一致）
            if r.randint(0, 1):
                value1, value2 = value2, value1
            board.set_value(pos, Value2X1K(pos, count=value1 * 10 + value2))
            logger.debug(f"Set {pos} to 2X1K[{value1 * 10 + value2}]")
        return board


class Value2X1K(AbstractClueValue):
    id = Rule2X1K.id

    def __init__(self, pos: Position, code: bytes = None, count: int = 0):
        super().__init__(pos, code)
        if code is not None:
            self.count = code[0]
        else:
            self.count = count
        self.value = SingleIntValue(self.count)

    def __repr__(self) -> str:
        return f"{self.count // 10} {self.count % 10}"

    def high_light(self, board: 'Board') -> List['Position']:
        return Rule2X1K.get_knight_neighbors(self.pos, board)

    def web_component(self, board) -> Dict:
        value = [self.count // 10, self.count % 10]
        value.sort()
        return MultiNumber(value)

    def compose(self, board) -> Dict:
        value = [self.count // 10, self.count % 10]
        value.sort()
        text_a = get_text(str(value[0]))
        text_b = get_text(str(value[1]))
        return get_row(text_a, text_b)

    @classmethod
    def type(cls) -> bytes:
        return Rule2X1K.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        template_data = _data
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError()

        return cls(pos, count=value.value)

    def create_constraints(self, board: 'Board', switch):
        """创建CP-SAT约束: 马步范围内染色格和非染色格的雷数分别等于两个数字（顺序不确定）"""
        model = board.get_model()
        s = switch.get(model, self)
        # 强制该线索开关为 True，确保线索有效
        model.Add(s == 1)
        # 强制该线索开关为 True，确保线索有效
        model.Add(s == 1)
        # 强制该线索开关为 True，确保线索有效
        model.Add(s == 1)

        # 收集马步范围内染色和非染色的变量
        neighbor_vars_dyed = []
        neighbor_vars_undyed = []
        for neighbor in Rule2X1K.get_knight_neighbors(self.pos, board):
            var = board.get_variable(neighbor)
            if var is not None:
                if board.get_dyed(neighbor):
                    neighbor_vars_dyed.append(var)
                else:
                    neighbor_vars_undyed.append(var)

        if neighbor_vars_dyed or neighbor_vars_undyed:
            # 使用布尔变量 t 控制顺序
            t = model.NewBoolVar('t')
            # 顺序1: 染色格 = count//10, 非染色格 = count%10
            model.Add(sum(neighbor_vars_dyed) == self.count // 10).OnlyEnforceIf([t, s])
            model.Add(sum(neighbor_vars_undyed) == self.count % 10).OnlyEnforceIf([t, s])
            # 顺序2: 染色格 = count%10, 非染色格 = count//10
            model.Add(sum(neighbor_vars_dyed) == self.count % 10).OnlyEnforceIf([t.Not(), s])
            model.Add(sum(neighbor_vars_undyed) == self.count // 10).OnlyEnforceIf([t.Not(), s])
            get_logger().trace(f"[2X1K] {self.pos}: {self.count // 10}/{self.count % 10} constraint added")
