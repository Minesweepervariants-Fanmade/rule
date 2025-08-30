#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 2A.py
"""
[2A']面积: 线索表示它所在的四连通非雷区的面积。
(注:如果出现大数字则速率极度底下)
"""
import itertools
import time
from typing import List, Tuple, Optional

from minesweepervariants.abs.rule import AbstractRule
from minesweepervariants.utils.impl_obj import VALUE_QUESS
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger


class Rule2A(AbstractClueRule):
    name = ["2A'", "面积'", "Area'"]
    doc = "线索表示它所在的四连通非雷区的面积。"

    def __init__(self, board: "AbstractBoard" = None, data=None):
        super().__init__(board, data)
        self.flag = None

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

            if (name in ["1D'", "1O"] and
               (data is None or all(x == "1" or "1:1" in x for x in data.split(";")))):
                self.flag = True

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for key in board.get_interactive_keys():
            size = board.get_config(key, "size")
            for pos, _ in board("N", key=key):
                if self.flag:
                    board[pos] = VALUE_QUESS
                    continue
                checked = [[False for _ in range(size[0])] for _ in range(size[1])]

                def dfs(p: 'AbstractPosition', _checked):
                    if not board.in_bounds(p): return None
                    if board.get_type(p) == "F": return None
                    if _checked[p.x][p.y]: return None
                    _checked[p.x][p.y] = True
                    dfs(p.left(1), _checked)
                    dfs(p.right(1), _checked)
                    dfs(p.up(1), _checked)
                    dfs(p.down(1), _checked)
                    return None

                checked[pos.x][pos.y] = True
                dfs(pos.left(1), checked)
                dfs(pos.right(1), checked)
                dfs(pos.up(1), checked)
                dfs(pos.down(1), checked)
                cnt = 0
                for i in range(size[0]):
                    for j in range(size[1]):
                        if checked[i][j]:
                            cnt += 1
                board.set_value(pos, Value2A(pos, bytes([cnt])))
                logger.debug(f"Set {pos} to 2A'[{cnt}]")
        return board


class Value2A(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        super().__init__(pos, code)
        self.value = code[0]
        self.neighbor = pos.neighbors(1)
        self.pos = pos

    def __repr__(self) -> str:
        return f"{self.value}"

    @classmethod
    def type(cls) -> bytes:
        return Rule2A.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        # 跳过已有的线索格
        model = board.get_model()
        s = switch.get(model, self)

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
                if "C" not in board.batch(list(checked), "type"):
                    yield list(checked) + locked, valides
            else:
                for n in range(1, min(deep, len(checked)) + 1):
                    for combo in itertools.combinations(checked, n):
                        outside = [pos for pos in checked if pos not in combo]
                        if "F" in board.batch(combo, "type"):
                            continue
                        if "C" in board.batch(outside, "type"):
                            continue
                        yield from dfs(deep - n, valides + list(combo), locked + outside)

        tmp_list = []
        t = time.time()
        for vars_f, vars_t in dfs(self.value - 1):
            vars_t.sort()
            tmp = model.NewBoolVar(f"{self.pos}[{self}]:C:|{vars_t}| F:|{vars_f}|")
            vars_t = board.batch(vars_t, mode="variable")
            vars_f = board.batch(vars_f, mode="variable")
            model.Add(sum(vars_t) == 0).OnlyEnforceIf(tmp)
            if vars_f:
                model.AddBoolAnd(vars_f).OnlyEnforceIf(tmp)
            tmp_list.append(tmp)
        model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
        get_logger().trace(f"position:{self.pos}, value:{self},"
                           f" used_time:{time.time() - t}s,"
                           f" 枚举所有可能性共:{len(tmp_list)}个")
        # print()
        # print()
        # print()
        # print(board)
        # print(f"position:{self.pos}, value:{self}, used_time:{time.time() - t}s, 枚举所有可能性共:{len(tmp_list)}个")
        # print(board)
        [get_logger().trace(tmp) for tmp in tmp_list]
        #
        # import sys
        # sys.exit()
