#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[5T] Triangle: Clue value represents the area of the triangle formed by the three nearest mines, 
decimal rounded to one decimal place.
"""
from typing import Dict, cast
from itertools import combinations

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleValue
from minesweepervariants.utils.web_template import Number
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, JSONObject
from ....utils.image_template import get_text


class Rule5T(AbstractClueRule):
    id = "5T"
    aliases = ("Triangle",)
    name = "Triangle"
    name.zh_CN = "三角形"
    doc = "Clue value indicates the area of the triangle formed by the three nearest mines, decimal rounded to one decimal place."
    doc.zh_CN = "线索值表示距离它最近的三个雷围成的三角形面积，十进制精确到小数点后一位。"
    tags = ["Local", "Number Clue", "Extensive Trial", "Creative"]
    creation_time = "2026-06-04"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        # Collect all mine positions (only non-clue cells that are mines)
        mine_positions = [pos for pos, _ in board("F")]
        if len(mine_positions) < 3:
            # Not enough mines to form a triangle, set all N cells to 0.0
            for pos, _ in board("N"):
                board.set_value(pos, Value5T(pos, 0.0))
            return board

        # For each non-mine cell, find the three nearest mines and compute triangle area
        for pos, _ in board("N"):
            # Compute squared distances to all mines
            distances = []
            for mpos in mine_positions:
                dx = pos.col - mpos.col
                dy = pos.row - mpos.row
                dist_sq = dx*dx + dy*dy
                distances.append((dist_sq, mpos))
            # Sort by distance squared and take the three closest
            distances.sort(key=lambda x: x[0])
            three_closest = [mpos for _, mpos in distances[:3]]
            # Compute area of triangle formed by these three mines
            area = self._triangle_area(three_closest[0], three_closest[1], three_closest[2])
            # Round to one decimal place
            area_rounded = round(area, 1)
            board.set_value(pos, Value5T(pos, area_rounded))
        return board

    @staticmethod
    def _triangle_area(p1: Position, p2: Position, p3: Position) -> float:
        """Compute area of triangle given three positions using cross product."""
        # Convert to coordinates relative to p1
        x1, y1 = p1.col, p1.row
        x2, y2 = p2.col, p2.row
        x3, y3 = p3.col, p3.row
        # Cross product of vectors (p2-p1) and (p3-p1)
        cross = abs((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1))
        return cross / 2.0


class Value5T(AbstractClueValue):
    id = Rule5T.id

    def __init__(self, pos: 'Position', value: float, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        # Store as SingleValue with float value rounded to one decimal
        self.value: SingleValue = SingleValue(round(value, 1))
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        # Attempt to parse as SingleValue (handles both int and float)
        val = SingleValue.try_from(template_data)
        if val is None:
            raise ValueError("value is empty")
        # Ensure it's a float
        try:
            float_val = float(val.value)
        except (TypeError, ValueError):
            raise ValueError("value must be numeric")
        return cls(pos, float_val)

    def high_light(self, board: 'Board') -> list['Position']:
        """Highlight the three nearest mines."""
        # Find all mines
        mine_positions = [pos for pos, _ in board("F", mode="none")]
        if len(mine_positions) < 3:
            return []
        # Compute distances and sort
        distances = []
        for mpos in mine_positions:
            dx = self.pos.col - mpos.col
            dy = self.pos.row - mpos.row
            dist_sq = dx*dx + dy*dy
            distances.append((dist_sq, mpos))
        distances.sort(key=lambda x: x[0])
        three_closest = [mpos for _, mpos in distances[:3]]
        return three_closest

    def create_constraints(self, board: 'Board', switch):
        """
        Constraint: The value at this position must equal the area of the triangle
        formed by the three nearest mines.
        """
        model = board.get_model()
        s = switch.get(model, self)

        # Get all positions that could be mines (non-clue positions with variables)
        # We need to iterate over all positions and check if they have a variable
        var_positions = []
        for pos, _ in board("always", mode="none"):
            # Skip positions that are definitely not mines (type 'C')
            if board.get_type(pos) == 'C':
                continue
            # Skip the clue's own position (it's not a mine)
            if pos == self.pos:
                continue
            var = board.get_variable(pos)
            if var is not None:
                var_positions.append((pos, var))

        if len(var_positions) < 3:
            # Not enough possible mine positions; clue is trivially satisfiable
            model.Add(s == 1)
            return

        # Compute squared distances from self.pos to each variable position
        candidates = []
        for pos, var in var_positions:
            dx = self.pos.col - pos.col
            dy = self.pos.row - pos.row
            dist_sq = dx*dx + dy*dy
            candidates.append((dist_sq, pos, var))
        candidates.sort(key=lambda x: x[0])

        # Limit to the 30 closest positions to keep combinatorial explosion manageable
        limit = min(30, len(candidates))
        candidates = candidates[:limit]

        if len(candidates) < 3:
            model.Add(s == 1)
            return

        # Enumerate all combinations of 3 candidates and create a temporary variable
        # for each combination that could be the nearest three mines.
        comb_vars = []
        indices = list(range(len(candidates)))
        for comb in combinations(indices, 3):
            i, j, k = comb
            d_i, p_i, var_i = candidates[i]
            d_j, p_j, var_j = candidates[j]
            d_k, p_k, var_k = candidates[k]
            max_d = max(d_i, d_j, d_k)

            # Variables for the three mines
            triple_vars = [var_i, var_j, var_k]

            # Variables for all other candidates with distance < max_d
            closer_vars = []
            for idx, (dist, pos, var) in enumerate(candidates):
                if idx in comb:
                    continue
                if dist < max_d:
                    closer_vars.append(var)

            # Check if the area of this triangle equals the clue value (rounded to 1 decimal)
            area = Rule5T._triangle_area(p_i, p_j, p_k)
            area_scaled = round(area * 10)
            target_scaled = int(round(self.value.value * 10))

            # Only consider combinations where the area matches
            if area_scaled != target_scaled:
                continue

            # Create a temporary variable indicating this combination is the nearest three
            tmp_var = model.NewBoolVar(f"tmp_5T_{self.pos.col}_{self.pos.row}_{len(comb_vars)}")
            
            # If tmp_var is true and the clue is active, enforce:
            # 1. The three mines are all mines
            model.Add(sum(triple_vars) == 3).OnlyEnforceIf([tmp_var, s])
            # 2. All closer positions are not mines
            if closer_vars:
                model.Add(sum(closer_vars) == 0).OnlyEnforceIf([tmp_var, s])
            
            comb_vars.append(tmp_var)

        if not comb_vars:
            # No valid combination; deactivate this clue
            model.Add(s == 0)
            return

        # At least one combination must be true when the clue is active
        model.Add(sum(comb_vars) == 1).OnlyEnforceIf(s)

    def web_component(self, board) -> Dict:
        """Render as a number with one decimal place."""
        return Number(str(self.value.value))

    def compose(self, board):
        """Render as a text element showing the area."""
        # Display the value with one decimal place
        return get_text(f"{self.value.value:.1f}")
