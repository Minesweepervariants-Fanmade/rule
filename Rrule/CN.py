#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/05 13:40
# @FileName: CN.py
"""
[CN] 复数雷值 (Complex Number)：雷的雷值将是(+1,-1,+i,-i)中的一种，
数字表示周围八格的雷值之和的模长。
"""
from typing import List, cast, Dict

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.image_template import get_col, get_dummy, get_image, get_row, get_text
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template

AXIS = "CN_axis"    # 0=实轴(±1)  1=虚轴(±i)
SIGN = "CN_sign"    # 0=负        1=正


def simplify_sqrt(n: int):
    """将非负整数 n 写成 a^2 * b（b 无平方因子），使 sqrt(n) = a*sqrt(b)。"""
    if n <= 0:
        return 0, 1
    a, b, i = 1, n, 2
    while i * i <= b:
        while b % (i * i) == 0:
            b //= i * i
            a *= i
        i += 1
    return a, b


class RuleCN(AbstractClueRule):
    id = "CN"
    name = "Complex Number"
    name.zh_CN = "复数雷值"
    doc = ("Each mine has a complex mine value in (+1, -1, +i, -i). "
           "Clues indicate the modulus of the sum of mine values in the surrounding 8 cells.")
    doc.zh_CN = ("雷的雷值将是(+1,-1,+i,-i)中的一种，"
                 "数字表示周围八格的雷值之和的模长。")
    tags = ["Variant", "Local", "Number Clue", "Mine-Value", "Creative"]
    creation_time = "2026-10-05"
    author = ("雾", 3140864122)
    special = SIGN

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        board.generate_board(AXIS, )

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()
        cg = {}
        for pos, _ in board("F", special='raw'):
            k = random.randint(0, 3)
            cg[pos] = ([1, -1, 0, 0][k], [0, 0, 1, -1][k])
        for pos, _ in board("N", special='raw'):
            sr = si = 0
            for nei in pos.neighbors(2):
                if not board.in_bounds(nei):
                    continue
                if nei in cg:
                    sr += cg[nei][0]
                    si += cg[nei][1]
            board.set_value(pos, ValueCN(pos, sr * sr + si * si))
        return board

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        # 每格注册两个 bool 表示雷值（非雷时均为 0，贡献自然为 0）：
        #   axis: False→实轴(±1)  True→虚轴(±i)
        #   sign: False→负        True→正
        for key in board.get_interactive_keys():
            for pos, mine_var in board(key=key, mode="var", special='raw'):
                if mine_var is None:
                    continue
                axis = model.new_bool_var(f"CN_axis_{key}_{pos.col}_{pos.row}")
                sign = model.new_bool_var(f"CN_sign_{key}_{pos.col}_{pos.row}")
                model.add(axis <= mine_var).only_enforce_if(s)
                model.add(sign <= mine_var).only_enforce_if(s)
                board.register_variable_special(AXIS, pos, axis)
                board.register_variable_special(SIGN, pos, sign)


class ValueCN(AbstractClueValue):
    id = RuleCN.id

    def __init__(self, pos: Position, value: int = 0, code: bytes = None):
        super().__init__(pos, b'')
        if code is not None:
            value = code[0] if len(code) == 1 else int.from_bytes(code[:2], "big")
        self.count = int(value)
        self.neighbor = pos.neighbors(2)
        self.value = SingleIntValue(self.count)

    def __repr__(self) -> str:
        a, b = simplify_sqrt(self.count)
        if b == 1:
            return f"{a}"
        if a == 1:
            return f"√{b}"
        return f"{a}√{b}"

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        val = SingleIntValue.try_from(cast(Template, _data))
        if val is None:
            raise ValueError("value is empty")
        return cls(pos, value=int(val.value))

    def high_light(self, board: 'Board') -> List['Position']:
        return [nei for nei in self.neighbor if board.in_bounds(nei)]

    def invalid(self, board: 'Board') -> bool:
        return board.batch(self.neighbor, mode="type", special='raw').count("N") == 0

    def compose(self, board) -> Dict:
        a, b = simplify_sqrt(self.count)
        if b == 1:
            return get_col(get_dummy(height=0.175), get_text(str(a)), get_dummy(height=0.175))
        if a == 1:
            return get_row(get_image("sqrt"), get_text(str(b)), spacing=-0.15)
        return get_row(get_text(str(a)), get_image("sqrt"), get_text(str(b)), spacing=-0.2)

    def web_component(self, board) -> Dict:
        a, b = simplify_sqrt(self.count)
        if b == 1:
            return get_text(str(a))
        if a == 1:
            return get_text("$\\sqrt{" + str(b) + "}$")
        return get_text("$" + str(a) + "\\sqrt{" + str(b) + "}$")

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self.pos)
        logger = get_logger()

        # 由 axis/sign 得到每格的实部、虚部（m=0 时两者恒为 0）：
        #   ab = axis AND sign
        #   re = -m + axis + 2*sign - 2*ab   ∈ {-1, 0, 1}
        #   im = 2*ab - axis                 ∈ {-1, 0, 1}
        re_terms: List = []
        im_terms: List = []
        for nei in self.neighbor:
            if not board.in_bounds(nei):
                continue
            m = board.get_variable(nei, special="raw")
            axis = board.get_variable(nei, special=AXIS)
            sign = board.get_variable(nei, special=SIGN)
            if m is None or axis is None or sign is None:
                continue
            ab = model.new_bool_var(f"CN_ab_{nei.board_key}_{nei.col}_{nei.row}")
            model.add(ab <= axis)
            model.add(ab <= sign)
            model.add(ab >= axis + sign - 1)
            re_terms.append(-m + axis + 2 * sign - 2 * ab)
            im_terms.append(2 * ab - axis)

        if not re_terms:
            model.add(self.count == 0).only_enforce_if(s)
            return

        sr = model.new_int_var(-8, 8, f"CN_sr_{self.pos.col}_{self.pos.row}")
        si = model.new_int_var(-8, 8, f"CN_si_{self.pos.col}_{self.pos.row}")
        model.add(sr == sum(re_terms)).only_enforce_if(s)
        model.add(si == sum(im_terms)).only_enforce_if(s)

        sr2 = model.new_int_var(0, 64, f"CN_sr2_{self.pos.col}_{self.pos.row}")
        si2 = model.new_int_var(0, 64, f"CN_si2_{self.pos.col}_{self.pos.row}")
        model.add_multiplication_equality(sr2, [sr, sr]).only_enforce_if(s)
        model.add_multiplication_equality(si2, [si, si]).only_enforce_if(s)

        model.add(sr2 + si2 == self.count).only_enforce_if(s)
        logger.trace(f"[CN] {self.pos}: N={self.count}")