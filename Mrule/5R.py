#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/14 10:55
# @Author  : DeepSeek Agent
# @FileName: 5R.py
"""
[5R] 排名：雷线索数字表示其雷区面积从小到大的排名

规则语义:
- 中线规则(Mrule), 线索存储在雷格上。
- 将题板内所有雷格按四连通划分为若干极大雷区。
- 对某个雷区 R(面积 A = |R|), 其排名定义为:
      rank(R) = 1 + #{其它雷区 R' : |R'| < A}
  (标准竞赛排名: 并列面积取同名次, 后续名次跳号)
- 同一雷区内的每个雷格的线索值均为 rank(R)。

示例:
- 三个雷区面积分别为 [1, 2, 2]: 排名为 1, 2, 2
- 四个雷区面积分别为 [1, 2, 2, 3]: 排名为 1, 2, 2, 4 (面积 3 有 3 个严格小于它的雷区)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Set

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import (
    SingleIntValue,
    is_value_template,
)
from ...rule.Lrule.connect import connect

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule5R(AbstractMinesClueRule):
    """[5R] 排名"""

    id = "5R"
    name = "Ranking"
    name.zh_CN = "排名"
    doc = "Mines clue value indicates the rank of its mine region area from smallest to largest"
    doc.zh_CN = "雷线索数字表示其雷区面积从小到大的排名"
    tags = ["Creative", "Local", "Number Clue", "Connectivity", "Extensive Trial"]
    creation_time = "2026-06-08"
    author = ("NT", 2201963934)

    # ------------------------------------------------------------------
    # 辅助函数
    # ------------------------------------------------------------------
    @staticmethod
    def _neighbors4(pos: Position) -> List[Position]:
        return [pos.up(), pos.down(), pos.left(), pos.right()]

    # ------------------------------------------------------------------
    # fill
    # ------------------------------------------------------------------
    def fill(self, board: "Board") -> "Board":
        for key in board.get_interactive_keys():
            mines = [pos for pos, _ in board("F", key=key)]
            mine_set: Set[Position] = set(mines)
            visited: Set[Position] = set()
            regions: List[List[Position]] = []

            for start in mines:
                if start in visited:
                    continue
                stack = [start]
                comp: List[Position] = []
                while stack:
                    cur = stack.pop()
                    if cur in visited or cur not in mine_set:
                        continue
                    visited.add(cur)
                    comp.append(cur)
                    for nb in self._neighbors4(cur):
                        if nb in visited or nb not in mine_set:
                            continue
                        if not board.in_bounds(nb):
                            continue
                        stack.append(nb)
                if comp:
                    regions.append(comp)

            areas = [len(c) for c in regions]
            for comp in regions:
                area = len(comp)
                rank = 1 + sum(1 for other_area in areas if other_area < area)
                code = bytes([rank & 0xFF])
                for pos in comp:
                    board.set_value(pos, Value5R(pos, code))
        return board

    # ------------------------------------------------------------------
    # create_constraints
    # ------------------------------------------------------------------
    def create_constraints(self, board: "Board", switch: "Switch"):
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        for key in board.get_interactive_keys():
            positions_vars = [
                (pos, var)
                for pos, var in board(key=key, mode="variable", special="raw")
                if var is not None
            ]
            if not positions_vars:
                continue

            positions = [p for p, _ in positions_vars]
            pos_index = {p: i for i, p in enumerate(positions)}
            n = len(positions)

            # ---- 1) 四连通分量划分 ----
            root_vars = [model.new_bool_var(f"[5R]root_{key}_{i}") for i in range(n)]
            component_ids = connect(
                model=model,
                board=board,
                switch=s,
                component_num=None,
                ub=False,
                connect_value=1,
                nei_value=1,
                positions_vars=positions_vars,
                root_vars=root_vars,
                special="raw",
            )

            # ---- 2) 每个分量的面积 ----
            # sizes[i] 仅在 i 为根时表示对应分量面积, 否则为 0。
            sizes = [
                model.new_int_var(0, n, f"[5R]size_{key}_{i}") for i in range(n)
            ]
            for i in range(n):
                member_vars = []
                for j in range(n):
                    same_comp = model.new_bool_var(f"[5R]sc_{key}_{i}_{j}")
                    model.add(component_ids[j] == i).only_enforce_if([same_comp, s])
                    model.add(component_ids[j] != i).only_enforce_if([same_comp.Not(), s])

                    mine_j = positions_vars[j][1]
                    member = model.new_bool_var(f"[5R]m_{key}_{i}_{j}")
                    # member == (same_comp AND mine_j)
                    model.add(member <= same_comp).only_enforce_if(s)
                    model.add(member <= mine_j).only_enforce_if(s)
                    model.add(member >= same_comp + mine_j - 1).only_enforce_if(s)
                    member_vars.append(member)

                model.add(sizes[i] == sum(member_vars)).only_enforce_if([root_vars[i], s])
                model.add(sizes[i] == 0).only_enforce_if([root_vars[i].Not(), s])

            # ---- 3) 排名 ----
            # rank_i = 1 + #{ j : root_j AND size_j < size_i }
            ranks = [model.new_int_var(0, n, f"[5R]rank_{key}_{i}") for i in range(n)]
            for i in range(n):
                lt_terms = []
                for j in range(n):
                    if j == i:
                        continue
                    lt = model.new_bool_var(f"[5R]lt_{key}_{i}_{j}")
                    # lt 仅在 root_i 真时受约束, 且 lt → root_j
                    model.add(lt <= root_vars[j]).only_enforce_if([root_vars[i], s])
                    # root_i 真 且 lt 真 → size_j < size_i
                    model.add(sizes[j] - sizes[i] <= -1).only_enforce_if([lt, root_vars[i], s])
                    # root_i 真 且 root_j 真 且 lt 假 → size_j >= size_i
                    model.add(sizes[j] - sizes[i] >= 0).only_enforce_if(
                        [lt.Not(), root_vars[i], root_vars[j], s]
                    )
                    lt_terms.append(lt)

                model.add(ranks[i] == 1 + sum(lt_terms)).only_enforce_if([root_vars[i], s])
                model.add(ranks[i] == 0).only_enforce_if([root_vars[i].Not(), s])

            # ---- 4) 线索值约束 ----
            for pos, obj in board("F", key=key, mode="obj"):
                if not isinstance(obj, Value5R):
                    continue
                idx = pos_index.get(pos)
                if idx is None:
                    continue

                raw_var = positions_vars[idx][1]
                model.add(raw_var == 1).only_enforce_if(s)

                clue_var = model.new_int_var(0, n, f"[5R]clue_{key}_{idx}")
                # clue_var == ranks[component_ids[idx]]
                model.add_element(
                    index=component_ids[idx],
                    expressions=ranks,
                    target=clue_var,
                ).only_enforce_if(s)
                model.add(clue_var == obj.value.value).only_enforce_if(s)
                logger.trace(
                    f"[5R] {pos}: clue == rank of its region (expect {obj.value.value})"
                )

    # ------------------------------------------------------------------
    # suggest_total
    # ------------------------------------------------------------------
    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            ub += info["total"][key]
        # 排名规则需要多种不同面积的雷区, 适中密度更易满足
        info["soft_fn"](ub * 0.4, 0)


class Value5R(AbstractMinesValue):
    """[5R] 线索值: 所在雷区面积从小到大的排名"""

    id = Rule5R.id

    def __init__(self, pos: Position, code: bytes = b""):
        super().__init__(pos)
        self.pos = pos
        self._rank = code[0] if code else 0
        self.value = SingleIntValue(self._rank, is_mine=True)

    @classmethod
    def from_json(cls, pos: "Position", data: "JSONObject") -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("5R value is not a value template")
        val = SingleIntValue.try_from(_data)
        if val is None:
            raise ValueError("5R value is empty")
        return cls(pos, code=bytes([val.value]))

    def __repr__(self) -> str:
        return str(self._rank)

    @classmethod
    def type(cls) -> bytes:
        return Rule5R.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self._rank & 0xFF])
