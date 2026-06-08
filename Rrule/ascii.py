#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
Rule: ascii
右线线索为周围八格从右格开始逆时针旋转一圈将雷/非雷视为1/0得到的一字节整数按下列对应方式映射后的整数对应的ascii:
0~31, 127~255 -> 0
33~62, 64, 65~90, 91~96, 123~126 -> 保持原数字
32 -> 该格不填充线索
63 -> 该格填充问号线索
97~122 -> 原数-32
"""

from ortools.sat.python.cp_model import CpModel, IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import VALUE_QUESS

# Corresponding bit weights (most‑significant bit first)
_weights = [128, 64, 32, 16, 8, 4, 2, 1]

class RuleAscii(AbstractClueRule):
    """右线线索：根据周围八格的雷分布生成 ASCII 字符"""

    id = "ascii"
    name = "ASCII"
    name.zh_CN = "ASCII"
    doc = (
        "Clue shows the ASCII character represented by the 8 surrounding cells, "
        "starting from the right cell and rotating counter‑clockwise, "
        "treating mines as 1 and empty cells as 0. Non‑printable or non‑ASCII "
        "characters are displayed as the Unknown."
    )
    doc.zh_CN = "右线线索为周围八格从右格开始逆时针旋转一圈将雷/非雷视为1/0得到的一字节对应的ascii字符，不可打印字符或非ascii字符显示为滚木"
    tags = ["Original", "Local", "Cryptic", "Weak"]
    creation_time = "2026-05-08"
    author = ("NT", 2201963934)


    def fill(self, board: 'Board') -> 'Board':
        """Populate the board with ValueAscii objects for each clue cell (type 'N')."""
        for pos, _ in board("N"):
            byte_val = 0
            # Determine neighbours in the required order using existing helper methods
            neighbours = [
                pos.right(),                     # right
                pos.right().up(),                # up‑right
                pos.up(),                        # up
                pos.left().up(),                 # up‑left
                pos.left(),                      # left
                pos.left().down(),               # down‑left
                pos.down(),                      # down
                pos.right().down(),              # down‑right
            ]
            for neighbor, weight in zip(neighbours, _weights):
                if board.get_type(neighbor) == "F":
                    byte_val += weight

            # Apply mapping rules to determine what to place on the board
            if byte_val == 32:
                # 32: do not place any clue (skip)
                continue
            if byte_val == 63:
                # 63: place a question‑mark clue
                board[pos] = VALUE_QUESS
                continue
            # Mapping for display value
            if 0 <= byte_val <= 31 or 127 <= byte_val <= 255:
                display_val = 0
            elif 33 <= byte_val <= 62 or byte_val == 64 or 65 <= byte_val <= 90 or 91 <= byte_val <= 96 or 123 <= byte_val <= 126:
                display_val = byte_val
            elif 97 <= byte_val <= 122:
                display_val = byte_val - 32
            else:
                # Should not occur; treat as 0
                display_val = 0
            board[pos] = ValueAscii(pos, bytes([display_val]))
        return board

class ValueAscii(AbstractClueValue):
    id = RuleAscii.id
    """Clue value storing the raw byte and providing a printable representation."""

    def __init__(self, pos: 'Position', code: bytes = b''):
        super().__init__(pos, code)
        # code is a single byte representing the ASCII value
        self.value = code[0] if code else 0

    def __repr__(self) -> str:
        # printable ASCII range 0x20‑0x7E; additionally ensure isprintable()
        if 0x20 <= self.value <= 0x7E:
            ch = chr(self.value)
            if ch.isprintable():
                return ch
        return "木"

    def code(self) -> bytes:
        return bytes([self.value])

    @classmethod
    def type(cls) -> bytes:
        return RuleAscii.id.encode("ascii")

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        """Create CP‑SAT constraints that enforce the ASCII value derived from mines."""
        model = board.get_model()

        # collect boolean variables for the eight neighbours in the same order
        neighbor_vars = []
        applicable_weights = []
        # Determine neighbour variables using helper methods (same order as fill)
        neighbours = [
            self.pos.right(),
            self.pos.right().up(),
            self.pos.up(),
            self.pos.left().up(),
            self.pos.left(),
            self.pos.left().down(),
            self.pos.down(),
            self.pos.right().down(),
        ]
        neighbor_vars = []
        applicable_weights = []
        for neighbor, weight in zip(neighbours, _weights):
            if not board.in_bounds(neighbor):
                continue
            neighbor_vars.append(board.get_variable(neighbor))
            applicable_weights.append(weight)
        weighted_sum = sum(v * w for v, w in zip(neighbor_vars, applicable_weights))

        # Reverse‑mapping: determine all possible original byte values that could produce the stored display value
        possible_originals: list[int] = []
        if self.value == 0:
            possible_originals.extend(range(0, 32))
            possible_originals.extend(range(127, 256))
        else:
            # original unchanged case (if within allowed original ranges)
            allowed_original = (
                list(range(33, 63)) + [64] + list(range(65, 91)) + list(range(91, 97)) + list(range(123, 127))
            )
            if self.value in allowed_original:
                possible_originals.append(self.value)
            # original could be display+32 (maps from 97‑122)
            if 97 <= self.value + 32 <= 122:
                possible_originals.append(self.value + 32)

        # Create an auxiliary variable for the weighted sum and restrict it to the possible originals
        sum_var = model.NewIntVar(0, 255, f"ascii_sum_{self.pos}")
        model.Add(sum_var == weighted_sum)
        if possible_originals:
            model.AddAllowedAssignments([sum_var], [[v] for v in possible_originals])
        # Enforce only when this clue is active
        model.Add(sum_var == sum_var).OnlyEnforceIf(switch.get(model, self))
