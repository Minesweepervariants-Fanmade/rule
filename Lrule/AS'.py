#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/05
# @Author  : AI Assistant
# @FileName: AS'.py
"""
[AS'] 自旋' (AutoSpin')：
每个2x2区域内不能同时存在染色非雷格、非染色非雷格、染色雷格和非染色雷格。
即一个2x2方块中，四种状态（染色/非染色 × 雷/非雷）不能全部出现。

(内容由AI生成 质量不可靠)
"""

from typing import List, Tuple
from ortools.sat.python.cp_model import IntVar

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition


class RuleASp(AbstractMinesRule):
    name = ["AS'", "自旋'", "AutoSpin'"]
    doc = "每个2x2区域内不能同时存在四种状态（染色雷、非染色雷、染色非雷、非染色非雷）。"

    subrules = [
        [True, "[AS'] 禁止四态共存"]
    ]

    def create_constraints(self, board: 'AbstractBoard', switch):
        """添加约束：每个2x2方块内不能四种状态都出现。"""
        if not self.subrules[0][0]:
            return

        model = board.get_model()
        s = switch.get(model, self)

        # 遍历所有可能的2x2方块
        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            max_x = bound.x
            max_y = bound.y

            for x in range(max_x):
                for y in range(max_y):
                    # 获取2x2方块的四个格子
                    pos_tl = board.get_pos(x, y, key)      # 左上
                    pos_tr = board.get_pos(x, y + 1, key)  # 右上
                    pos_bl = board.get_pos(x + 1, y, key)  # 左下
                    pos_br = board.get_pos(x + 1, y + 1, key)  # 右下

                    if not all(board.in_bounds(p) for p in [pos_tl, pos_tr, pos_bl, pos_br]):
                        continue

                    # 获取每个格子的变量和染色状态
                    var_tl = board.get_variable(pos_tl)
                    var_tr = board.get_variable(pos_tr)
                    var_bl = board.get_variable(pos_bl)
                    var_br = board.get_variable(pos_br)

                    dye_tl = board.get_dyed(pos_tl)
                    dye_tr = board.get_dyed(pos_tr)
                    dye_bl = board.get_dyed(pos_bl)
                    dye_br = board.get_dyed(pos_br)

                    # 根据染色状态构建允许的赋值列表（排除四种状态都出现的组合）
                    allowed = self._compute_allowed_assignments(
                        [dye_tl, dye_tr, dye_bl, dye_br]
                    )

                    # 添加允许赋值约束
                    model.AddAllowedAssignments(
                        [var_tl, var_tr, var_bl, var_br],
                        allowed
                    ).OnlyEnforceIf(s)

    def _compute_allowed_assignments(self, dyes: List[bool]) -> List[Tuple[int, int, int, int]]:
        """
        根据四个格子的染色状态，返回所有允许的 (var0,var1,var2,var3) 赋值组合。
        排除那些四种状态（染色雷、非染色雷、染色非雷、非染色非雷）全部出现的组合。
        """
        allowed = []
        # 枚举所有 2^4 = 16 种雷/非雷组合
        for mask in range(16):
            vars_vals = [(mask >> i) & 1 for i in range(4)]
            # 统计四种类型是否出现
            has_dyed_mine = False
            has_undyed_mine = False
            has_dyed_empty = False
            has_undyed_empty = False

            for dye, is_mine in zip(dyes, vars_vals):
                if is_mine:
                    if dye:
                        has_dyed_mine = True
                    else:
                        has_undyed_mine = True
                else:
                    if dye:
                        has_dyed_empty = True
                    else:
                        has_undyed_empty = True

            # 如果四种状态都出现了，则禁止此组合
            if has_dyed_mine and has_undyed_mine and has_dyed_empty and has_undyed_empty:
                continue
            allowed.append(tuple(vars_vals))
        return allowed

    def suggest_total(self, info: dict):
        """软约束：建议总雷数不超过格子数的一半（无严格依赖）。"""
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        info["soft_fn"](ub // 2, 0)