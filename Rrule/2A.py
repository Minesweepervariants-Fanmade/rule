#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 2A.py
"""
[2A]面积: 线索表示四方向相邻雷区域的面积之和
(注:如果出现大数字则速率极度底下)
"""
import itertools
from typing import List, Tuple, Optional

from ortools.sat.python.cp_model import CpModel

from minesweepervariants.abs.rule import AbstractRule
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger


UN_FLAG = 0
GROUP_4 = 1
GROUP_3 = 2
CONNECT = 4


class Rule2A(AbstractClueRule):
    name = ["2A", "面积", "Area"]
    doc = "线索表示四方向相邻雷区域的面积之和"

    def __init__(self, board: "AbstractBoard" = None, data=None):
        super().__init__(board, data)
        self.flag = UN_FLAG

    def combine(self, rules: List[Tuple['AbstractRule', Optional[str]]]):
        """
        合并规则：
        - 如果存在 (rule, data)，其中 rule 的 name 是 '1S'
        - 并且 data 满足以下之一：
            * None
            * "1"
            * "1;1;...;1"（由一个或多个 '1' 组成，中间以分号分隔）
        则将 self.flag_1S 设为 True。
        """
        for rule, data in rules:
            name = getattr(rule, "name", None)
            if isinstance(name, list):
                name = name[0] if name else None

            if (name in ["1S", "3Y", "1S'", "1S^"] and
               (data is None or all(x == "1" or "1:1" in x for x in data.split(";")))):
                self.flag = CONNECT

            if name == "2G" and data is None:
                self.flag = GROUP_4

            if name == "2G'" and data is None:
                self.flag = GROUP_3

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            if self.flag == CONNECT:
                if board.batch(pos.neighbors(1), "type").count("F") > 0:
                    code = b'\x04'
                else:
                    code = b'\x05'
                board.set_value(pos, Value2A(pos, code))
                continue
            checked = [[False for _ in range(20)] for _ in range(20)]

            def dfs(p: 'AbstractPosition', _checked):
                if not board.in_bounds(p): return None
                if board.get_type(p) != "F": return None
                if _checked[p.x][p.y]: return None
                _checked[p.x][p.y] = True
                dfs(p.left(1), _checked)
                dfs(p.right(1), _checked)
                dfs(p.up(1), _checked)
                dfs(p.down(1), _checked)
                return None

            dfs(pos.left(1), checked)
            dfs(pos.right(1), checked)
            dfs(pos.up(1), checked)
            dfs(pos.down(1), checked)
            cnt = 0
            for i in range(20):
                for j in range(20):
                    if checked[i][j]:
                        cnt += 1
            board.set_value(pos, Value2A(pos, bytes([self.flag, cnt])))
            logger.debug(f"Set {pos} to 2A[{cnt}]")
        return board


