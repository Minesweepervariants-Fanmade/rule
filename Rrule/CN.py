#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/05 13:40
# @Author  : DeepSeek Agent
# @FileName: CN.py
"""
[CN] 复数雷值 (Complex Number)：雷的雷值将是(+1,-1,+i,-i)中的一种，
数字表示周围八格的雷值之和的模长。
"""
from typing import Dict, List, cast

from ortools.sat.python.cp_model import IntVar

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.image_template import get_col, get_dummy, get_image, get_row, get_text
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template


def simplify_sqrt(n: int):
    """
    将非负整数 n 写成 a^2 * b 的形式（b 无平方因子），满足 sqrt(n) = a * sqrt(b)。
    :return: (a, b)
    """
    if n <= 0:
        return 0, 1
    a = 1
    b = n
    i = 2
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

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()
        # 出题时随机为每个雷分配复数雷值 ±1 / ±i
        cg: Dict[Position, tuple[int, int]] = {}
        for pos, _ in board("F", special='raw'):
            choice = random.randint(0, 3)
            re = [1, -1, 0, 0][choice]
            im = [0, 0, 1, -1][choice]
            cg[pos] = (re, im)
        # 计算每个非雷格的线索值 = 周围八格雷值之和的模长平方
        for pos, _ in board("N", special='raw'):
            s_re = 0
            s_im = 0
            for nei in pos.neighbors(2):
                if not board.in_bounds(nei):
                    continue
                if nei in cg:
                    s_re += cg[nei][0]
                    s_im += cg[nei][1]
            N = s_re * s_re + s_im * s_im
            board.set_value(pos, ValueCN(pos, N))
        return board

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        # 为每个格子创建并注册复数雷值的四个分量变量
        # 雷格：恰好一个分量为 True，其余为 False
        # 非雷格：全部为 False
        for key in board.get_interactive_keys():
            for pos, mine_var in board(key=key, mode="var", special='raw'):
                if mine_var is None:
                    continue
                re_pos = model.new_bool_var(f"CN_re_pos_{key}_{pos.col}_{pos.row}")
                re_neg = model.new_bool_var(f"CN_re_neg_{key}_{pos.col}_{pos.row}")
                im_pos = model.new_bool_var(f"CN_im_pos_{key}_{pos.col}_{pos.row}")
                im_neg = model.new_bool_var(f"CN_im_neg_{key}_{pos.col}_{pos.row}")
                board.register_variable_special("CN_re_pos", pos, re_pos)
                board.register_variable_special("CN_re_neg", pos, re_neg)
                board.register_variable_special("CN_im_pos", pos, im_pos)
                board.register_variable_special("CN_im_neg", pos, im_neg)
                model.add(
                    re_pos + re_neg + im_pos + im_neg == mine_var
                ).only_enforce_if(s)


class ValueCN(AbstractClueValue):
    id = RuleCN.id

    def __init__(self, pos: Position, value: int = 0, code: bytes = None):
        super().__init__(pos, b'')
        if code is not None:
            if len(code) == 1:
                value = code[0]
            elif len(code) >= 2:
                value = int.from_bytes(code[:2], "big")
        self.count = int(value)
        self.neighbor = pos.neighbors(2)
        # 线索值存储为模长平方 N；sqrt(N) 即语义上的模长
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
        template_data = cast(Template, _data)
        val = SingleIntValue.try_from(template_data)
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
            return get_col(
                get_dummy(height=0.175),
                get_text(str(a)),
                get_dummy(height=0.175),
            )
        if a == 1:
            return get_row(
                get_image("sqrt"),
                get_text(str(b)),
                spacing=-0.15,
            )
        return get_row(
            get_text(str(a)),
            get_image("sqrt"),
            get_text(str(b)),
            spacing=-0.2,
        )

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

        # 收集周围 8 格的 re/im 线性表达式
        neighbor_re: List = []
        neighbor_im: List = []
        for nei in self.neighbor:
            if not board.in_bounds(nei):
                continue
            re_pos = board.get_variable(nei, special='CN_re_pos')
            re_neg = board.get_variable(nei, special='CN_re_neg')
            im_pos = board.get_variable(nei, special='CN_im_pos')
            im_neg = board.get_variable(nei, special='CN_im_neg')
            if re_pos is None or re_neg is None or im_pos is None or im_neg is None:
                continue
            neighbor_re.append(re_pos - re_neg)
            neighbor_im.append(im_pos - im_neg)

        if not neighbor_re:
            # 没有有效邻居，模长必须为 0
            model.add(self.count == 0).only_enforce_if(s)
            return

        sr = model.new_int_var(-8, 8, f"CN_sr_{self.pos.col}_{self.pos.row}")
        si = model.new_int_var(-8, 8, f"CN_si_{self.pos.col}_{self.pos.row}")
        model.add(sr == sum(neighbor_re)).only_enforce_if(s)
        model.add(si == sum(neighbor_im)).only_enforce_if(s)

        sr2 = model.new_int_var(0, 64, f"CN_sr2_{self.pos.col}_{self.pos.row}")
        si2 = model.new_int_var(0, 64, f"CN_si2_{self.pos.col}_{self.pos.row}")
        model.add_multiplication_equality(sr2, [sr, sr]).only_enforce_if(s)
        model.add_multiplication_equality(si2, [si, si]).only_enforce_if(s)

        # 线索值（模长平方）等于实部平方 + 虚部平方
        model.add(sr2 + si2 == self.count).only_enforce_if(s)
        logger.trace(f"[CN] {self.pos}: N={self.count}")
