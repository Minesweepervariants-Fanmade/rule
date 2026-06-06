#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[6L] 光
作者: Jsky单推人 (2638680527)

规则语义:
- 右线规则。每个线索格的值等于题板上所有雷到该格中心的欧几里得距离平方倒数之和。
- 线索值以最简分数显示。
- 约束阶段把有理式乘以距离平方的最小公倍数，转成整系数线性等式。
"""

from fractions import Fraction
import math

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.image_template import get_dummy, get_text, get_col, get_row, get_image


class Rule6L(AbstractClueRule):
    id = "6L"
    name = "Light"
    name.zh_CN = "光"
    doc = "Mines are light bulbs, and each bulb increases the brightness of any cell on the board by the inverse of the square of the distance. Clues indicate the total brightness of that cell."
    doc.zh_CN = "雷是一个灯泡，一个灯可以让题板任意位置的亮度增加距离平方的倒数，线索指示该格的亮度总和"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2026-05-20"
    author = ("Jsky单推人", 2638680527)

    def fill(self, board: 'Board') -> 'Board':
        for key in board.get_interactive_keys():
            mines = [pos for pos, _ in board("F", key=key)]
            for pos, _ in board("N", key=key):
                total = Fraction(0, 1)
                for mine in mines:
                    dx = mine.x - pos.x
                    dy = mine.y - pos.y
                    dist2 = dx * dx + dy * dy
                    if dist2 <= 0:
                        continue
                    total += Fraction(1, dist2)
                board.set_value(pos, Value6L(pos, value=total))
        return board

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions_vars = [
                (pos, var)
                for pos, var in board(key=key, mode="variable", special="raw")
                if var is not None
            ]

            if not positions_vars:
                continue

            for pos, obj in board("C", key=key):
                if not isinstance(obj, Value6L):
                    continue

                clue_var = board.get_variable(pos, special="raw")
                if clue_var is not None:
                    model.Add(clue_var == 0).OnlyEnforceIf(s)

                terms: list[tuple[object, int]] = []
                denominators: list[int] = []
                for other_pos, var in positions_vars:
                    if other_pos == pos:
                        continue

                    dx = other_pos.x - pos.x
                    dy = other_pos.y - pos.y
                    dist2 = dx * dx + dy * dy
                    if dist2 <= 0:
                        continue

                    terms.append((var, dist2))
                    denominators.append(dist2)

                if not terms:
                    if obj.value != 0:
                        model.Add(False).OnlyEnforceIf(s)
                    continue

                scale = math.lcm(*denominators)
                coeffs = [scale * obj.value.denominator // dist2 for _, dist2 in terms]
                rhs = scale * obj.value.numerator

                divisor = abs(rhs)
                for coeff in coeffs:
                    divisor = math.gcd(divisor, abs(coeff))
                if divisor > 1:
                    coeffs = [coeff // divisor for coeff in coeffs]
                    rhs //= divisor

                model.Add(
                    sum(coeff * var for (var, _), coeff in zip(terms, coeffs)) == rhs
                ).OnlyEnforceIf(s)


class Value6L(AbstractClueValue):
    id = "6L"
    def __init__(self, pos: 'Position', value: Fraction | int | tuple[int, int] | None = None, code: bytes | None = None):
        super().__init__(pos, code or b'')
        if code is not None:
            text = code.decode("ascii")
            if "/" in text:
                numerator, denominator = text.split("/", 1)
                self.value = Fraction(int(numerator), int(denominator))
            elif text:
                self.value = Fraction(int(text), 1)
            else:
                self.value = Fraction(0, 1)
        else:
            if value is None:
                self.value = Fraction(0, 1)
            elif isinstance(value, Fraction):
                self.value = value
            elif isinstance(value, tuple):
                self.value = Fraction(value[0], value[1])
            else:
                self.value = Fraction(int(value), 1)

    def __repr__(self):
        if self.value.denominator == 1:
            return str(self.value.numerator)
        return f"{self.value.numerator}/{self.value.denominator}"

    def compose(self, board):
        whole = self.value.numerator // self.value.denominator
        rem = self.value.numerator % self.value.denominator

        if rem == 0:
            return get_col(
                get_dummy(height=0.175),
                get_text(str(whole)),
                get_dummy(height=0.175),
            )

        fraction_col = get_col(
            get_text(str(rem)),
            get_image(
                "double_horizontal_arrow",
                image_width=0.6,
                image_height=0.05,
                dominant_by_height=False,
            ),
            get_text(str(self.value.denominator)),
            spacing=0,
            dominant_by_height=False,
        )

        if whole == 0:
            return fraction_col

        return get_row(
            get_text(str(whole), width=0.3),
            fraction_col,
            spacing=-0.1,
            dominant_by_height=True,
        )

    def web_component(self, board):
        return self.compose(board)

    @classmethod
    def type(cls) -> bytes:
        return Rule6L.id.encode("ascii")

    def code(self) -> bytes:
        if self.value.denominator == 1:
            return str(self.value.numerator).encode("ascii")
        return f"{self.value.numerator}/{self.value.denominator}".encode("ascii")