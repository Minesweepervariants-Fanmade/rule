#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1FL] 至少一行/一列/一对角线全为雷
要求题板中至少存在一行、一列、主对角线或副对角线上的所有格子都是雷。
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleAtLeastOneFullLine(AbstractMinesRule):
    id = "1FL"
    name = "AtLeastOneFullLine"
    name.zh_CN = "至少一行/一列/一对角线全为雷"
    doc = "Requires that at least one row, one column, one main diagonal, or one anti-diagonal is completely filled with mines."
    doc.zh_CN = "要求至少有一行、一列、一条主对角线或一条副对角线全部为雷。"
    author = ("Assistant", 0)
    tags = ["Creative", "Global", "Construction"]
    creation_time = "2026-06-02"

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            bound = board.boundary(key=key)
            rows = bound.row + 1
            cols = bound.col + 1

            # 收集所有有效格子的变量
            var_map = {}
            for r in range(rows):
                for c in range(cols):
                    pos = board.get_pos(r, c, key)
                    if pos is not None and board.is_valid(pos):
                        var = board.get_variable(pos)
                        if var is not None:
                            var_map[(r, c)] = var

            if not var_map:
                continue

            line_vars = []

            # ----- 每一行 -----
            for r in range(rows):
                cells = [(r, c) for c in range(cols) if (r, c) in var_map]
                if not cells:
                    continue
                line_flag = model.NewBoolVar(f"full_row_{key}_{r}")
                for (_, c) in cells:
                    model.Add(var_map[(r, c)] == 1).OnlyEnforceIf([line_flag, rule_switch])
                line_vars.append(line_flag)

            # ----- 每一列 -----
            for c in range(cols):
                cells = [(r, c) for r in range(rows) if (r, c) in var_map]
                if not cells:
                    continue
                line_flag = model.NewBoolVar(f"full_col_{key}_{c}")
                for (r, _) in cells:
                    model.Add(var_map[(r, c)] == 1).OnlyEnforceIf([line_flag, rule_switch])
                line_vars.append(line_flag)

            # ----- 主对角线 (左上→右下) -----
            diag = []
            r, c = 0, 0
            while r < rows and c < cols:
                if (r, c) in var_map:
                    diag.append((r, c))
                r += 1
                c += 1
            if diag:
                diag_flag = model.NewBoolVar(f"full_maindiag_{key}")
                for (r, c) in diag:
                    model.Add(var_map[(r, c)] == 1).OnlyEnforceIf([diag_flag, rule_switch])
                line_vars.append(diag_flag)

            # ----- 副对角线 (右上→左下) -----
            diag = []
            r, c = 0, cols - 1
            while r < rows and c >= 0:
                if (r, c) in var_map:
                    diag.append((r, c))
                r += 1
                c -= 1
            if diag:
                antidiag_flag = model.NewBoolVar(f"full_antidiag_{key}")
                for (r, c) in diag:
                    model.Add(var_map[(r, c)] == 1).OnlyEnforceIf([antidiag_flag, rule_switch])
                line_vars.append(antidiag_flag)

            # 至少一个候选线成立
            if line_vars:
                model.AddBoolOr(line_vars).OnlyEnforceIf(rule_switch)