class Value2A(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        super().__init__(pos, code)
        if code[0] >= CONNECT:
            self.flag = CONNECT
            if code[0] == 4:
                self.value = 0
            else:
                self.value = 1
        else:
            self.flag = code[0]
            self.value = code[1]

    def __repr__(self) -> str:
        if self.flag == CONNECT:
            if self.value is 1:
                return ">0"
            else:
                return "0"
        return f"{self.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule2A.name[0].encode("ascii")

    def code(self) -> bytes:
        if self.flag == CONNECT:
            if self.value == 1:
                return b'\x04'
            else:
                return b'\x05'
        return bytes([self.flag, self.value])

    def create_constraints_connect(self, model, board, switch):
        var_list = board.batch(self.pos.neighbors(1), "var", drop_none=True)
        model.AddBoolOr(var_list).OnlyEnforceIf(switch)

    def create_constraints_group_4(self, model, board, s):
        value = self.value // 4
        return self.create_constraints_group(value, model, board, s)

    def create_constraints_group_3(self, model, board, s):
        value = self.value // 3
        return self.create_constraints_group(value, model, board, s)

    def create_constraints_group(self, value, model: CpModel, board, s):
        var_a = board.get_variable(self.pos.up().left())
        var_b = board.get_variable(self.pos.up().right())
        var_c = board.get_variable(self.pos.down().right())
        var_d = board.get_variable(self.pos.down().left())

        var_1 = board.get_variable(self.pos.up())
        var_2 = board.get_variable(self.pos.right())
        var_3 = board.get_variable(self.pos.down())
        var_4 = board.get_variable(self.pos.left())

        var_dict = {}
        """
        A 1 B
        4 ? 2
        D 3 C
        """

        for __var_1, __var_2, __var_3, ap_n in [
            (var_a, var_1, var_4, "A"),
            (var_b, var_1, var_2, "B"),
            (var_c, var_3, var_2, "C"),
            (var_d, var_3, var_4, "D"),
        ]:
            if __var_1 is None or __var_2 is None or __var_3 is None:
                continue
            var_X = model.NewBoolVar(f"{__var_1}")
            model.Add(var_X == 1).OnlyEnforceIf([__var_1, __var_2, __var_3])
            model.Add(var_X == 0).OnlyEnforceIf(__var_1.Not())
            model.Add(var_X == 0).OnlyEnforceIf(__var_2.Not())
            model.Add(var_X == 0).OnlyEnforceIf(__var_3.Not())
            var_dict[ap_n] = var_X

        for var_n, ap_1, ap_2 in [
            (var_1, "A", "B"),
            (var_2, "C", "B"),
            (var_3, "D", "C"),
            (var_4, "A", "D"),
        ]:
            if var_n is None:
                continue
            if ap_1 not in var_dict and ap_2 not in var_dict:
                Var_n = var_n
            elif ap_1 not in var_dict:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf(var_dict[ap_2].Not())
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_2])
            elif ap_2 not in var_dict:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf(var_dict[ap_1].Not())
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_1])
            else:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf([var_dict[ap_1].Not(), var_dict[ap_2].Not()])
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_1])
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_2])
            var_dict[var_n] = Var_n

        model.Add(sum(var_dict.values()) == value).OnlyEnforceIf(s)

    def create_constraints(self, board: 'AbstractBoard', switch):
        # 跳过已有的线索格
        model = board.get_model()
        s = switch.get(model, self)

        if self.flag == CONNECT:
            return self.create_constraints_connect(model, board, s)
        elif self.flag == GROUP_4:
            return self.create_constraints_group_4(model, board, s)
        elif self.flag == GROUP_3:
            return self.create_constraints_group_3(model, board, s)

        def dfs(
                deep: int,
                valides: list = None,
                locked: list = None  # 上级锁定的格子,不允许进行扩展
        ):
            if valides is None:
                valides = [self.pos]
            if locked is None:
                locked = []
            checked = set()
            for pos in valides:
                for _pos in pos.neighbors(1):
                    if _pos in locked:
                        continue
                    if _pos in valides:
                        continue
                    if not board.in_bounds(_pos):
                        continue
                    checked.add(_pos)
            if deep == 0:
                if "F" not in board.batch(list(checked), "type"):
                    yield valides, list(checked) + locked
            else:
                for n in range(1, min(deep, len(checked)) + 1):
                    for combo in itertools.combinations(checked, n):
                        outside = [pos for pos in checked if pos not in combo]
                        if "C" in board.batch(combo, "type"):
                            continue
                        if "F" in board.batch(outside, "type"):
                            continue
                        yield from dfs(deep - n, valides + list(combo), locked + outside)

        tmp_list = []
        for vars_f, vars_t in dfs(self.value):
            vars_f = [var_f for var_f in vars_f if var_f != self.pos]
            tmp = model.NewBoolVar(f"tmp,F:{vars_f}|C:{vars_t}")
            vars_t = board.batch(vars_t, mode="variable")
            vars_f = board.batch(vars_f, mode="variable")
            model.Add(sum(vars_t) == 0).OnlyEnforceIf(tmp)
            if vars_f:
                model.AddBoolAnd(vars_f).OnlyEnforceIf(tmp)
            tmp_list.append(tmp)
        model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
        get_logger().trace(f"position:{self.pos}, value:{self}, 枚举所有可能性共:{len(tmp_list)}个")
