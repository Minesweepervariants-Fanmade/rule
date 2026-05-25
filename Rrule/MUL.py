#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/25 20:10
# @Author  : Wu_RH
# @FileName: MUL.py
from base64 import b64encode

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.Mrule import AbstractMinesClueRule
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition, JSONObject, ImmutableDict
from minesweepervariants.abs.rule import AbstractValue, AbstractRule
from minesweepervariants.impl.impl_obj import VALUE_QUESS, add_rule, get_value_type

from collections import Counter

from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger


def prime_factors(n: int) -> dict[int, int]:
    """返回 n 的质因数分解字典 {质因数: 指数}，n 为正整数"""
    if n <= 1:
        return {}
    factors = Counter()
    # 处理因子 2
    while n % 2 == 0:
        factors[2] += 1
        n //= 2
    # 处理奇数因子
    p = 3
    while p * p <= n:
        while n % p == 0:
            factors[p] += 1
            n //= p
        p += 2
    if n > 1:
        factors[n] += 1
    return dict(factors)


def div_pairs(factors: dict[int, int]):
    """
    输入质因数分解字典 {质因数: 指数}，返回所有无序因子对 (a, b)，其中 a <= b 且 a * b = N。
    例如：{3:3, 37:1} -> [(1, 999), (3, 333), (9, 111), (27, 37)]
    """
    # 先计算 N 的值
    N = 1
    for p, e in factors.items():
        N *= p ** e

    # 递归生成所有因子
    primes = list(factors.items())
    divisors = []

    def generate(idx: int, current: int):
        if idx == len(primes):
            divisors.append(current)
            return
        p, e = primes[idx]
        mul = 1
        for _ in range(e + 1):
            generate(idx + 1, current * mul)
            mul *= p

    generate(0, 1)
    divisors.sort()

    # 生成无序对 (a <= b)
    pairs = []
    for a in divisors:
        b = N // a
        if a <= b:
            pairs.append((a, b))
    return pairs


class RuleMUL(AbstractClueRule):
    id = "MUL"
    name = "Multiplication Combination"
    name.zh_CN = "乘法组合"
    doc = "Combines two right-side variants via multiplication."
    doc.zh_CN = "将两个右侧变体通过乘法组合。"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2026/5/22 0:42"
    author = ("ekisacik", 0)

    def __init__(self, board: "AbstractBoard | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        if data is None:
            raise ValueError("需要传入两个规则")
        if ";" not in data:
            raise ValueError("需要使用;分割两个规则")
        self.rule1, self.rule2 = data.split(";")

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        board_a = board.clone()
        board_b = board.clone()
        _rule1 = add_rule(
            board_a, self.rule1.split(":", 1)[0],
            self.rule1.split(":", 1)[1] if ":" in self.rule1 else None, False
        )
        _rule2 = add_rule(
            board_b, self.rule2.split(":", 1)[0],
            self.rule2.split(":", 1)[1] if ":" in self.rule2 else None, False
        )
        if not isinstance(_rule1, AbstractClueRule):
            raise ValueError(f"不接受的规则: {_rule1}")
        if not isinstance(_rule2, AbstractClueRule):
            raise ValueError(f"不接受的规则: {_rule2}")
        board1 = _rule1.fill(board_a)
        board2 = _rule2.fill(board_b)

        for pos, _ in board("N", mode="none"):
            if get_value_type(board1[pos].type().decode("ascii")) is None:
                raise ValueError(f"[MUL]OBJ_TYPE:{self.rule1} undefind")
            if get_value_type(board2[pos].type().decode("ascii")) is None:
                raise ValueError(f"[MUL]OBJ_TYPE:{self.rule2} undefind")
            break
        for pos, _ in board("N", mode="none"):
            obj1 = board1[pos]
            obj2 = board2[pos]
            if not (str(obj1).isdigit() and str(obj2).isdigit()):
                board[pos] = VALUE_QUESS
            value = int(str(obj1)) * int(str(obj2))
            obj = ValueMUL.from_json(pos, ImmutableDict({
                "value": value,
                "type1": obj1.type().decode("ascii"),
                "type2": obj2.type().decode("ascii")
            }))
            board[pos] = obj
        return board


class ValueMUL(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition') -> None:
        super().__init__(pos)
        self.value: int = -1
        self.type1: str = ""
        self.type2: str = ""

    def json(self) -> 'JSONObject':
        return ImmutableDict({"value": self.value, "type1": self.type1, "type2": self.type2})

    @classmethod
    def from_json(cls, pos: 'AbstractPosition', data: 'JSONObject') -> 'AbstractClueValue':
        obj = cls(pos)
        obj.value = data["value"]
        obj.type1 = data["type1"]
        obj.type2 = data["type2"]
        return obj

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return RuleMUL.id.encode("ascii")

    def create_constraints(self, board: AbstractBoard, switch):
        if self.type1 == "" and self.type2 == "":
            raise ValueError("Object uninit")
        model = board.get_model()
        type1 = get_value_type(self.type1)
        type2 = get_value_type(self.type2)

        choose_list = []

        def get_possimbl():
            if self.value == 0:
                yield 0, 0
                k = 1
                while True:
                    yield 0, k
                    yield k, 0
                    k += 1
            for a, b in div_pairs(prime_factors(self.value)):
                yield a, b
                if a != b:
                    yield b, a

        def init_obj(numa, numb):
            dataa = ImmutableDict({
                "old_style": True, "type": b64encode(type1.type()).decode(),
                "code": b64encode(bytes([numa])).decode()
            })
            obja = type1.from_json(self.pos, dataa)
            datab = ImmutableDict({
                "old_style": True, "type": b64encode(type2.type()).decode(),
                "code": b64encode(bytes([numb])).decode()
            })
            objb = type2.from_json(self.pos, datab)
            choose_list.append(model.new_bool_var(
                f"choose_{numa}->{type1.type().decode('ascii')}_"
                f"{numb}->{type2.type().decode('ascii')}"
            ))
            return obja, objb

        for num1, num2 in get_possimbl():
            try:
                obj1, obj2 = init_obj(num1, num2)
                ...
            except Exception as e:
                get_logger().trace(str(e))
                if self.value == 0:
                    break
                continue
            obj1.create_constraints(board, FakeSwitch(choose_list[-1]))
            obj2.create_constraints(board, FakeSwitch(choose_list[-1]))
        get_logger().trace(f"[{self.pos}]ADD OR: {choose_list}")
        model.add_bool_or(choose_list).only_enforce_if(switch.get(model, self))


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
