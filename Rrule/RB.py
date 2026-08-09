#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[RB] 彩虹：从题版上方向下射出彩虹单色光，遇到非雷格向下传递，遇到雷格分成两条向斜向左下右下传递一格。
线索格表示该格拥有的光种类。（第一列的光表示为A，第二列为B，以此类推...）
"""

from typing import cast, List
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.impl.summon.solver import Switch


class RuleRB(AbstractClueRule):
    """彩虹规则：光线传播，线索值为到达该格的光颜色位掩码。"""

    id = "RB"
    name = "Rainbow"
    name.zh_CN = "彩虹"
    doc = "Rainbow light beams travel downward from the top; non-mine cells pass them down, mines split them into two diagonal rays. Clue shows the set of colors (bitmask) that reach the cell."
    doc.zh_CN = "从题版上方向下射出彩虹单色光，遇到非雷格向下传递，遇到雷格分成两条向斜向左下右下传递一格。线索格表示该格拥有的光种类（位掩码）。"
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-08-10"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        keys = board.get_interactive_keys()
        if not keys:
            return board
        key = keys[0]
        bound = board.boundary(key)
        rows = bound.row + 1
        cols = bound.col + 1

        masks = [[0 for _ in range(cols)] for _ in range(rows)]
        for c in range(cols):
            masks[0][c] = (1 << c)

        for r in range(rows - 1):
            for c in range(cols):
                mask = masks[r][c]
                if mask == 0:
                    continue
                pos = board.get_pos(r, c, key)
                if pos is None or not board.is_valid(pos):
                    continue
                is_mine = (board.get_type(pos, special='raw') == "F")
                if not is_mine:
                    down_pos = board.get_pos(r + 1, c, key)
                    if down_pos is not None and board.is_valid(down_pos):
                        masks[r + 1][c] |= mask
                else:
                    if c > 0:
                        left_down = board.get_pos(r + 1, c - 1, key)
                        if left_down is not None and board.is_valid(left_down):
                            masks[r + 1][c - 1] |= mask
                    if c < cols - 1:
                        right_down = board.get_pos(r + 1, c + 1, key)
                        if right_down is not None and board.is_valid(right_down):
                            masks[r + 1][c + 1] |= mask

        for r in range(rows):
            for c in range(cols):
                pos = board.get_pos(r, c, key)
                if pos is None or not board.is_valid(pos):
                    continue
                if board.get_type(pos, special='raw') == "N":
                    board.set_value(pos, ValueRB(pos, masks[r][c]))
                    logger.trace(f"RB fill {pos}: mask={masks[r][c]:08b}")

        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        keys = board.get_interactive_keys()
        if not keys:
            return
        key = keys[0]
        bound = board.boundary(key)
        rows = bound.row + 1
        cols = bound.col + 1

        rule_switch = switch.get(model, self)

        # 为每个格子的每种颜色创建布尔变量
        bit = [[[None for _ in range(cols)] for _ in range(cols)] for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                for k in range(cols):
                    bit[r][c][k] = model.NewBoolVar(f"RB_bit_{r}_{c}_{k}")

        # 第一行：只有同列的光线为真
        for c in range(cols):
            for k in range(cols):
                if c == k:
                    model.Add(bit[0][c][k] == 1).OnlyEnforceIf(rule_switch)
                else:
                    model.Add(bit[0][c][k] == 0).OnlyEnforceIf(rule_switch)

        # 传播约束：使用来源视角，每个格子的光线来源于上一行的三个候选位置
        for r in range(1, rows):
            for c in range(cols):
                pos = board.get_pos(r, c, key)
                if pos is None or not board.is_valid(pos):
                    continue

                for k in range(cols):
                    cur_bit = bit[r][c][k]
                    sources = []

                    # 来源1: 正上方直传（正上方非雷）
                    up_pos = board.get_pos(r - 1, c, key)
                    if up_pos is not None and board.is_valid(up_pos):
                        up_mine = board.get_variable(up_pos, special='raw')
                        if up_mine is not None:
                            up_bit = bit[r - 1][c][k]
                            src_up = model.NewBoolVar(f"RB_src_up_{r}_{c}_{k}")
                            model.Add(src_up == up_bit).OnlyEnforceIf([up_mine.Not(), rule_switch])
                            model.Add(src_up == 0).OnlyEnforceIf([up_mine, rule_switch])
                            sources.append(src_up)

                    # 来源2: 左上方分裂（左上方是雷）
                    up_left_pos = board.get_pos(r - 1, c - 1, key)
                    if up_left_pos is not None and board.is_valid(up_left_pos) and c > 0:
                        up_left_mine = board.get_variable(up_left_pos, special='raw')
                        if up_left_mine is not None:
                            up_left_bit = bit[r - 1][c - 1][k]
                            src_ul = model.NewBoolVar(f"RB_src_ul_{r}_{c}_{k}")
                            model.Add(src_ul == up_left_bit).OnlyEnforceIf([up_left_mine, rule_switch])
                            model.Add(src_ul == 0).OnlyEnforceIf([up_left_mine.Not(), rule_switch])
                            sources.append(src_ul)

                    # 来源3: 右上方分裂（右上方是雷）
                    up_right_pos = board.get_pos(r - 1, c + 1, key)
                    if up_right_pos is not None and board.is_valid(up_right_pos) and c < cols - 1:
                        up_right_mine = board.get_variable(up_right_pos, special='raw')
                        if up_right_mine is not None:
                            up_right_bit = bit[r - 1][c + 1][k]
                            src_ur = model.NewBoolVar(f"RB_src_ur_{r}_{c}_{k}")
                            model.Add(src_ur == up_right_bit).OnlyEnforceIf([up_right_mine, rule_switch])
                            model.Add(src_ur == 0).OnlyEnforceIf([up_right_mine.Not(), rule_switch])
                            sources.append(src_ur)

                    if sources:
                        # 当前格子的光线必须恰好等于一个来源（对于每种颜色，只能有一条路径到达）
                        # 并且如果当前位为1，则恰好有一个来源为1；如果为0，则所有来源为0
                        # 这等价于：sum(sources) == cur_bit
                        model.Add(sum(sources) == cur_bit).OnlyEnforceIf(rule_switch)
                    else:
                        # 没有任何来源，当前位必须为假
                        model.Add(cur_bit == 0).OnlyEnforceIf(rule_switch)

        # 线索值约束
        for r in range(rows):
            for c in range(cols):
                pos = board.get_pos(r, c, key)
                if pos is None or not board.is_valid(pos):
                    continue
                obj = board.get_value(pos)
                if not isinstance(obj, ValueRB):
                    continue
                terms = []
                for k in range(cols):
                    if bit[r][c][k] is not None:
                        terms.append((1 << k) * bit[r][c][k])
                if terms:
                    model.Add(sum(terms) == obj.value).OnlyEnforceIf(rule_switch)


class ValueRB(AbstractClueValue):
    id = RuleRB.id

    def __init__(self, pos: Position, value: int = 0):
        super().__init__(pos, b'')
        self.value = value
        self.pos = pos
        self.value_template = SingleIntValue(value)

    def __repr__(self) -> str:
        if self.value == 0:
            return "0"
        chars = []
        for k in range(26):
            if self.value & (1 << k):
                chars.append(chr(ord('A') + k))
        return ''.join(chars) if chars else "0"

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid value template")
        template = cast(Template, _data)
        val = SingleIntValue.try_from(template)
        if val is None:
            raise ValueError("Missing value")
        return cls(pos, val.value)

    def json(self) -> JSONObject:
        return self.value_template.json()

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        pass

    def tag(self, board: 'Board') -> bytes:
        if self.value == 0:
            return b"0"
        chars = []
        for k in range(26):
            if self.value & (1 << k):
                chars.append(chr(ord('A') + k))
        return ''.join(chars).encode('ascii')

    def high_light(self, board: 'Board') -> List[Position] | None:
        return [self.pos]
