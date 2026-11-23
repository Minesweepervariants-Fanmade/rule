#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-05-27 04:03:00
# @Author  : NT (2201963934)
# @FileName: Same.py
"""
[Same] 板子相同: 多块主板里至少有两块的雷布局完全相同。
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING, List, Tuple

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.position import Position

if TYPE_CHECKING:
    from ortools.sat.python.cp_model import IntVar
    from minesweepervariants.board import Board
    from minesweepervariants.impl.summon.solver import Switch


class RuleSame(AbstractMinesRule):
    id = "Same"
    name = "Same"
    name.zh_CN = "板子相同"
    doc = "Among the main boards, at least two boards have exactly the same mine layout."
    doc.zh_CN = "板子相同：多块主板里至少有两块相同"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Multi-Board", "Meta"]
    creation_time = "2026-05-27 04:03:00"

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        keys = board.get_interactive_keys()
        if len(keys) < 2:
            # 只有一块主板时该规则没有可比较的对象。
            return

        pair_vars = []
        for key_a, key_b in combinations(keys, 2):
            size_a = board.get_config(key_a, "size")
            size_b = board.get_config(key_b, "size")
            if size_a is None or size_b is None or size_a != size_b:
                continue

            # 两块板必须具有相同的有效格形状（尺寸与掩码一致），
            # 才可能被称为“相同”。
            compared: List[Tuple['IntVar', 'IntVar']] = []
            same_shape = True
            for row in range(size_a.rows):
                for col in range(size_a.cols):
                    pos_a = Position(col, row, key_a)
                    pos_b = Position(col, row, key_b)
                    valid_a = board.is_valid(pos_a)
                    valid_b = board.is_valid(pos_b)
                    if valid_a != valid_b:
                        same_shape = False
                        break
                    if not valid_a:
                        continue

                    var_a = board.get_variable(pos_a, special="raw")
                    var_b = board.get_variable(pos_b, special="raw")
                    if var_a is None or var_b is None:
                        same_shape = False
                        break
                    compared.append((var_a, var_b))
                if not same_shape:
                    break

            if not same_shape:
                continue

            # pair_var 为真 => 两块板在所有有效位置上的雷状态完全一致。
            pair_var = model.new_bool_var(f"Same_{key_a}_{key_b}")
            for var_a, var_b in compared:
                model.add(var_a == var_b).only_enforce_if(pair_var, s)
            pair_vars.append(pair_var)

        if pair_vars:
            # 至少有一对主板完全相同。
            model.add_bool_or(pair_vars).only_enforce_if(s)
        else:
            # 存在多块主板，但没有任何两块具有相同的尺寸与掩码。
            model.add_bool_or([]).only_enforce_if(s)
