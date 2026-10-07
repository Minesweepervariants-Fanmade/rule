#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/05 13:40
# @FileName: CN.py
"""
[CN] 复数雷值 (Complex Number)：雷的雷值将是(+1,-1,+i,-i)中的一种，
数字表示周围八格的雷值之和的模长。
"""
from typing import Dict, List, cast

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, Size, JSONObject, MASTER_BOARD_KEY
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.image_template import get_col, get_dummy, get_image, get_row, get_text
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template

AXIS_BOARD = "CN_AXIS"   # 虚实：0=实轴(±1)  1=虚轴(±i)
SIGN_BOARD = "CN_SIGN"   # 正负：0=负        1=正
RE_NS = "CN_RE"          # 实部 int 命名空间 ∈ {-1, 0, 1}
IM_NS = "CN_IM"          # 虚部 int 命名空间 ∈ {-1, 0, 1}

def simplify_sqrt(n: int):
    """将非负整数 n 写成 a^2*b（b 无平方因子），使 sqrt(n)=a*sqrt(b)。"""
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
    special = []

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        bound = board.boundary()
        size = Size(bound.col + 1, bound.row + 1)
        axis_labels: dict[Position, str] = {}
        sign_labels: dict[Position, str] = {}
        board.generate_board(AXIS_BOARD, size=size)
        board.generate_board(SIGN_BOARD, size=size)
        for pos, _ in board(key=AXIS_BOARD):
            master_pos = pos.clone()
            master_pos.to_board(MASTER_BOARD_KEY)
            axis_labels[pos] = f"{master_pos} ±i"
        for pos, _ in board(key=SIGN_BOARD):
            master_pos = pos.clone()
            master_pos.to_board(MASTER_BOARD_KEY)
            sign_labels[pos] = f"{master_pos}=+"
        board.set_config(AXIS_BOARD, "labels", axis_labels)
        board.set_config(SIGN_BOARD, "labels", sign_labels)
        board.set_config(AXIS_BOARD, "pos_label", True)
        board.set_config(SIGN_BOARD, "pos_label", True)
        board.set_config(AXIS_BOARD, "interactive", False)
        board.set_config(SIGN_BOARD, "interactive", False)
        if data is not None:
            self.special.extend([RE_NS, IM_NS])

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()

        # 先给两个副板所有格子清零
        for name in (AXIS_BOARD, SIGN_BOARD):
            for pos, _ in board(key=name, special='raw'):
                board.set_value(pos, None)

        # 出题时随机给每个雷分配复数雷值 ±1 / ±i，并写入两个副板
        cg: Dict[Position, tuple] = {}
        for pos, _ in board("F", special='raw'):
            k = random.randint(0, 3)
            re, im = ([1, -1, 0, 0][k], [0, 0, 1, -1][k])
            cg[pos] = (re, im)
            axis_pos = Position(pos.col, pos.row, AXIS_BOARD)
            sign_pos = Position(pos.col, pos.row, SIGN_BOARD)
            # AXIS：虚轴置 1，实轴置 0
            board.set_value(axis_pos, VALUE_CIRCLE if im != 0 else VALUE_CROSS)
            # SIGN：正号置 1，负号置 0
            board.set_value(sign_pos, VALUE_CIRCLE if (re > 0 or im > 0) else VALUE_CROSS)

        # 主板上非雷格：线索值 = 周围八格雷值之和的模长平方
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

    def create_constraints(self, board: 'Board', switch: Switch) -> None:
        model = board.get_model()
        s = switch.get(model, self)

        # 每格：
        #   1) 副板 bool (axis, sign) 与雷变量保持物理一致（非雷两板必须 0）
        #   2) 注册 re / im 两个 int 命名空间，把副板 bit 线性化成实部/虚部分量
        #      ab = axis AND sign
        #      re = -m + 2*sign + axis - 2*ab  ∈ {-1, 0, +1}
        #      im = 2*ab - axis                ∈ {-1, 0, +1}
        for key in board.get_interactive_keys():
            for pos, mine_var in board(key=key, mode="var", special='raw'):
                if mine_var is None:
                    continue
                axis = board.get_variable(Position(pos.col, pos.row, AXIS_BOARD))
                sign = board.get_variable(Position(pos.col, pos.row, SIGN_BOARD))
                if axis is None or sign is None:
                    continue
                model.add(axis <= mine_var).only_enforce_if(s)
                model.add(sign <= mine_var).only_enforce_if(s)

                ab = model.new_bool_var(f"CN_ab_{pos.board_key}_{pos.col}_{pos.row}")
                model.add(ab <= axis)
                model.add(ab <= sign)
                model.add(ab >= axis + sign - 1)

                re = model.new_int_var(-1, 1, f"CN_re_{pos.board_key}_{pos.col}_{pos.row}")
                im = model.new_int_var(-1, 1, f"CN_im_{pos.board_key}_{pos.col}_{pos.row}")
                model.add(re == -mine_var + 2 * sign + axis - 2 * ab).only_enforce_if(s)
                model.add(im == 2 * ab - axis).only_enforce_if(s)
                board.register_variable_special(RE_NS, pos, re)
                board.register_variable_special(IM_NS, pos, im)

    def init_clear(self, board: 'Board', vice_board=False) -> None:
        if vice_board:
            return
        for name in (AXIS_BOARD, SIGN_BOARD):
            for pos, _ in board(key=name, special='raw'):
                board.set_value(pos, None)


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

    def compose(self, board) -> dict:
        a, b = simplify_sqrt(self.count)
        if b == 1:
            return get_col(get_dummy(height=0.175), get_text(str(a)), get_dummy(height=0.175))
        if a == 1:
            return get_row(get_image("sqrt"), get_text(str(b)), spacing=-0.15)
        return get_row(get_text(str(a)), get_image("sqrt"), get_text(str(b)), spacing=-0.2)

    def web_component(self, board) -> dict:
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

        # 直接从 int 命名空间读实部/虚部
        neighbor_re: List = []
        neighbor_im: List = []
        for nei in self.neighbor:
            if not board.in_bounds(nei):
                continue
            re = board.get_variable(nei, special=RE_NS)
            im = board.get_variable(nei, special=IM_NS)
            if re is None or im is None:
                continue
            neighbor_re.append(re)
            neighbor_im.append(im)

        if not neighbor_re:
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

        model.add(sr2 + si2 == self.count).only_enforce_if(s)
        logger.trace(f"[CN] {self.pos}: N={self.count}")